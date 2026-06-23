#!/usr/bin/env python3
"""Phase 8: Build master topic index aggregating all classified episodes."""

import json
import os
from collections import defaultdict
from pathlib import Path

# Use cwd if running from tests, otherwise use script location
ROOT = Path.cwd() if (Path.cwd() / "youtube" / "metadata").exists() else Path(__file__).parent.parent
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
