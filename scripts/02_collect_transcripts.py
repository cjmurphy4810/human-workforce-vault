#!/usr/bin/env python3
"""Phase 3: Download transcripts for all indexed videos."""

import json
import re
import subprocess
import sys
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

ROOT = Path(__file__).parent.parent
_config_path = Path.cwd() / "config.json" if (Path.cwd() / "config.json").exists() else ROOT / "config.json"
CONFIG = json.loads(_config_path.read_text())
_config_root = _config_path.parent

TRANSCRIPT_DIR = _config_root / "youtube" / "transcripts"
INDEX_PATH = _config_root / "youtube" / "metadata" / "index.json"

DRY_RUN = "--dry-run" in sys.argv
FORCE = "--force" in sys.argv


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text[:70]


def clean_transcript(snippets: list[dict]) -> str:
    lines = []
    prev = ""
    for s in snippets:
        text = s.get("text", "").strip()
        text = re.sub(r"\[.*?\]", "", text).strip()  # remove [Music], [Applause], etc.
        if text and text != prev:
            lines.append(text)
            prev = text
    raw = " ".join(lines)
    # Break into paragraphs every ~500 chars at sentence boundaries
    sentences = re.split(r"(?<=[.!?])\s+", raw)
    paragraphs, current = [], []
    char_count = 0
    for sent in sentences:
        current.append(sent)
        char_count += len(sent)
        if char_count > 500:
            paragraphs.append(" ".join(current))
            current, char_count = [], 0
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs)


def fetch_via_api(video_id: str) -> str | None:
    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=["en", "en-US"])
        # Convert FetchedTranscript snippets (dataclass objects) to dicts
        snippets = [{"text": s.text} for s in fetched]
        return clean_transcript(snippets)
    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    except Exception as e:
        print(f"    API error for {video_id}: {e}")
        return None


def fetch_via_ytdlp(video_id: str, tmp_dir: Path) -> str | None:
    url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = [
        "yt-dlp", "--write-auto-sub", "--sub-lang", "en",
        "--skip-download", "--sub-format", "vtt",
        "-o", str(tmp_dir / "%(id)s.%(ext)s"), url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    vtt_files = list(tmp_dir.glob(f"{video_id}*.vtt"))
    if not vtt_files:
        return None
    vtt_text = vtt_files[0].read_text(encoding="utf-8")
    # Strip VTT formatting
    lines = vtt_text.splitlines()
    clean = []
    prev = ""
    for line in lines:
        line = line.strip()
        if "-->" in line or not line or line.startswith("WEBVTT") or line.isdigit():
            continue
        line = re.sub(r"<[^>]+>", "", line)
        if line and line != prev:
            clean.append(line)
            prev = line
    return " ".join(clean)


def write_transcript_file(entry: dict, text: str) -> Path:
    slug = slugify(entry["title"])
    filename = TRANSCRIPT_DIR / f"episode-{entry['index']:03d}-{slug}.md"
    if filename.exists() and not FORCE:
        return filename
    content = f"""# Transcript: {entry['title']}

**Video ID:** {entry['video_id']}
**URL:** {entry['url']}
**Episode:** {entry['index']:03d}

---

{text}
"""
    if not DRY_RUN:
        filename.write_text(content, encoding="utf-8")
    return filename


def main() -> None:
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    index = json.loads(INDEX_PATH.read_text())

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for entry in index:
            vid_id = entry["video_id"]
            slug = slugify(entry["title"])
            out_path = TRANSCRIPT_DIR / f"episode-{entry['index']:03d}-{slug}.md"

            if out_path.exists() and not FORCE:
                print(f"  [SKIP] {entry['title'][:60]} (exists)")
                entry["transcript_file"] = str(out_path.relative_to(_config_root))
                continue

            print(f"  [{entry['index']:03d}] {entry['title'][:60]}")
            text = fetch_via_api(vid_id) or fetch_via_ytdlp(vid_id, tmp_path)

            if text:
                path = write_transcript_file(entry, text)
                entry["transcript_file"] = str(path.relative_to(_config_root))
                print(f"         → saved ({len(text)} chars)")
            else:
                entry["transcript_file"] = None
                print(f"         → no transcript available")

    if not DRY_RUN:
        INDEX_PATH.write_text(json.dumps(index, indent=2))
    print(f"\nDone. {sum(1 for e in index if e.get('transcript_file'))} transcripts collected.")


if __name__ == "__main__":
    main()
