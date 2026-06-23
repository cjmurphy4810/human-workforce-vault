#!/usr/bin/env python3
"""Phase 9: Build speaker index by searching transcripts for known speaker names."""

import json
import re
import os
from collections import defaultdict
from pathlib import Path

# Use cwd if running from tests, otherwise use script location
ROOT = Path.cwd() if (Path.cwd() / "youtube" / "metadata").exists() else Path(__file__).parent.parent
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
