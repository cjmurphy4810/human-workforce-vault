#!/usr/bin/env python3
"""Phase 10: Generate short-form content ideas per episode using Claude."""

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
SHORTS_DIR = _config_root / "shorts"

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
            summary_text = (_config_root / summary_path).read_text(encoding="utf-8")
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
