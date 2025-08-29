from session_mgr import SessionManager
from api_client import search_anime, get_all_episodes
from scraper import scrape_download_links
from resolver import resolve_download_info, resolve_download_url
from transfer import download_with_progress, advanced_download_with_progress


def main():
    sm = SessionManager()
    query = input("Enter anime name: ").strip()
    if not query:
        print("No query entered.")
        return
    print("🔎 Searching…")
    results = search_anime(sm, query)
    if not results:
        print("No results.")
        return
    print("\nSearch results:")
    for i, a in enumerate(results, 1):
        print(f"{i:2d}. {a.get('title')}  "
              f"[type: {a.get('type','?')}, eps: {a.get('episodes','?')}, id: {a.get('id')}]")
    try:
        idx = int(input("\nSelect number: ")) - 1
        if idx < 0 or idx >= len(results):
            print("Invalid selection.")
            return
    except Exception:
        print("Invalid input.")
        return
    selected = results[idx]
    anime_session = selected["session"]
    print(f"\n📺 Fetching episodes for: {selected['title']} (session={anime_session})…")
    eps = get_all_episodes(sm, anime_session)
    print(f"✅ Total episodes fetched: {len(eps)}")
    selection = input("\nEnter episode selection (all, 1-20, 5,10,15): ").strip().lower()
    if selection == "all":
        chosen_eps = eps
    elif "-" in selection:
        start, end = map(int, selection.split("-"))
        chosen_eps = [e for e in eps if start <= e["episode"] <= end]
    else:
        nums = [int(x) for x in selection.split(",") if x.isdigit()]
        chosen_eps = [e for e in eps if e["episode"] in nums]
    print(f"📥 Selected {len(chosen_eps)} episodes for download.")

    # Scrape the first episode to detect available qualities/languages
    first_ep = chosen_eps[0]
    print(f"\n🔎 Checking available qualities for Episode {first_ep['episode']}...")
    links = scrape_download_links(anime_session, first_ep["session"])

    if not links:
        print("⚠️ Could not detect available qualities, aborting.")
        return

    available_qualities = sorted(set(k.split("_")[0] for k in links.keys()))
    print("Available qualities:", ", ".join(available_qualities))

    q_choice = input(f"Enter preferred quality [{available_qualities[0]}]: ").strip() or available_qualities[0]

    available_langs = [k.split("_")[1] for k in links.keys() if k.startswith(q_choice)]
    if len(available_langs) == 1:
        lang_choice = available_langs[0]
        print(f"✅ Only {lang_choice.upper()} available for {q_choice}p, auto-selected.")
    else:
        print(f"Available languages for {q_choice}p:", ", ".join(available_langs))
        lang_choice = input(f"Enter language [{available_langs[0]}]: ").strip().lower() or available_langs[0]

    for e in chosen_eps:
        print(f"\n🎬 Episode {e['episode']}")
        links = scrape_download_links(anime_session, e["session"])

        raw_url = links.get(f"{q_choice}_{lang_choice}")
        if not raw_url:
            print(f"⚠️ {q_choice}p {lang_choice.upper()} not available for this episode.")
            print("Available:", ", ".join(links.keys()))
            continue

        # Use the new advanced download system
        download_info = resolve_download_info(raw_url)
        if not download_info:
            print("⚠️ Could not resolve download information.")
            continue

        # Use extracted filename or fallback to custom format
        if not download_info.get('filename'):
            download_info['filename'] = f"{selected['title']} - Ep{e['episode']}"

        # Download with the advanced function
        success = advanced_download_with_progress(download_info)
        if success:
            print(f"✅ Episode {e['episode']} downloaded successfully")
        else:
            print(f"❌ Failed to download Episode {e['episode']}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBye.")

 
