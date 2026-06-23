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
