#!/usr/bin/env python3
import os
import re
import sys
import json
from datetime import datetime
from typing import List, Dict, Any

import requests

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
README_PATH = os.path.join(REPO_ROOT, "README.md")
DEFAULT_ORCID = "0009-0002-0202-7891"
ENV_ORCID = os.getenv("ORCID_ID", "").strip()
ORCID_ID = ENV_ORCID if ENV_ORCID else DEFAULT_ORCID
MAX_ITEMS = int(os.getenv("MAX_PUBLICATIONS", "10"))

OPENALEX_BASE = "https://api.openalex.org"
HEADERS = {"User-Agent": "github.com/pappuraj README updater (contact: pappuraj.duet@gmail.com)"}


def fetch_author_id_by_orcid(orcid_id: str) -> str | None:
    url = f"{OPENALEX_BASE}/authors"
    params = {"filter": f"orcid:{orcid_id}", "per_page": 1}
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    results = data.get("results", [])
    if not results:
        return None
    return results[0]["id"]


def fetch_works_by_author(author_id: str, max_items: int) -> List[Dict[str, Any]]:
    url = f"{OPENALEX_BASE}/works"
    params = {
        "filter": f"author.id:{author_id}",
        "sort": "publication_year:desc",
        "per_page": max_items,
    }
    r = requests.get(url, params=params, headers=HEADERS, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data.get("results", [])


def format_publication_item(work: Dict[str, Any]) -> str:
    title = (work.get("title") or "Untitled").strip()
    year = work.get("publication_year") or (work.get("from_publication_date", "")[:4] or "")
    venue = (
        (work.get("host_venue", {}) or {}).get("display_name")
        or (work.get("primary_location", {}) or {}).get("source", {}).get("display_name")
        or ""
    )
    doi = work.get("doi")
    doi_url = f"https://doi.org/{doi}" if doi else None
    openalex_url = work.get("id") or None

    parts: List[str] = []
    if doi_url:
        parts.append(f"**[{title}]({doi_url})**")
    elif openalex_url:
        parts.append(f"**[{title}]({openalex_url})**")
    else:
        parts.append(f"**{title}**")

    meta_bits: List[str] = []
    if venue:
        meta_bits.append(venue)
    if year:
        meta_bits.append(str(year))
    if meta_bits:
        parts.append(f" — {', '.join(meta_bits)}")

    links_bits: List[str] = []
    if doi_url:
        links_bits.append(f"[DOI]({doi_url})")
    if openalex_url:
        links_bits.append(f"[OpenAlex]({openalex_url})")
    if links_bits:
        parts.append(f" ({' · '.join(links_bits)})")

    return "".join(parts)


def build_markdown_list(works: List[Dict[str, Any]]) -> str:
    if not works:
        lines = [
            "- No publications found yet for this ORCID in OpenAlex.",
            "",
            f"_Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_",
        ]
        return "\n".join(lines)

    lines: List[str] = []
    for w in works:
        lines.append(f"- {format_publication_item(w)}")
    lines.append("")
    lines.append(f"_Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_")
    return "\n".join(lines)


def replace_between_markers(content: str, new_block: str, start_marker: str, end_marker: str) -> str:
    import re as _re
    pattern = _re.compile(
        rf"(<!--\s*{_re.escape(start_marker)}\s*-->)([\s\S]*?)(<!--\s*{_re.escape(end_marker)}\s*-->)",
        _re.MULTILINE,
    )
    replacement = rf"\1\n{new_block}\n\3"
    if not pattern.search(content):
        raise RuntimeError("Publication markers not found in README.")
    return pattern.sub(replacement, content)


def write_status_to_readme(message: str) -> None:
    with open(README_PATH, "r", encoding="utf-8") as f:
        readme = f.read()
    updated = replace_between_markers(
        readme,
        message,
        start_marker="PUBLICATIONS:START",
        end_marker="PUBLICATIONS:END",
    )
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated)


def main() -> int:
    try:
        author_id = fetch_author_id_by_orcid(ORCID_ID)
        if not author_id:
            md_block = build_markdown_list([])
            write_status_to_readme(md_block)
            print(f"No OpenAlex author found for ORCID {ORCID_ID}. Updated README with placeholder.")
            return 0

        works = fetch_works_by_author(author_id, MAX_ITEMS)
        md_block = build_markdown_list(works)
        write_status_to_readme(md_block)
        print("README updated with latest publications.")
        return 0
    except Exception as e:
        fallback = (
            "- Unable to fetch publications right now. Please try again later.\n\n"
            f"_Last attempted: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_"
        )
        try:
            write_status_to_readme(fallback)
        except Exception:
            pass
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
