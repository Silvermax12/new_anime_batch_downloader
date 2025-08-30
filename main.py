from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import os
import uuid
from datetime import datetime

from session_mgr import SessionManager
from api_client import search_anime, get_all_episodes
from scraper import scrape_download_links
from resolver import resolve_download_info
from transfer import advanced_download_with_progress

app = FastAPI(
    title="Anime Batch Downloader API",
    description="API service for downloading anime episodes from AnimePagehe",
    version="1.0.0"
)

# Global session manager - initialized lazily to avoid startup issues
sm = None

def get_session_manager():
    """Get or create session manager"""
    global sm
    if sm is None:
        sm = SessionManager()
    return sm

# In-memory storage for download tasks (in production, use Redis or database)
download_tasks = {}

class SearchRequest(BaseModel):
    query: str

class SearchResult(BaseModel):
    title: str
    type: str
    episodes: int
    id: int
    session: str
    status: Optional[str] = None
    season: Optional[str] = None
    year: Optional[int] = None
    score: Optional[float] = None
    poster: Optional[str] = None

class EpisodesRequest(BaseModel):
    anime_session: str

class Episode(BaseModel):
    episode: int
    session: str

class QualityRequest(BaseModel):
    anime_session: str
    episode_session: str

class DownloadRequest(BaseModel):
    anime_session: str
    episodes: List[int]  # List of episode numbers
    quality: str = "720"
    language: str = "eng"
    download_directory: str = "./"

class DownloadTask(BaseModel):
    task_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: float
    current_episode: Optional[int] = None
    total_episodes: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "Anime Batch Downloader API", "version": "1.0.0"}

@app.post("/search", response_model=List[SearchResult])
async def search_anime_endpoint(request: SearchRequest):
    """Search for anime by name"""
    try:
        # Get session manager in a thread-safe way
        session_manager = get_session_manager()
        results = search_anime(session_manager, request.query)
        if not results:
            raise HTTPException(status_code=404, detail="No anime found for your search query. Try different keywords.")
        
        return [SearchResult(**result) for result in results]
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Search endpoint error: {error_details}")
        
        # Provide more user-friendly error messages
        error_msg = str(e)
        if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
            raise HTTPException(
                status_code=503, 
                detail="AnimePagehe service is temporarily unavailable. Please try again later or check your internet connection."
            )
        elif "animepahe.ru" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="Cannot connect to AnimePagehe. The service may be down or your connection may be blocked."
            )
        else:
            raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/episodes", response_model=List[Episode])
async def get_episodes_endpoint(request: EpisodesRequest):
    """Get all episodes for a specific anime"""
    try:
        session_manager = get_session_manager()
        episodes = get_all_episodes(session_manager, request.anime_session)
        if not episodes:
            raise HTTPException(status_code=404, detail="No episodes found")
        
        return [Episode(**ep) for ep in episodes]
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Episodes endpoint error: {error_details}")
        raise HTTPException(status_code=500, detail=f"Failed to get episodes: {str(e)}")

@app.post("/qualities")
async def get_qualities_endpoint(request: QualityRequest):
    """Get available qualities and languages for a specific episode"""
    try:
        links = scrape_download_links(request.anime_session, request.episode_session)
        if not links:
            raise HTTPException(status_code=404, detail="No download links found")
        
        # Parse qualities and languages
        qualities = {}
        for key in links.keys():
            if "_" in key:
                quality, language = key.split("_", 1)
                if quality not in qualities:
                    qualities[quality] = []
                if language not in qualities[quality]:
                    qualities[quality].append(language)
        
        return {
            "available_qualities": qualities,
            "raw_links": links
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get qualities: {str(e)}")

@app.post("/download")
async def start_download_endpoint(request: DownloadRequest, background_tasks: BackgroundTasks):
    """Start downloading episodes in the background"""
    try:
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Get episodes for the anime
        session_manager = get_session_manager()
        all_episodes = get_all_episodes(session_manager, request.anime_session)
        selected_episodes = [ep for ep in all_episodes if ep["episode"] in request.episodes]
        
        if not selected_episodes:
            raise HTTPException(status_code=404, detail="No matching episodes found")
        
        # Create download task
        task = DownloadTask(
            task_id=task_id,
            status="pending",
            progress=0.0,
            total_episodes=len(selected_episodes),
            created_at=datetime.now()
        )
        download_tasks[task_id] = task
        
        # Start download in background
        background_tasks.add_task(
            download_episodes_background,
            task_id,
            request.anime_session,
            selected_episodes,
            request.quality,
            request.language,
            request.download_directory
        )
        
        return {"task_id": task_id, "message": f"Download started for {len(selected_episodes)} episodes"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start download: {str(e)}")

@app.get("/download/{task_id}")
async def get_download_status(task_id: str):
    """Get download task status and progress"""
    if task_id not in download_tasks:
        raise HTTPException(status_code=404, detail="Download task not found")
    
    return download_tasks[task_id]

@app.get("/downloads")
async def list_download_tasks():
    """List all download tasks"""
    return {"tasks": list(download_tasks.values())}

@app.delete("/download/{task_id}")
async def cancel_download_task(task_id: str):
    """Cancel a download task (if possible)"""
    if task_id not in download_tasks:
        raise HTTPException(status_code=404, detail="Download task not found")
    
    task = download_tasks[task_id]
    if task.status in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel {task.status} task")
    
    task.status = "cancelled"
    return {"message": "Download task cancelled"}

async def download_episodes_background(
    task_id: str,
    anime_session: str,
    episodes: List[Dict[str, Any]],
    quality: str,
    language: str,
    download_directory: str
):
    """Background task to download episodes"""
    task = download_tasks[task_id]
    task.status = "running"
    
    try:
        for i, episode in enumerate(episodes):
            task.current_episode = episode["episode"]
            task.progress = (i / len(episodes)) * 100
            
            print(f"🎬 Processing Episode {episode['episode']}")
            
            # Get download links
            links = scrape_download_links(anime_session, episode["session"])
            raw_url = links.get(f"{quality}_{language}")
            
            if not raw_url:
                print(f"⚠️ {quality}p {language.upper()} not available for episode {episode['episode']}")
                continue
            
            # Resolve download info
            download_info = resolve_download_info(raw_url)
            if not download_info:
                print(f"⚠️ Could not resolve download info for episode {episode['episode']}")
                continue
            
            # Set filename if not extracted
            if not download_info.get('filename'):
                download_info['filename'] = f"Episode_{episode['episode']}"
            
            # Download episode
            success = advanced_download_with_progress(download_info, download_directory)
            if not success:
                print(f"❌ Failed to download episode {episode['episode']}")
        
        # Mark task as completed
        task.status = "completed"
        task.progress = 100.0
        task.completed_at = datetime.now()
        print(f"✅ All episodes downloaded for task {task_id}")
        
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        print(f"❌ Download task {task_id} failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
