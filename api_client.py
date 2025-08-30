import time
import urllib.parse
import requests
from config import API_BASE


def search_anime(sm, query: str, max_retries=3):
    """Search for anime with retry logic for better reliability"""
    q = urllib.parse.quote_plus(query)
    url = f"{API_BASE}?m=search&q={q}"
    
    for attempt in range(max_retries):
        try:
            print(f"🔍 Search attempt {attempt + 1}/{max_retries} for '{query}'...")
            r = sm.get(url, timeout=30)  # Increased timeout
            r.raise_for_status()
            data = r.json()
            results = data.get("data", [])
            print(f"✅ Search successful! Found {len(results)} results")
            return results
            
        except requests.exceptions.ConnectTimeout as e:
            print(f"⚠️ Connection timeout (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise Exception(f"Failed to connect to animepahe.ru after {max_retries} attempts. The site may be temporarily unavailable.")
            time.sleep(2 ** attempt)  # Exponential backoff
            
        except requests.exceptions.ConnectionError as e:
            print(f"⚠️ Connection error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise Exception(f"Cannot connect to animepahe.ru. Please check your internet connection or try again later.")
            time.sleep(2 ** attempt)
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Request error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise Exception(f"API request failed: {str(e)}")
            time.sleep(2 ** attempt)
            
        except Exception as e:
            print(f"❌ Unexpected error during search: {e}")
            raise
    
    return []


def get_all_episodes(sm, anime_session: str):
    episodes = []
    page = 1
    while True:
        url = f"{API_BASE}?m=release&id={anime_session}&sort=episode_asc&page={page}"
        print(f"📄 Fetching page {page} -> {url}")
        r = sm.get(url, timeout=30)
        if r.status_code != 200:
            print(f"⚠️ page {page} -> HTTP {r.status_code}; stopping.")
            break
        data = r.json()
        chunk = data.get("data", [])
        if not chunk:
            break
        print(f"   Retrieved {len(chunk)} episodes on page {page}")
        episodes.extend(chunk)
        last_page = data.get("last_page")
        if last_page and page >= int(last_page):
            break
        page += 1
        time.sleep(0.75)
    return episodes


