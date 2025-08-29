import time
import urllib.parse
from config import API_BASE


def search_anime(sm, query: str):
    q = urllib.parse.quote_plus(query)
    url = f"{API_BASE}?m=search&q={q}"
    r = sm.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()
    return data.get("data", [])


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


