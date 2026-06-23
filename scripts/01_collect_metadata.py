#!/usr/bin/env python3
"""Phase 2: Collect YouTube video metadata from channel/playlist using yt-dlp."""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
# Allow tests (or manual runs from a different cwd) to supply their own config.json
_cwd_config = Path.cwd() / "config.json"
_config_path = _cwd_config if _cwd_config.exists() else ROOT / "config.json"
CONFIG = json.loads(_config_path.read_text())
# Output directory is always relative to the config we loaded
_config_root = _config_path.parent
METADATA_DIR = _config_root / "youtube" / "metadata"

DRY_RUN = "--dry-run" in sys.argv
FORCE = "--force" in sys.argv


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text[:70]


def fetch_video_list(url: str) -> list[dict]:
    cmd = ["yt-dlp", "--dump-json", "--flat-playlist", "--no-warnings", url]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return [json.loads(line) for line in result.stdout.strip().splitlines() if line.strip()]


def format_duration(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def write_metadata_file(video: dict, index: int) -> Path:
    raw_date = video.get("upload_date") or "00000000"
    date_str = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
    slug = slugify(video.get("title") or "untitled")
    filepath = METADATA_DIR / f"{date_str}-{slug}.md"

    if filepath.exists() and not FORCE:
        return filepath

    vid_id = video.get("id") or video.get("url", "").split("v=")[-1]
    duration = format_duration(int(video.get("duration") or 0))

    content = f"""# {video.get("title", "Untitled")}

**Episode Index:** {index:03d}
**Video ID:** {vid_id}
**URL:** https://www.youtube.com/watch?v={vid_id}
**Published:** {date_str}
**Duration:** {duration}

## Description

{video.get("description") or "_No description available._"}
"""
    if not DRY_RUN:
        filepath.write_text(content, encoding="utf-8")
    return filepath


def main() -> None:
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    url = CONFIG["channel_url"]
    print(f"Fetching video list from: {url}")
    videos = fetch_video_list(url)
    print(f"Found {len(videos)} videos.")

    index_data = []
    for i, video in enumerate(videos, start=1):
        filepath = write_metadata_file(video, i)
        vid_id = video.get("id") or ""
        entry = {
            "index": i,
            "video_id": vid_id,
            "title": video.get("title") or "Untitled",
            "upload_date": video.get("upload_date") or "",
            "duration_seconds": int(video.get("duration") or 0),
            "url": f"https://www.youtube.com/watch?v={vid_id}",
            "metadata_file": str(filepath.relative_to(_config_root)),
        }
        index_data.append(entry)
        print(f"  [{i:03d}] {entry['title'][:65]}")

    if not DRY_RUN:
        index_path = METADATA_DIR / "index.json"
        index_path.write_text(json.dumps(index_data, indent=2), encoding="utf-8")
        print(f"\nSaved index to {index_path}")
    else:
        print("\n[dry-run] No files written.")


if __name__ == "__main__":
    main()
