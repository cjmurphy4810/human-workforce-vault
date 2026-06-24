# Human Workforce Knowledge Vault Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully automated Python pipeline that ingests every Human Workforce YouTube video, generates AI-powered summaries and analysis, and outputs a structured knowledge vault ready for NotebookLM, Claude Projects, and book/content development.

**Architecture:** A series of standalone Python scripts, each reading from the vault directory and writing to it, run in sequence by a top-level pipeline runner. AI analysis uses the Anthropic SDK (claude-haiku-4-5 for cost-efficient bulk processing, claude-sonnet-4-6 for the final intelligence report). All outputs are Markdown or JSON — no database required.

**Tech Stack:** Python 3.11+, yt-dlp, youtube-transcript-api, anthropic SDK, pyyaml, python-slugify

## Global Constraints

- All vault files live under `HumanWorkforceVault/` (the project root)
- Metadata filenames: `YYYY-MM-DD-slug.md`; transcript/summary filenames: `episode-NNN-slug.md`
- Never overwrite an existing file unless `--force` flag passed — allow safe reruns
- All AI calls must use the model specified in `config.json`; never hardcode model names
- Every script accepts `--dry-run` to print what it would do without writing files
- API key read from environment variable `ANTHROPIC_API_KEY`; never hardcoded
- YouTube channel/playlist URL stored in `config.json` — never hardcoded in scripts

---

## File Map

```
HumanWorkforceVault/
├── config.json                          # Channel URL, model, speaker list, categories
├── requirements.txt                     # All Python dependencies
├── .env.example                         # Template for ANTHROPIC_API_KEY
├── scripts/
│   ├── 01_collect_metadata.py           # yt-dlp metadata extraction → youtube/metadata/
│   ├── 02_collect_transcripts.py        # youtube-transcript-api + yt-dlp fallback → youtube/transcripts/
│   ├── 03_summarize_episodes.py         # Claude haiku per transcript → youtube/summaries/
│   ├── 04_extract_entities_topics.py    # Claude haiku per transcript → taxonomy/
│   ├── 05_build_knowledge_graph.py      # Co-occurrence analysis → taxonomy/knowledge-graph.json
│   ├── 06_build_master_index.py         # Aggregates topics.json → topic-index/master-index.md
│   ├── 07_build_speaker_index.py        # Searches transcripts for known speakers → speaker-index/
│   ├── 08_generate_shorts.py            # Claude haiku per summary → shorts/
│   ├── 09_prepare_notebooklm.py         # Concatenates vault content → notebooklm/
│   ├── 10_generate_report.py            # Claude sonnet full vault → exports/
│   └── run_pipeline.py                  # Runs scripts 01-10 in sequence with checkpoints
├── source/
├── youtube/
│   ├── metadata/
│   │   └── index.json                   # Master list of all videos with file pointers
│   ├── transcripts/
│   └── summaries/
├── jellypod/
│   ├── scripts/
│   └── summaries/
├── books/
│   ├── last-job-youll-ever-hate/
│   ├── club-genius/
│   ├── human-disadvantage/
│   ├── agentic-insider/
│   └── future-books/
├── research/
├── topic-index/
├── speaker-index/
├── shorts/
├── taxonomy/
├── notebooklm/
│   └── topic-guides/
└── exports/
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `HumanWorkforceVault/config.json`
- Create: `HumanWorkforceVault/requirements.txt`
- Create: `HumanWorkforceVault/.env.example`
- Create: `HumanWorkforceVault/scripts/` (empty dir)
- Create: all vault subdirectories

**Interfaces:**
- Produces: `config.json` used by every subsequent script

- [ ] **Step 1: Create the full folder structure**

Run from `HumanWorkforceVault/`:

```bash
mkdir -p scripts source \
  youtube/metadata youtube/transcripts youtube/summaries \
  jellypod/scripts jellypod/summaries \
  books/last-job-youll-ever-hate books/club-genius \
  books/human-disadvantage books/agentic-insider books/future-books \
  research topic-index speaker-index shorts \
  taxonomy notebooklm/topic-guides exports
```

- [ ] **Step 2: Create `config.json`**

```json
{
  "channel_url": "PASTE_YOUR_YOUTUBE_CHANNEL_OR_PLAYLIST_URL_HERE",
  "model_bulk": "claude-haiku-4-5-20251001",
  "model_report": "claude-sonnet-4-6",
  "speakers": [
    "Simon Carver",
    "Lachlan Reed",
    "CJ Murphy",
    "Jack Burns",
    "Dr. Zara Sterling",
    "Jacques San Dimas",
    "Mariana Costa",
    "Sofia Navarro"
  ],
  "primary_categories": [
    "Agentic AI",
    "Generative AI",
    "Future of Work",
    "Business Continuity",
    "Operational Resilience",
    "Risk Management",
    "Cybersecurity",
    "Governance",
    "Compliance",
    "Leadership",
    "Productivity",
    "Enterprise Transformation",
    "Automation",
    "Digital Labor",
    "Human Skills",
    "Organizational Design"
  ]
}
```

- [ ] **Step 3: Create `requirements.txt`**

```text
yt-dlp>=2024.1.0
youtube-transcript-api>=0.6.2
anthropic>=0.40.0
pyyaml>=6.0
python-slugify>=8.0.4
```

- [ ] **Step 4: Create `.env.example`**

```bash
ANTHROPIC_API_KEY=your_key_here
```

- [ ] **Step 5: Install dependencies and verify**

```bash
pip install -r requirements.txt
yt-dlp --version
python -c "import anthropic; print('anthropic ok')"
python -c "from youtube_transcript_api import YouTubeTranscriptApi; print('transcript api ok')"
```

Expected: version strings and "ok" messages with no errors.

- [ ] **Step 6: Commit**

```bash
git init
echo ".env" >> .gitignore
echo "__pycache__/" >> .gitignore
git add config.json requirements.txt .env.example .gitignore
git commit -m "feat: scaffold Human Workforce Knowledge Vault project"
```

---

## Task 2: YouTube Metadata Collection

**Files:**
- Create: `scripts/01_collect_metadata.py`
- Produces: `youtube/metadata/YYYY-MM-DD-slug.md` per video + `youtube/metadata/index.json`

**Interfaces:**
- Consumes: `config.json["channel_url"]`
- Produces: `youtube/metadata/index.json` — array of `{index, video_id, title, upload_date, duration_seconds, url, metadata_file}` — used by scripts 02–10

- [ ] **Step 1: Write the test**

Create `tests/test_01_metadata.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

def test_metadata_produces_index(tmp_path, monkeypatch):
    """Run script against a known short public video and verify index.json is written."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "youtube" / "metadata").mkdir(parents=True)
    config = {
        "channel_url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        "model_bulk": "claude-haiku-4-5-20251001",
        "model_report": "claude-sonnet-4-6",
        "speakers": [],
        "primary_categories": []
    }
    (tmp_path / "config.json").write_text(json.dumps(config))

    result = subprocess.run(
        [sys.executable, str(Path(__file__).parents[1] / "scripts" / "01_collect_metadata.py")],
        cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    index = json.loads((tmp_path / "youtube" / "metadata" / "index.json").read_text())
    assert len(index) >= 1
    assert "video_id" in index[0]
    assert "title" in index[0]
    assert "metadata_file" in index[0]
```

- [ ] **Step 2: Run test — expect FAIL (script doesn't exist yet)**

```bash
pytest tests/test_01_metadata.py -v
```

Expected: `FileNotFoundError` or `ModuleNotFoundError`

- [ ] **Step 3: Write `scripts/01_collect_metadata.py`**

```python
#!/usr/bin/env python3
"""Phase 2: Collect YouTube video metadata from channel/playlist using yt-dlp."""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text())
METADATA_DIR = ROOT / "youtube" / "metadata"

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
            "metadata_file": str(filepath.relative_to(ROOT)),
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
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/test_01_metadata.py -v
```

Expected: `PASSED`

- [ ] **Step 5: Smoke test against real channel (after adding your URL to config.json)**

```bash
python scripts/01_collect_metadata.py --dry-run
```

Expected: prints video titles, no files written.

```bash
python scripts/01_collect_metadata.py
```

Expected: `youtube/metadata/index.json` exists, one `.md` per video.

- [ ] **Step 6: Commit**

```bash
git add scripts/01_collect_metadata.py tests/test_01_metadata.py
git commit -m "feat: add YouTube metadata collection script"
```

---

## Task 3: Transcript Collection

**Files:**
- Create: `scripts/02_collect_transcripts.py`
- Produces: `youtube/transcripts/episode-NNN-slug.md` per video

**Interfaces:**
- Consumes: `youtube/metadata/index.json`
- Produces: updates each entry in index.json with `"transcript_file"` key; writes transcript `.md` files

- [ ] **Step 1: Write the test**

Create `tests/test_02_transcripts.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

KNOWN_VIDEO_ID = "jNQXAC9IVRw"  # "Me at the zoo" — first YouTube video, has captions

def test_transcript_fetched(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "youtube" / "transcripts").mkdir(parents=True)
    (tmp_path / "youtube" / "metadata").mkdir(parents=True)

    index = [{
        "index": 1,
        "video_id": KNOWN_VIDEO_ID,
        "title": "Me at the zoo",
        "upload_date": "20050423",
        "duration_seconds": 19,
        "url": f"https://www.youtube.com/watch?v={KNOWN_VIDEO_ID}",
        "metadata_file": "youtube/metadata/2005-04-23-me-at-the-zoo.md"
    }]
    (tmp_path / "youtube" / "metadata" / "index.json").write_text(json.dumps(index))

    config = {
        "channel_url": "",
        "model_bulk": "claude-haiku-4-5-20251001",
        "model_report": "claude-sonnet-4-6",
        "speakers": [],
        "primary_categories": []
    }
    (tmp_path / "config.json").write_text(json.dumps(config))

    result = subprocess.run(
        [sys.executable, str(Path(__file__).parents[1] / "scripts" / "02_collect_transcripts.py")],
        cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr

    transcript_files = list((tmp_path / "youtube" / "transcripts").glob("*.md"))
    assert len(transcript_files) == 1
    content = transcript_files[0].read_text()
    assert len(content) > 50
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_02_transcripts.py -v
```

- [ ] **Step 3: Write `scripts/02_collect_transcripts.py`**

```python
#!/usr/bin/env python3
"""Phase 3: Download transcripts for all indexed videos."""

import json
import re
import subprocess
import sys
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

ROOT = Path(__file__).parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text())
TRANSCRIPT_DIR = ROOT / "youtube" / "transcripts"
INDEX_PATH = ROOT / "youtube" / "metadata" / "index.json"

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
        snippets = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US"])
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
                entry["transcript_file"] = str(out_path.relative_to(ROOT))
                continue

            print(f"  [{entry['index']:03d}] {entry['title'][:60]}")
            text = fetch_via_api(vid_id) or fetch_via_ytdlp(vid_id, tmp_path)

            if text:
                path = write_transcript_file(entry, text)
                entry["transcript_file"] = str(path.relative_to(ROOT))
                print(f"         → saved ({len(text)} chars)")
            else:
                entry["transcript_file"] = None
                print(f"         → no transcript available")

    if not DRY_RUN:
        INDEX_PATH.write_text(json.dumps(index, indent=2))
    print(f"\nDone. {sum(1 for e in index if e.get('transcript_file'))} transcripts collected.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/test_02_transcripts.py -v
```

- [ ] **Step 5: Smoke test**

```bash
python scripts/02_collect_transcripts.py --dry-run
```

Expected: prints episode list with transcript availability, no files written.

- [ ] **Step 6: Commit**

```bash
git add scripts/02_collect_transcripts.py tests/test_02_transcripts.py
git commit -m "feat: add transcript collection with youtube-transcript-api + yt-dlp fallback"
```

---

## Task 4: Episode Summarization

**Files:**
- Create: `scripts/03_summarize_episodes.py`
- Produces: `youtube/summaries/episode-NNN-slug.md` per transcript

**Interfaces:**
- Consumes: `youtube/metadata/index.json`, `youtube/transcripts/*.md`
- Produces: updates index entries with `"summary_file"` key

- [ ] **Step 1: Write the test**

Create `tests/test_03_summarize.py`:

```python
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest

def test_summarize_skips_when_no_api_key(tmp_path, monkeypatch):
    """Without ANTHROPIC_API_KEY, script should exit with clear error."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "youtube" / "metadata").mkdir(parents=True)
    (tmp_path / "youtube" / "transcripts").mkdir(parents=True)
    (tmp_path / "youtube" / "summaries").mkdir(parents=True)

    index = [{"index": 1, "video_id": "abc", "title": "Test", "url": "",
               "upload_date": "", "duration_seconds": 0,
               "metadata_file": "", "transcript_file": None}]
    (tmp_path / "youtube" / "metadata" / "index.json").write_text(json.dumps(index))
    (tmp_path / "config.json").write_text(json.dumps({
        "channel_url": "", "model_bulk": "claude-haiku-4-5-20251001",
        "model_report": "claude-sonnet-4-6", "speakers": [], "primary_categories": []
    }))

    env = {**os.environ, "ANTHROPIC_API_KEY": ""}
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parents[1] / "scripts" / "03_summarize_episodes.py")],
        cwd=tmp_path, capture_output=True, text=True, env=env
    )
    assert result.returncode != 0 or "no transcripts" in result.stdout.lower() or "skip" in result.stdout.lower()
```

- [ ] **Step 2: Run test — expect behavior to be defined by the script not existing yet**

```bash
pytest tests/test_03_summarize.py -v
```

- [ ] **Step 3: Write `scripts/03_summarize_episodes.py`**

```python
#!/usr/bin/env python3
"""Phase 4: Generate AI summaries for each episode transcript."""

import json
import os
import re
import sys
from pathlib import Path

import anthropic

ROOT = Path(__file__).parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text())
INDEX_PATH = ROOT / "youtube" / "metadata" / "index.json"
SUMMARY_DIR = ROOT / "youtube" / "summaries"

DRY_RUN = "--dry-run" in sys.argv
FORCE = "--force" in sys.argv

SUMMARY_PROMPT = """\
You are a knowledge management specialist for The Human Workforce — a platform covering AI, \
Agentic AI, Workforce Transformation, Future of Work, Business Continuity, Operational \
Resilience, Technology Risk, Cybersecurity, AI Governance, Human-Machine Collaboration, \
Enterprise Transformation, Digital Labor, Executive Leadership, and Organizational Change.

Analyze the following podcast transcript and produce a structured summary.

Transcript:
---
{transcript}
---

Respond in this exact Markdown format:

# Executive Summary

[2–5 paragraph narrative summary of the episode]

# Key Themes

- [theme 1]
- [theme 2]
- [theme 3]

# Key Findings

- [finding 1]
- [finding 2]
- [finding 3]

# Actionable Takeaways

- [takeaway 1]
- [takeaway 2]
- [takeaway 3]

# Notable Quotes

> "[quote 1]"

> "[quote 2]"

# Human Workforce Relevance

**AI:** [1–2 sentences]
**Workforce:** [1–2 sentences]
**Leadership:** [1–2 sentences]
**Risk & Governance:** [1–2 sentences]
**Business Continuity:** [1–2 sentences]

# Suggested Future Content

## Episode Ideas
1. [idea 1]
2. [idea 2]
3. [idea 3]
4. [idea 4]
5. [idea 5]

## Shorts Ideas
1. [idea 1]
2. [idea 2]
3. [idea 3]
4. [idea 4]
5. [idea 5]

## Newsletter Ideas
1. [idea 1]
2. [idea 2]
3. [idea 3]
4. [idea 4]
5. [idea 5]
"""


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text[:70]


def summarize(client: anthropic.Anthropic, transcript_text: str, model: str) -> str:
    # Truncate to ~100k chars to stay within context
    truncated = transcript_text[:100_000]
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": SUMMARY_PROMPT.format(transcript=truncated)}]
    )
    return message.content[0].text


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    index = json.loads(INDEX_PATH.read_text())
    client = anthropic.Anthropic(api_key=api_key)
    model = CONFIG["model_bulk"]

    skipped, processed, failed = 0, 0, 0
    for entry in index:
        transcript_path = entry.get("transcript_file")
        if not transcript_path:
            print(f"  [SKIP] {entry['title'][:60]} (no transcript)")
            skipped += 1
            continue

        slug = slugify(entry["title"])
        out_path = SUMMARY_DIR / f"episode-{entry['index']:03d}-{slug}.md"

        if out_path.exists() and not FORCE:
            print(f"  [SKIP] {entry['title'][:60]} (summary exists)")
            entry["summary_file"] = str(out_path.relative_to(ROOT))
            skipped += 1
            continue

        print(f"  [{entry['index']:03d}] Summarizing: {entry['title'][:55]}...")

        if DRY_RUN:
            print("         → [dry-run] skipping API call")
            continue

        try:
            full_path = ROOT / transcript_path
            transcript_text = full_path.read_text(encoding="utf-8")
            summary_md = summarize(client, transcript_text, model)

            header = f"""# Summary: {entry['title']}

**Video ID:** {entry['video_id']}
**URL:** {entry['url']}
**Episode:** {entry['index']:03d}
**Source:** {transcript_path}

---

"""
            out_path.write_text(header + summary_md, encoding="utf-8")
            entry["summary_file"] = str(out_path.relative_to(ROOT))
            processed += 1
            print(f"         → saved")
        except Exception as e:
            print(f"         → ERROR: {e}")
            failed += 1

    if not DRY_RUN:
        INDEX_PATH.write_text(json.dumps(index, indent=2))

    print(f"\nDone. Processed: {processed}, Skipped: {skipped}, Failed: {failed}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/test_03_summarize.py -v
```

- [ ] **Step 5: Smoke test (requires ANTHROPIC_API_KEY set)**

```bash
export ANTHROPIC_API_KEY=your_key_here
python scripts/03_summarize_episodes.py --dry-run
```

Expected: lists episodes with transcript status, no API calls made.

- [ ] **Step 6: Commit**

```bash
git add scripts/03_summarize_episodes.py tests/test_03_summarize.py
git commit -m "feat: add Claude-powered episode summarization"
```

---

## Task 5: Entity Extraction + Topic Classification

**Files:**
- Create: `scripts/04_extract_entities_topics.py`
- Produces: `taxonomy/entities.json`, `taxonomy/topics.json`

**Interfaces:**
- Consumes: `youtube/metadata/index.json`, `youtube/transcripts/*.md`
- Produces: `taxonomy/entities.json` — `{video_id: {people, orgs, products, platforms, concepts, technologies, methodologies, frameworks}}`, `taxonomy/topics.json` — `{video_id: [category, ...]}`

- [ ] **Step 1: Write `scripts/04_extract_entities_topics.py`**

```python
#!/usr/bin/env python3
"""Phase 5+6: Extract entities and classify topics for each episode."""

import json
import os
import re
import sys
from pathlib import Path

import anthropic

ROOT = Path(__file__).parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text())
INDEX_PATH = ROOT / "youtube" / "metadata" / "index.json"
TAXONOMY_DIR = ROOT / "taxonomy"

DRY_RUN = "--dry-run" in sys.argv
FORCE = "--force" in sys.argv

EXTRACT_PROMPT = """\
Analyze this podcast transcript and return a JSON object with two keys:

"entities": {{
  "people": ["name", ...],
  "organizations": ["name", ...],
  "products": ["name", ...],
  "platforms": ["name", ...],
  "concepts": ["name", ...],
  "technologies": ["name", ...],
  "methodologies": ["name", ...],
  "frameworks": ["name", ...]
}},
"topics": ["category1", "category2", ...]

For topics, choose only from these categories:
{categories}

Transcript (excerpt):
---
{transcript}
---

Return ONLY valid JSON. No explanation, no markdown fences.
"""


def extract(client: anthropic.Anthropic, transcript_text: str, model: str) -> dict:
    categories = json.dumps(CONFIG["primary_categories"])
    truncated = transcript_text[:60_000]
    message = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": EXTRACT_PROMPT.format(
            categories=categories, transcript=truncated
        )}]
    )
    raw = message.content[0].text.strip()
    # Strip any accidental markdown fences
    raw = re.sub(r"^```json?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    TAXONOMY_DIR.mkdir(parents=True, exist_ok=True)
    index = json.loads(INDEX_PATH.read_text())
    client = anthropic.Anthropic(api_key=api_key)
    model = CONFIG["model_bulk"]

    entities_out: dict = {}
    topics_out: dict = {}

    # Load existing data to allow incremental runs
    entities_path = TAXONOMY_DIR / "entities.json"
    topics_path = TAXONOMY_DIR / "topics.json"
    if entities_path.exists() and not FORCE:
        entities_out = json.loads(entities_path.read_text())
    if topics_path.exists() and not FORCE:
        topics_out = json.loads(topics_path.read_text())

    for entry in index:
        vid_id = entry["video_id"]
        if vid_id in entities_out and vid_id in topics_out and not FORCE:
            print(f"  [SKIP] {entry['title'][:60]}")
            continue

        transcript_path = entry.get("transcript_file")
        if not transcript_path:
            print(f"  [SKIP] {entry['title'][:60]} (no transcript)")
            continue

        print(f"  [{entry['index']:03d}] Extracting: {entry['title'][:55]}...")
        if DRY_RUN:
            print("         → [dry-run]")
            continue

        try:
            text = (ROOT / transcript_path).read_text(encoding="utf-8")
            result = extract(client, text, model)
            entities_out[vid_id] = result.get("entities", {})
            topics_out[vid_id] = result.get("topics", [])
            print(f"         → {len(result.get('topics', []))} topics, "
                  f"{sum(len(v) for v in result.get('entities', {}).values())} entities")
        except Exception as e:
            print(f"         → ERROR: {e}")

    if not DRY_RUN:
        entities_path.write_text(json.dumps(entities_out, indent=2))
        topics_path.write_text(json.dumps(topics_out, indent=2))
        print(f"\nSaved {entities_path} and {topics_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke test**

```bash
python scripts/04_extract_entities_topics.py --dry-run
```

- [ ] **Step 3: Commit**

```bash
git add scripts/04_extract_entities_topics.py
git commit -m "feat: add entity extraction and topic classification"
```

---

## Task 6: Knowledge Graph

**Files:**
- Create: `scripts/05_build_knowledge_graph.py`
- Produces: `taxonomy/knowledge-graph.json`

**Interfaces:**
- Consumes: `taxonomy/entities.json`, `taxonomy/topics.json`, `youtube/metadata/index.json`
- Produces: `taxonomy/knowledge-graph.json` — nodes (episodes, concepts, topics) + edges (co-occurrence, shared-topic)

- [ ] **Step 1: Write `scripts/05_build_knowledge_graph.py`**

```python
#!/usr/bin/env python3
"""Phase 7: Build a knowledge graph from entity and topic co-occurrence."""

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
INDEX_PATH = ROOT / "youtube" / "metadata" / "index.json"
ENTITIES_PATH = ROOT / "taxonomy" / "entities.json"
TOPICS_PATH = ROOT / "taxonomy" / "topics.json"
OUTPUT_PATH = ROOT / "taxonomy" / "knowledge-graph.json"


def build_graph(index: list, entities: dict, topics: dict) -> dict:
    nodes = []
    edges = []

    episode_map = {e["video_id"]: e for e in index}

    # Episode nodes
    for entry in index:
        nodes.append({
            "id": f"episode:{entry['video_id']}",
            "type": "episode",
            "label": entry["title"],
            "index": entry["index"],
            "video_id": entry["video_id"],
        })

    # Concept nodes (deduplicated across all entity types)
    concept_episodes: dict[str, list[str]] = defaultdict(list)
    for vid_id, ent_map in entities.items():
        for category, items in ent_map.items():
            for item in items:
                key = f"{category}:{item.lower()}"
                concept_episodes[key].append(vid_id)

    for key, vid_ids in concept_episodes.items():
        category, label = key.split(":", 1)
        nodes.append({
            "id": f"concept:{key}",
            "type": "concept",
            "category": category,
            "label": label,
            "episode_count": len(vid_ids),
        })
        for vid_id in vid_ids:
            edges.append({
                "source": f"episode:{vid_id}",
                "target": f"concept:{key}",
                "relation": "mentions",
            })

    # Topic nodes
    topic_episodes: dict[str, list[str]] = defaultdict(list)
    for vid_id, topic_list in topics.items():
        for topic in topic_list:
            topic_episodes[topic].append(vid_id)

    for topic, vid_ids in topic_episodes.items():
        nodes.append({
            "id": f"topic:{topic}",
            "type": "topic",
            "label": topic,
            "episode_count": len(vid_ids),
        })
        for vid_id in vid_ids:
            edges.append({
                "source": f"episode:{vid_id}",
                "target": f"topic:{topic}",
                "relation": "covers",
            })

    # Related episode edges (episodes sharing 2+ topics)
    ep_topics: dict[str, set] = {vid: set(t_list) for vid, t_list in topics.items()}
    vid_ids_list = list(ep_topics.keys())
    for i in range(len(vid_ids_list)):
        for j in range(i + 1, len(vid_ids_list)):
            a, b = vid_ids_list[i], vid_ids_list[j]
            shared = ep_topics[a] & ep_topics[b]
            if len(shared) >= 2:
                edges.append({
                    "source": f"episode:{a}",
                    "target": f"episode:{b}",
                    "relation": "related",
                    "shared_topics": sorted(shared),
                })

    return {"nodes": nodes, "edges": edges}


def main() -> None:
    index = json.loads(INDEX_PATH.read_text())
    entities = json.loads(ENTITIES_PATH.read_text()) if ENTITIES_PATH.exists() else {}
    topics = json.loads(TOPICS_PATH.read_text()) if TOPICS_PATH.exists() else {}

    graph = build_graph(index, entities, topics)
    OUTPUT_PATH.write_text(json.dumps(graph, indent=2))
    print(f"Knowledge graph: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke test**

```bash
python scripts/05_build_knowledge_graph.py
```

Expected: prints node/edge counts, `taxonomy/knowledge-graph.json` created.

- [ ] **Step 3: Commit**

```bash
git add scripts/05_build_knowledge_graph.py
git commit -m "feat: add knowledge graph builder"
```

---

## Task 7: Master Index + Speaker Index

**Files:**
- Create: `scripts/06_build_master_index.py`
- Create: `scripts/07_build_speaker_index.py`
- Produces: `topic-index/master-index.md`, `speaker-index/speaker-index.md`

**Interfaces:**
- Consumes: `youtube/metadata/index.json`, `taxonomy/topics.json`, `taxonomy/entities.json`, `youtube/transcripts/*.md`

- [ ] **Step 1: Write `scripts/06_build_master_index.py`**

```python
#!/usr/bin/env python3
"""Phase 8: Build master topic index aggregating all classified episodes."""

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
INDEX_PATH = ROOT / "youtube" / "metadata" / "index.json"
TOPICS_PATH = ROOT / "taxonomy" / "topics.json"
ENTITIES_PATH = ROOT / "taxonomy" / "entities.json"
OUTPUT_PATH = ROOT / "topic-index" / "master-index.md"


def main() -> None:
    index = json.loads(INDEX_PATH.read_text())
    topics = json.loads(TOPICS_PATH.read_text()) if TOPICS_PATH.exists() else {}
    entities = json.loads(ENTITIES_PATH.read_text()) if ENTITIES_PATH.exists() else {}

    # Episodes by topic
    by_topic: dict[str, list] = defaultdict(list)
    for entry in index:
        for topic in topics.get(entry["video_id"], []):
            by_topic[topic].append(entry)

    # Most referenced concepts
    concept_count: dict[str, int] = defaultdict(int)
    for ent_map in entities.values():
        for items in ent_map.values():
            for item in items:
                concept_count[item.lower()] += 1
    top_concepts = sorted(concept_count.items(), key=lambda x: -x[1])[:50]

    lines = ["# Human Workforce Master Index\n"]
    lines.append(f"**Total Episodes:** {len(index)}\n")
    lines.append(f"**Topics Covered:** {len(by_topic)}\n\n---\n")

    lines.append("## Episodes by Topic\n")
    for topic in sorted(by_topic):
        lines.append(f"\n### {topic}\n")
        for ep in sorted(by_topic[topic], key=lambda e: e["index"]):
            lines.append(f"- [{ep['title']}]({ep.get('summary_file', ep['url'])}) — Episode {ep['index']:03d}")

    lines.append("\n\n## Most Referenced Concepts\n")
    for concept, count in top_concepts:
        lines.append(f"- **{concept}** ({count} episodes)")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Master index saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write `scripts/07_build_speaker_index.py`**

```python
#!/usr/bin/env python3
"""Phase 9: Build speaker index by searching transcripts for known speaker names."""

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text())
INDEX_PATH = ROOT / "youtube" / "metadata" / "index.json"
TOPICS_PATH = ROOT / "taxonomy" / "topics.json"
OUTPUT_PATH = ROOT / "speaker-index" / "speaker-index.md"


def find_speaker_mentions(transcript_text: str, speaker: str) -> list[str]:
    """Return sentences containing the speaker name."""
    sentences = re.split(r"(?<=[.!?])\s+", transcript_text)
    return [s.strip() for s in sentences if speaker.lower() in s.lower()][:5]


def main() -> None:
    index = json.loads(INDEX_PATH.read_text())
    topics = json.loads(TOPICS_PATH.read_text()) if TOPICS_PATH.exists() else {}
    speakers = CONFIG["speakers"]

    speaker_data: dict[str, dict] = {s: {"episodes": [], "themes": []} for s in speakers}

    for entry in index:
        transcript_path = entry.get("transcript_file")
        if not transcript_path:
            continue
        text = (ROOT / transcript_path).read_text(encoding="utf-8")
        for speaker in speakers:
            if speaker.lower() in text.lower():
                ep_topics = topics.get(entry["video_id"], [])
                speaker_data[speaker]["episodes"].append({
                    "index": entry["index"],
                    "title": entry["title"],
                    "url": entry["url"],
                    "topics": ep_topics,
                })
                speaker_data[speaker]["themes"].extend(ep_topics)

    lines = ["# Human Workforce Speaker Index\n"]

    for speaker, data in speaker_data.items():
        lines.append(f"\n## {speaker}\n")
        if not data["episodes"]:
            lines.append("_Not yet mentioned in transcripts._\n")
            continue

        # Deduplicate themes
        theme_counts: dict[str, int] = defaultdict(int)
        for t in data["themes"]:
            theme_counts[t] += 1
        top_themes = sorted(theme_counts.items(), key=lambda x: -x[1])[:5]

        lines.append(f"**Episodes mentioned in:** {len(data['episodes'])}\n")
        lines.append("\n**Primary Expertise Areas:**\n")
        for theme, count in top_themes:
            lines.append(f"- {theme} ({count} episodes)")

        lines.append("\n**Episodes:**\n")
        for ep in sorted(data["episodes"], key=lambda e: e["index"]):
            topic_str = ", ".join(ep["topics"][:3])
            lines.append(f"- [Episode {ep['index']:03d}: {ep['title']}]({ep['url']}) — {topic_str}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Speaker index saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Smoke test both**

```bash
python scripts/06_build_master_index.py
python scripts/07_build_speaker_index.py
```

Expected: both files created with content.

- [ ] **Step 4: Commit**

```bash
git add scripts/06_build_master_index.py scripts/07_build_speaker_index.py
git commit -m "feat: add master index and speaker index builders"
```

---

## Task 8: Shorts Generation + NotebookLM Prep

**Files:**
- Create: `scripts/08_generate_shorts.py`
- Create: `scripts/09_prepare_notebooklm.py`

**Interfaces:**
- Consumes: `youtube/summaries/*.md`, `youtube/metadata/index.json`, `taxonomy/*.json`
- Produces: `shorts/episode-NNN-slug-shorts.md`, `notebooklm/master-source.md`, `notebooklm/episode-index.md`, `notebooklm/glossary.md`, `notebooklm/frameworks.md`, `notebooklm/topic-guides/*.md`

- [ ] **Step 1: Write `scripts/08_generate_shorts.py`**

```python
#!/usr/bin/env python3
"""Phase 10: Generate short-form content ideas per episode using Claude."""

import json
import os
import re
import sys
from pathlib import Path

import anthropic

ROOT = Path(__file__).parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text())
INDEX_PATH = ROOT / "youtube" / "metadata" / "index.json"
SHORTS_DIR = ROOT / "shorts"

DRY_RUN = "--dry-run" in sys.argv
FORCE = "--force" in sys.argv

SHORTS_PROMPT = """\
You are a short-form content strategist for The Human Workforce — a platform on AI, Future of Work, \
Workforce Transformation, Operational Resilience, and Leadership.

Based on the episode summary below, generate exactly 10 short-form content ideas (30–90 second videos).

For each idea use this format:

## Idea N: [Title]

**Hook:** [1 sentence opening that stops the scroll]

**Key Message:** [The single insight or takeaway]

**Suggested Visual:** [What appears on screen]

**CTA:** [Call to action]

---

Episode Summary:
{summary}
"""


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text[:70]


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    SHORTS_DIR.mkdir(parents=True, exist_ok=True)
    index = json.loads(INDEX_PATH.read_text())
    client = anthropic.Anthropic(api_key=api_key)
    model = CONFIG["model_bulk"]

    for entry in index:
        summary_path = entry.get("summary_file")
        if not summary_path:
            print(f"  [SKIP] {entry['title'][:60]} (no summary)")
            continue

        slug = slugify(entry["title"])
        out_path = SHORTS_DIR / f"episode-{entry['index']:03d}-{slug}-shorts.md"

        if out_path.exists() and not FORCE:
            print(f"  [SKIP] {entry['title'][:60]} (exists)")
            continue

        print(f"  [{entry['index']:03d}] Generating shorts: {entry['title'][:50]}...")
        if DRY_RUN:
            print("         → [dry-run]")
            continue

        try:
            summary_text = (ROOT / summary_path).read_text(encoding="utf-8")
            message = client.messages.create(
                model=model,
                max_tokens=3000,
                messages=[{"role": "user", "content": SHORTS_PROMPT.format(summary=summary_text[:8000])}]
            )
            content = f"# Shorts Ideas: {entry['title']}\n\n**Episode:** {entry['index']:03d}  \n**Source:** {summary_path}\n\n---\n\n"
            content += message.content[0].text
            out_path.write_text(content, encoding="utf-8")
            print(f"         → saved")
        except Exception as e:
            print(f"         → ERROR: {e}")

    print("\nShorts generation complete.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write `scripts/09_prepare_notebooklm.py`**

```python
#!/usr/bin/env python3
"""Phase 11: Compile NotebookLM-ready master files from the vault."""

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
INDEX_PATH = ROOT / "youtube" / "metadata" / "index.json"
TOPICS_PATH = ROOT / "taxonomy" / "topics.json"
ENTITIES_PATH = ROOT / "taxonomy" / "entities.json"
NLM_DIR = ROOT / "notebooklm"


def compile_master_source(index: list) -> str:
    parts = ["# The Human Workforce — Master Knowledge Source\n\n"]
    parts.append("*Auto-generated knowledge vault for use in NotebookLM, Claude Projects, and ChatGPT Projects.*\n\n---\n\n")

    for entry in index:
        summary_path = entry.get("summary_file")
        if not summary_path:
            continue
        summary_text = (ROOT / summary_path).read_text(encoding="utf-8")
        parts.append(f"---\n\n## Episode {entry['index']:03d}: {entry['title']}\n\n")
        parts.append(f"**URL:** {entry['url']}  \n**Published:** {entry.get('upload_date', '')[:4]}\n\n")
        parts.append(summary_text)
        parts.append("\n\n")

    return "".join(parts)


def compile_episode_index(index: list, topics: dict) -> str:
    lines = ["# Episode Index\n"]
    for entry in sorted(index, key=lambda e: e["index"]):
        ep_topics = ", ".join(topics.get(entry["video_id"], [])[:3])
        lines.append(f"\n## Episode {entry['index']:03d}: {entry['title']}")
        lines.append(f"\n**URL:** {entry['url']}")
        lines.append(f"\n**Topics:** {ep_topics or 'Unclassified'}")
        lines.append(f"\n**Summary:** {entry.get('summary_file', '_not generated_')}\n")
    return "\n".join(lines)


def compile_glossary(entities: dict) -> str:
    concepts: dict[str, int] = defaultdict(int)
    for ent_map in entities.values():
        for item in ent_map.get("concepts", []):
            concepts[item] += 1
    for ent_map in entities.values():
        for item in ent_map.get("technologies", []):
            concepts[item] += 1

    lines = ["# Glossary of Key Terms\n"]
    lines.append("*Recurring concepts and technologies across The Human Workforce content.*\n")
    for term, count in sorted(concepts.items(), key=lambda x: -x[1])[:100]:
        lines.append(f"\n## {term.title()}\n")
        lines.append(f"*Referenced in {count} episode(s).*\n")
        lines.append("_Definition to be added._\n")
    return "\n".join(lines)


def compile_frameworks(entities: dict) -> str:
    frameworks: dict[str, int] = defaultdict(int)
    methodologies: dict[str, int] = defaultdict(int)
    for ent_map in entities.values():
        for item in ent_map.get("frameworks", []):
            frameworks[item] += 1
        for item in ent_map.get("methodologies", []):
            methodologies[item] += 1

    lines = ["# Frameworks and Methodologies\n"]
    if frameworks:
        lines.append("\n## Frameworks\n")
        for name, count in sorted(frameworks.items(), key=lambda x: -x[1]):
            lines.append(f"- **{name}** ({count} episodes)")
    if methodologies:
        lines.append("\n\n## Methodologies\n")
        for name, count in sorted(methodologies.items(), key=lambda x: -x[1]):
            lines.append(f"- **{name}** ({count} episodes)")
    return "\n".join(lines)


def compile_topic_guides(index: list, topics: dict, categories: list) -> dict[str, str]:
    guides = {}
    by_topic: dict[str, list] = defaultdict(list)
    for entry in index:
        for topic in topics.get(entry["video_id"], []):
            by_topic[topic].append(entry)

    for category in categories:
        episodes = by_topic.get(category, [])
        if not episodes:
            continue
        lines = [f"# Topic Guide: {category}\n"]
        lines.append(f"*{len(episodes)} episode(s) cover this topic.*\n")
        for ep in sorted(episodes, key=lambda e: e["index"]):
            lines.append(f"\n## Episode {ep['index']:03d}: {ep['title']}")
            lines.append(f"\n**URL:** {ep['url']}")
            summary_path = ep.get("summary_file")
            if summary_path and (ROOT / summary_path).exists():
                summary_text = (ROOT / summary_path).read_text()[:500]
                lines.append(f"\n\n{summary_text}...\n")
        slug = re.sub(r"\s+", "-", category.lower())
        guides[slug] = "\n".join(lines)
    return guides


def main() -> None:
    NLM_DIR.mkdir(parents=True, exist_ok=True)
    (NLM_DIR / "topic-guides").mkdir(exist_ok=True)

    index = json.loads(INDEX_PATH.read_text())
    topics = json.loads(TOPICS_PATH.read_text()) if TOPICS_PATH.exists() else {}
    entities = json.loads(ENTITIES_PATH.read_text()) if ENTITIES_PATH.exists() else {}
    categories = json.loads((ROOT / "config.json").read_text())["primary_categories"]

    print("Compiling master-source.md...")
    (NLM_DIR / "master-source.md").write_text(compile_master_source(index), encoding="utf-8")

    print("Compiling episode-index.md...")
    (NLM_DIR / "episode-index.md").write_text(compile_episode_index(index, topics), encoding="utf-8")

    print("Compiling glossary.md...")
    (NLM_DIR / "glossary.md").write_text(compile_glossary(entities), encoding="utf-8")

    print("Compiling frameworks.md...")
    (NLM_DIR / "frameworks.md").write_text(compile_frameworks(entities), encoding="utf-8")

    print("Compiling topic guides...")
    guides = compile_topic_guides(index, topics, categories)
    for slug, content in guides.items():
        (NLM_DIR / "topic-guides" / f"{slug}.md").write_text(content, encoding="utf-8")
        print(f"  → {slug}.md")

    print(f"\nNotebookLM prep complete. Files in {NLM_DIR}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit**

```bash
git add scripts/08_generate_shorts.py scripts/09_prepare_notebooklm.py
git commit -m "feat: add shorts generator and NotebookLM compiler"
```

---

## Task 9: Intelligence Report

**Files:**
- Create: `scripts/10_generate_report.py`
- Produces: `exports/human-workforce-intelligence-report.md`

**Interfaces:**
- Consumes: `notebooklm/master-source.md`, `taxonomy/*.json`, `youtube/metadata/index.json`

- [ ] **Step 1: Write `scripts/10_generate_report.py`**

```python
#!/usr/bin/env python3
"""Phase 13: Generate Human Workforce Intelligence Report using Claude Sonnet."""

import json
import os
import sys
from pathlib import Path

import anthropic

ROOT = Path(__file__).parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text())
INDEX_PATH = ROOT / "youtube" / "metadata" / "index.json"
MASTER_SOURCE = ROOT / "notebooklm" / "master-source.md"
TOPICS_PATH = ROOT / "taxonomy" / "topics.json"
ENTITIES_PATH = ROOT / "taxonomy" / "entities.json"
OUTPUT_PATH = ROOT / "exports" / "human-workforce-intelligence-report.md"

REPORT_PROMPT = """\
You are a senior research analyst for The Human Workforce — a platform on AI, Agentic AI, \
Workforce Transformation, Future of Work, Business Continuity, Operational Resilience, \
Technology Risk, Cybersecurity, AI Governance, Human-Machine Collaboration, and Executive Leadership.

You have access to the complete vault of Human Workforce podcast content. Produce a comprehensive \
intelligence report in this exact structure:

# Human Workforce Intelligence Report

## Executive Summary
[3–5 paragraphs distilling the most important findings across all content]

## Top 25 Themes
[Numbered list of the 25 most dominant themes with a 1-sentence description each]

## Most Important Findings
[10 bullet points — the most significant insights discovered across all episodes]

## Emerging Trends
[5–8 trends identified from recent content, with evidence]

## Workforce Predictions
[5 specific, evidence-based predictions for the workforce]

## AI Predictions
[5 specific, evidence-based predictions for AI adoption and impact]

## Governance Predictions
[5 specific, evidence-based predictions for AI governance and regulation]

## Recommended Future Books
[5 book ideas with working title, thesis, and target audience]

## Recommended Future Podcast Series
[5 podcast series ideas with concept and first 3 episode titles]

## Recommended Future Courses
[5 course ideas with title, audience, and key learning outcomes]

## Recommended Future Research Areas
[5 research areas that need more investigation]

---

Content vault summary (first 120,000 characters):
{vault_content}

---

Topic distribution:
{topic_summary}
"""


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    if not MASTER_SOURCE.exists():
        print("ERROR: master-source.md not found. Run script 09 first.", file=sys.stderr)
        sys.exit(1)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic(api_key=api_key)
    model = CONFIG["model_report"]

    vault_content = MASTER_SOURCE.read_text(encoding="utf-8")[:120_000]

    topics = json.loads(TOPICS_PATH.read_text()) if TOPICS_PATH.exists() else {}
    from collections import Counter
    topic_counter: Counter = Counter()
    for topic_list in topics.values():
        topic_counter.update(topic_list)
    topic_summary = "\n".join(f"- {t}: {c} episodes" for t, c in topic_counter.most_common(20))

    print(f"Generating intelligence report using {model}...")
    message = client.messages.create(
        model=model,
        max_tokens=8192,
        messages=[{"role": "user", "content": REPORT_PROMPT.format(
            vault_content=vault_content,
            topic_summary=topic_summary
        )}]
    )

    OUTPUT_PATH.write_text(message.content[0].text, encoding="utf-8")
    print(f"Report saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke test**

```bash
python scripts/10_generate_report.py
```

Expected: `exports/human-workforce-intelligence-report.md` created.

- [ ] **Step 3: Commit**

```bash
git add scripts/10_generate_report.py
git commit -m "feat: add intelligence report generator"
```

---

## Task 10: Pipeline Runner

**Files:**
- Create: `scripts/run_pipeline.py`
- Runs all 10 scripts in sequence with checkpoint tracking

**Interfaces:**
- Consumes: all scripts 01–10
- Produces: `pipeline-state.json` for checkpoint/resume support

- [ ] **Step 1: Write `scripts/run_pipeline.py`**

```python
#!/usr/bin/env python3
"""Master pipeline runner — executes all vault-building scripts in sequence."""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
STATE_FILE = ROOT / "pipeline-state.json"

SCRIPTS = [
    ("01_collect_metadata", "scripts/01_collect_metadata.py"),
    ("02_collect_transcripts", "scripts/02_collect_transcripts.py"),
    ("03_summarize_episodes", "scripts/03_summarize_episodes.py"),
    ("04_extract_entities_topics", "scripts/04_extract_entities_topics.py"),
    ("05_build_knowledge_graph", "scripts/05_build_knowledge_graph.py"),
    ("06_build_master_index", "scripts/06_build_master_index.py"),
    ("07_build_speaker_index", "scripts/07_build_speaker_index.py"),
    ("08_generate_shorts", "scripts/08_generate_shorts.py"),
    ("09_prepare_notebooklm", "scripts/09_prepare_notebooklm.py"),
    ("10_generate_report", "scripts/10_generate_report.py"),
]

RESUME = "--resume" in sys.argv
FROM_STEP = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--from=")), 1)


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"completed": [], "runs": []}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def main() -> None:
    state = load_state()
    completed = set(state["completed"]) if RESUME else set()

    run_record = {"started": datetime.now().isoformat(), "steps": []}
    state["runs"].append(run_record)

    for i, (name, script_path) in enumerate(SCRIPTS, start=1):
        if i < FROM_STEP:
            print(f"[{i:02d}/{len(SCRIPTS)}] SKIP (--from={FROM_STEP}): {name}")
            continue
        if RESUME and name in completed:
            print(f"[{i:02d}/{len(SCRIPTS)}] SKIP (already done): {name}")
            continue

        print(f"\n{'='*60}")
        print(f"[{i:02d}/{len(SCRIPTS)}] Running: {name}")
        print(f"{'='*60}")

        result = subprocess.run(
            [sys.executable, str(ROOT / script_path)],
            cwd=ROOT
        )

        step_record = {
            "name": name,
            "returncode": result.returncode,
            "timestamp": datetime.now().isoformat()
        }
        run_record["steps"].append(step_record)

        if result.returncode == 0:
            state["completed"].append(name)
            save_state(state)
            print(f"✓ {name} completed successfully")
        else:
            save_state(state)
            print(f"\nPipeline stopped at step {i}: {name} failed (exit code {result.returncode})")
            print("Fix the issue and re-run with: python scripts/run_pipeline.py --resume")
            sys.exit(result.returncode)

    print(f"\n{'='*60}")
    print("PIPELINE COMPLETE")
    print(f"{'='*60}")
    print(f"All {len(SCRIPTS)} steps finished. Vault ready at: {ROOT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test the runner (dry-run each script)**

```bash
python scripts/run_pipeline.py --from=6
```

Expected: runs steps 6–10 (index builders that don't need API), completes without error.

- [ ] **Step 3: Commit**

```bash
git add scripts/run_pipeline.py
git commit -m "feat: add pipeline runner with checkpoint/resume support"
```

---

## Self-Review Against Spec

**Spec coverage:**

| Phase | Spec Requirement | Covered By |
|-------|-----------------|------------|
| 1 | Folder structure | Task 1 |
| 2 | YouTube metadata (title, desc, URL, ID, date, duration) | Task 2, script 01 |
| 3 | Transcript collection, cleaned | Task 3, script 02 |
| 4 | Episode summaries (exec summary, themes, findings, takeaways, quotes, relevance, future ideas) | Task 4, script 03 |
| 5 | Entity extraction (people, orgs, products, platforms, concepts, tech, methodologies, frameworks) | Task 5, script 04 |
| 6 | Topic classification (16 primary categories) | Task 5, script 04 |
| 7 | Knowledge graph (nodes, edges, related episodes) | Task 6, script 05 |
| 8 | Master index | Task 7, script 06 |
| 9 | Speaker index (all 8 speakers) | Task 7, script 07 |
| 10 | Shorts (10 ideas/episode, hook/message/visual/CTA) | Task 8, script 08 |
| 11 | NotebookLM prep (master-source, topic-guides, episode-index, glossary, frameworks) | Task 8, script 09 |
| 12 | Book intelligence | Manual step — noted below |
| 13 | Intelligence report (25 themes, predictions, recommendations) | Task 9, script 10 |

**Manual step required (Phase 12 — Book Intelligence):**
Book manuscripts must be placed in their respective `books/` subdirectories manually. Once placed, add a `scripts/11_analyze_books.py` script following the same pattern as `03_summarize_episodes.py` to cross-reference with transcripts.

**Prerequisites the user must complete before running:**
1. Add YouTube channel/playlist URL to `config.json["channel_url"]`
2. Set `ANTHROPIC_API_KEY` environment variable
3. Confirm Python 3.11+ is installed: `python --version`

---

## Running the Full Pipeline

```bash
cd HumanWorkforceVault
export ANTHROPIC_API_KEY=your_key_here

# Full run from scratch:
python scripts/run_pipeline.py

# Resume after a failure:
python scripts/run_pipeline.py --resume

# Start from a specific step (e.g., step 3 — skip metadata and transcripts):
python scripts/run_pipeline.py --from=3
```

**Cost estimate (rough):** ~$5–15 USD in Claude API costs for a 50-episode channel using claude-haiku-4-5 for bulk processing and claude-sonnet-4-6 only for the final report.
