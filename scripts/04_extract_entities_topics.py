#!/usr/bin/env python3
"""Phase 5+6: Extract entities and classify topics for each episode."""

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
TAXONOMY_DIR = _config_root / "taxonomy"

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
            text = (_config_root / transcript_path).read_text(encoding="utf-8")
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
