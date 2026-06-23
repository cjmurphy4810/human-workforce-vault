import json
import sys
import importlib.util
from pathlib import Path

# Load the module directly from file path
script_path = Path(__file__).parents[1] / "scripts" / "05_build_knowledge_graph.py"
spec = importlib.util.spec_from_file_location("build_knowledge_graph", script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

build_graph = module.build_graph


def test_build_graph_structure(tmp_path, monkeypatch):
    """Test that build_graph creates correct node and edge structure."""
    # Create fixture data
    index = [
        {"index": 1, "video_id": "vid1", "title": "Episode 1"},
        {"index": 2, "video_id": "vid2", "title": "Episode 2"},
        {"index": 3, "video_id": "vid3", "title": "Episode 3"},
    ]

    entities = {
        "vid1": {
            "person": ["Alice", "Bob"],
            "organization": ["Acme Corp"],
        },
        "vid2": {
            "person": ["Alice", "Charlie"],
            "organization": ["Acme Corp", "TechCorp"],
        },
        "vid3": {
            "person": ["Bob"],
        },
    }

    topics = {
        "vid1": ["AI", "Machine Learning"],
        "vid2": ["AI", "Machine Learning", "Deep Learning"],
        "vid3": ["Data Science", "Machine Learning"],
    }

    graph = build_graph(index, entities, topics)

    # Verify graph structure
    assert "nodes" in graph
    assert "edges" in graph
    assert isinstance(graph["nodes"], list)
    assert isinstance(graph["edges"], list)

    # Count node types
    nodes_by_type = {}
    for node in graph["nodes"]:
        node_type = node["type"]
        nodes_by_type[node_type] = nodes_by_type.get(node_type, 0) + 1

    # Verify episode nodes
    assert nodes_by_type.get("episode", 0) == 3, "Should have 3 episode nodes"

    # Verify concept nodes (unique category:label pairs)
    concept_count = nodes_by_type.get("concept", 0)
    assert concept_count > 0, "Should have concept nodes"
    # Expected concepts: person (alice, bob, charlie), organization (acme corp, techcorp)
    # = 5 concept nodes
    assert concept_count == 5, f"Expected 5 concept nodes, got {concept_count}"

    # Verify topic nodes
    topic_count = nodes_by_type.get("topic", 0)
    assert topic_count == 4, f"Expected 4 topic nodes, got {topic_count}"
    # Topics: AI, Machine Learning, Deep Learning, Data Science

    # Verify edge types
    edges_by_relation = {}
    for edge in graph["edges"]:
        rel = edge["relation"]
        edges_by_relation[rel] = edges_by_relation.get(rel, 0) + 1

    # mentions edges: episode -> concept
    mentions_count = edges_by_relation.get("mentions", 0)
    assert mentions_count > 0, "Should have mentions edges"

    # covers edges: episode -> topic
    covers_count = edges_by_relation.get("covers", 0)
    assert covers_count > 0, "Should have covers edges"

    # related edges: episode -> episode (2+ shared topics)
    # vid1 & vid2: share AI, Machine Learning (2) -> related
    # vid2 & vid3: share Machine Learning (1) -> not related
    # vid1 & vid3: share Machine Learning (1) -> not related
    related_count = edges_by_relation.get("related", 0)
    assert related_count == 1, f"Expected 1 related edge, got {related_count}"

    # Verify related edge has shared_topics
    for edge in graph["edges"]:
        if edge["relation"] == "related":
            assert "shared_topics" in edge
            assert isinstance(edge["shared_topics"], list)


def test_build_graph_empty_data():
    """Test that build_graph handles empty input gracefully."""
    graph = build_graph([], {}, {})
    assert graph["nodes"] == []
    assert graph["edges"] == []


def test_build_graph_episode_nodes_contain_metadata(tmp_path):
    """Test that episode nodes contain all required metadata."""
    index = [
        {"index": 1, "video_id": "vid1", "title": "Test Episode"},
    ]
    entities = {}
    topics = {}

    graph = build_graph(index, entities, topics)

    episode_nodes = [n for n in graph["nodes"] if n["type"] == "episode"]
    assert len(episode_nodes) == 1

    node = episode_nodes[0]
    assert node["id"] == "episode:vid1"
    assert node["label"] == "Test Episode"
    assert node["index"] == 1
    assert node["video_id"] == "vid1"


def test_build_graph_concept_node_deduplication():
    """Test that concepts are deduplicated properly."""
    # Same concept in multiple episodes should create one node with multiple edges
    index = [
        {"index": 1, "video_id": "vid1", "title": "Ep 1"},
        {"index": 2, "video_id": "vid2", "title": "Ep 2"},
    ]
    entities = {
        "vid1": {"person": ["Alice"]},
        "vid2": {"person": ["Alice"]},  # Same person
    }
    topics = {}

    graph = build_graph(index, entities, topics)

    concept_nodes = [n for n in graph["nodes"] if n["type"] == "concept"]
    assert len(concept_nodes) == 1

    concept_node = concept_nodes[0]
    assert concept_node["label"] == "alice"
    assert concept_node["episode_count"] == 2

    # Verify two mentions edges (one from each episode)
    mentions_edges = [e for e in graph["edges"] if e["relation"] == "mentions"]
    assert len(mentions_edges) == 2
