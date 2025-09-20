#!/usr/bin/env python3
import os
import re
import sys
from typing import Tuple
from datetime import datetime, timezone

import requests

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
README_PATH = os.path.join(REPO_ROOT, "README.md")

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
CHANNEL_HANDLE = os.getenv("YOUTUBE_CHANNEL_HANDLE", "@pappuraj").strip()
CHANNEL_ID_ENV = os.getenv("YOUTUBE_CHANNEL_ID", "").strip()

HEADERS = {"User-Agent": "github.com/pappuraj README updater (YT stats)"}


def _now_utc_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def resolve_channel_id_from_search(handle: str) -> str:
    """
    Resolve a YouTube channel ID from a handle (e.g., '@pappuraj') using the Search API.
    NOTE: In the Search API, the channel ID is in items[0]['id']['channelId'], not in snippet.
    """
    if handle.startswith("@"):
        query = handle
    else:
        query = f"@{handle}"

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "id",
        "q": query,
        "type": "channel",
        "maxResults": 1,
        "key": YOUTUBE_API_KEY,
    }
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    items = data.get("items", [])
    if not items or "id" not in items[0] or "channelId" not in items[0]["id"]:
        raise RuntimeError(f"Channel not found from handle search for '{handle}'")
    return items[0]["id"]["channelId"]


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
        raise RuntimeError("No statistics found for channel (check channel ID and API quota).")
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

        # Prefer explicit channel ID if provided; otherwise resolve from handle.
        if CHANNEL_ID_ENV:
            channel_id = CHANNEL_ID_ENV
        else:
            channel_id = resolve_channel_id_from_search(CHANNEL_HANDLE)

        subs, views, videos = fetch_channel_stats(channel_id)
        block = (
            f"Subscribers: {subs:,}\n"
            f"Views: {views:,}\n"
            f"Videos: {videos:,}\n\n"
            f"_Last updated: {_now_utc_str()}_"
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
        # Best-effort fallback: write attempt timestamp so your README still reflects recency.
        try:
            with open(README_PATH, "r", encoding="utf-8") as f:
                readme = f.read()
            fallback = (
                "Subscribers: n/a\nViews: n/a\nVideos: n/a\n\n"
                f"_Last attempted: {_now_utc_str()}_"
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
