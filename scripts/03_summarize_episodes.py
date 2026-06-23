#!/usr/bin/env python3
"""Phase 4: Generate AI summaries for each episode transcript."""

import json
import os
import re
import sys
from pathlib import Path

import anthropic

ROOT = Path(__file__).parent.parent
_config_path = Path.cwd() / "config.json" if (Path.cwd() / "config.json").exists() else ROOT / "config.json"
CONFIG = json.loads(_config_path.read_text())
_config_root = _config_path.parent

INDEX_PATH = _config_root / "youtube" / "metadata" / "index.json"
SUMMARY_DIR = _config_root / "youtube" / "summaries"

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
            entry["summary_file"] = str(out_path.relative_to(_config_root))
            skipped += 1
            continue

        print(f"  [{entry['index']:03d}] Summarizing: {entry['title'][:55]}...")

        if DRY_RUN:
            print("         → [dry-run] skipping API call")
            continue

        try:
            full_path = _config_root / transcript_path
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
            entry["summary_file"] = str(out_path.relative_to(_config_root))
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
