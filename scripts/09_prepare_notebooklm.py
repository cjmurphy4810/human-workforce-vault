#!/usr/bin/env python3
"""Phase 11: Compile NotebookLM-ready master files from the vault."""

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
_config_path = Path.cwd() / "config.json" if (Path.cwd() / "config.json").exists() else ROOT / "config.json"
_config_root = _config_path.parent

INDEX_PATH = _config_root / "youtube" / "metadata" / "index.json"
TOPICS_PATH = _config_root / "taxonomy" / "topics.json"
ENTITIES_PATH = _config_root / "taxonomy" / "entities.json"
NLM_DIR = _config_root / "notebooklm"


def compile_master_source(index: list) -> str:
    parts = ["# The Human Workforce — Master Knowledge Source\n\n"]
    parts.append("*Auto-generated knowledge vault for use in NotebookLM, Claude Projects, and ChatGPT Projects.*\n\n---\n\n")

    for entry in index:
        summary_path = entry.get("summary_file")
        if not summary_path:
            continue
        summary_text = (_config_root / summary_path).read_text(encoding="utf-8")
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
            if summary_path and (_config_root / summary_path).exists():
                summary_text = (_config_root / summary_path).read_text()[:500]
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
    categories = json.loads(_config_path.read_text())["primary_categories"]

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
