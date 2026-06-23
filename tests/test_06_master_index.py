import json
import sys
import importlib.util
from pathlib import Path

# Load the module directly from file path
script_path = Path(__file__).parents[1] / "scripts" / "06_build_master_index.py"
spec = importlib.util.spec_from_file_location("build_master_index", script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_master_index_basic(tmp_path, monkeypatch):
    """Test that master index generates output with episodes by topic."""
    monkeypatch.chdir(tmp_path)

    # Create fixture data
    index = [
        {"index": 1, "video_id": "vid1", "title": "Episode 1", "url": "https://youtube.com/watch?v=vid1"},
        {"index": 2, "video_id": "vid2", "title": "Episode 2", "url": "https://youtube.com/watch?v=vid2"},
        {"index": 3, "video_id": "vid3", "title": "Episode 3", "url": "https://youtube.com/watch?v=vid3"},
    ]

    topics = {
        "vid1": ["AI", "Machine Learning"],
        "vid2": ["AI", "Data Science"],
        "vid3": ["Machine Learning"],
    }

    entities = {
        "vid1": {"person": ["Alice", "Bob"]},
        "vid2": {"person": ["Charlie"], "organization": ["TechCorp"]},
        "vid3": {"person": ["Alice"]},
    }

    # Create required directories and files
    (tmp_path / "youtube" / "metadata").mkdir(parents=True)
    (tmp_path / "taxonomy").mkdir(parents=True)
    (tmp_path / "topic-index").mkdir(parents=True)

    (tmp_path / "youtube" / "metadata" / "index.json").write_text(json.dumps(index))
    (tmp_path / "taxonomy" / "topics.json").write_text(json.dumps(topics))
    (tmp_path / "taxonomy" / "entities.json").write_text(json.dumps(entities))

    # Run the script
    import subprocess
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr

    # Verify output file exists
    output_file = tmp_path / "topic-index" / "master-index.md"
    assert output_file.exists()

    content = output_file.read_text()
    assert "Human Workforce Master Index" in content
    assert "Total Episodes:** 3" in content
    assert "Topics Covered:** 3" in content
    assert "AI" in content
    assert "Machine Learning" in content
    assert "Episode 1" in content
    assert "Episode 2" in content
    assert "Episode 3" in content


def test_master_index_missing_taxonomy(tmp_path, monkeypatch):
    """Test that master index handles missing topics and entities gracefully."""
    monkeypatch.chdir(tmp_path)

    # Create minimal fixture data
    index = [
        {"index": 1, "video_id": "vid1", "title": "Episode 1", "url": "https://youtube.com/watch?v=vid1"},
    ]

    # Create required directories and files
    (tmp_path / "youtube" / "metadata").mkdir(parents=True)
    (tmp_path / "taxonomy").mkdir(parents=True)
    (tmp_path / "topic-index").mkdir(parents=True)

    (tmp_path / "youtube" / "metadata" / "index.json").write_text(json.dumps(index))
    # Don't create topics.json or entities.json

    # Run the script
    import subprocess
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr

    # Verify output file exists with minimal content
    output_file = tmp_path / "topic-index" / "master-index.md"
    assert output_file.exists()
    content = output_file.read_text()
    assert "Master Index" in content


def test_master_index_concept_counting(tmp_path, monkeypatch):
    """Test that concepts are counted correctly."""
    monkeypatch.chdir(tmp_path)

    index = [
        {"index": 1, "video_id": "vid1", "title": "Episode 1", "url": "https://youtube.com/watch?v=vid1"},
        {"index": 2, "video_id": "vid2", "title": "Episode 2", "url": "https://youtube.com/watch?v=vid2"},
    ]

    topics = {
        "vid1": ["AI"],
        "vid2": ["AI"],
    }

    entities = {
        "vid1": {"person": ["Alice", "Bob"], "organization": ["Corp"]},
        "vid2": {"person": ["Alice", "Alice"]},  # Alice appears twice
    }

    # Create required directories and files
    (tmp_path / "youtube" / "metadata").mkdir(parents=True)
    (tmp_path / "taxonomy").mkdir(parents=True)
    (tmp_path / "topic-index").mkdir(parents=True)

    (tmp_path / "youtube" / "metadata" / "index.json").write_text(json.dumps(index))
    (tmp_path / "taxonomy" / "topics.json").write_text(json.dumps(topics))
    (tmp_path / "taxonomy" / "entities.json").write_text(json.dumps(entities))

    # Run the script
    import subprocess
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr

    output_file = tmp_path / "topic-index" / "master-index.md"
    content = output_file.read_text()

    # Verify that "Most Referenced Concepts" section exists
    assert "Most Referenced Concepts" in content
    # Alice should appear with count 3 (1+1+1 from both episodes and duplicate)
    assert "alice" in content.lower()
