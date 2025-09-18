#!/usr/bin/env python3
import os
import re
import sys
from typing import Tuple
from datetime import datetime

import requests

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
README_PATH = os.path.join(REPO_ROOT, "README.md")

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
CHANNEL_HANDLE = os.getenv("YOUTUBE_CHANNEL_HANDLE", "@pappuraj").strip()

HEADERS = {"User-Agent": "github.com/pappuraj README updater (YT stats)"}


def resolve_channel_id(handle: str) -> str:
    # Use YouTube Data API search to resolve handle to channelId
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": handle,
        "type": "channel",
        "maxResults": 1,
        "key": YOUTUBE_API_KEY,
    }
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    items = data.get("items", [])
    if not items:
        raise RuntimeError("Channel not found from handle search")
    return items[0]["snippet"]["channelId"]


def fetch_channel_stats(channel_id: str) -> Tuple[int, int, int]:
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "statistics",
        "id": channel_id,
        "key": YOUTUBE_API_KEY,
    }
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    items = data.get("items", [])
    if not items:
        raise RuntimeError("No statistics found for channel")
    stats = items[0]["statistics"]
    subs = int(stats.get("subscriberCount", 0))
    views = int(stats.get("viewCount", 0))
    videos = int(stats.get("videoCount", 0))
    return subs, views, videos


def replace_between_markers(content: str, new_block: str, start_marker: str, end_marker: str) -> str:
    pattern = re.compile(
        rf"(<!--\s*{re.escape(start_marker)}\s*-->)([\s\S]*?)(<!--\s*{re.escape(end_marker)}\s*-->)",
        re.MULTILINE,
    )
    replacement = rf"\1\n{new_block}\n\3"
    if not pattern.search(content):
        raise RuntimeError("YT_STATS markers not found in README.")
    return pattern.sub(replacement, content)


def main() -> int:
    try:
        if not YOUTUBE_API_KEY:
            raise RuntimeError("YOUTUBE_API_KEY is not set")
        channel_id = resolve_channel_id(CHANNEL_HANDLE)
        subs, views, videos = fetch_channel_stats(channel_id)
        block = (
            f"Subscribers: {subs:,}\n"
            f"Views: {views:,}\n"
            f"Videos: {videos:,}\n\n"
            f"_Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_"
        )
        with open(README_PATH, "r", encoding="utf-8") as f:
            readme = f.read()
        updated = replace_between_markers(readme, block, "YT_STATS:START", "YT_STATS:END")
        if updated != readme:
            with open(README_PATH, "w", encoding="utf-8") as f:
                f.write(updated)
            print("README updated with YouTube stats.")
        else:
            print("No changes to README.")
        return 0
    except Exception as e:
        try:
            with open(README_PATH, "r", encoding="utf-8") as f:
                readme = f.read()
            fallback = (
                "Subscribers: n/a\nViews: n/a\nVideos: n/a\n\n"
                f"_Last attempted: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_"
            )
            updated = replace_between_markers(readme, fallback, "YT_STATS:START", "YT_STATS:END")
            with open(README_PATH, "w", encoding="utf-8") as f:
                f.write(updated)
        except Exception:
            pass
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
