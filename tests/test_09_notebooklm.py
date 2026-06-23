import json
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "09_prepare_notebooklm.py"


def _make_fixture(tmp_path: Path) -> None:
    """Create minimal fixture data for script 09."""
    # Directories
    (tmp_path / "youtube" / "metadata").mkdir(parents=True)
    (tmp_path / "youtube" / "summaries").mkdir(parents=True)
    (tmp_path / "taxonomy").mkdir(parents=True)
    (tmp_path / "notebooklm" / "topic-guides").mkdir(parents=True)

    # Summary file
    summary_text = "This episode discusses AI in the workforce and how automation changes jobs."
    summary_rel = "youtube/summaries/episode-001-test.md"
    (tmp_path / summary_rel).write_text(summary_text, encoding="utf-8")

    # Index
    index = [
        {
            "index": 1,
            "video_id": "vid1",
            "title": "Test Episode One",
            "url": "https://youtube.com/watch?v=vid1",
            "upload_date": "20240101",
            "summary_file": summary_rel,
        }
    ]
    (tmp_path / "youtube" / "metadata" / "index.json").write_text(json.dumps(index))

    # Topics
    topics = {"vid1": ["Agentic AI", "Future of Work"]}
    (tmp_path / "taxonomy" / "topics.json").write_text(json.dumps(topics))

    # Entities
    entities = {
        "vid1": {
            "concepts": ["automation", "digital labor"],
            "technologies": ["GPT-4"],
            "frameworks": ["DORA"],
            "methodologies": ["agile"],
        }
    }
    (tmp_path / "taxonomy" / "entities.json").write_text(json.dumps(entities))

    # Config
    config = {
        "channel_url": "",
        "model_bulk": "claude-haiku-4-5-20251001",
        "model_report": "claude-sonnet-4-6",
        "speakers": [],
        "primary_categories": ["Agentic AI", "Future of Work", "Leadership"],
    }
    (tmp_path / "config.json").write_text(json.dumps(config))


def test_notebooklm_creates_output_files(tmp_path, monkeypatch):
    """Script 09 should create master-source.md, episode-index.md, glossary.md, frameworks.md."""
    monkeypatch.chdir(tmp_path)
    _make_fixture(tmp_path)

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    nlm = tmp_path / "notebooklm"
    assert (nlm / "master-source.md").exists(), "master-source.md not created"
    assert (nlm / "episode-index.md").exists(), "episode-index.md not created"
    assert (nlm / "glossary.md").exists(), "glossary.md not created"
    assert (nlm / "frameworks.md").exists(), "frameworks.md not created"


def test_notebooklm_master_source_content(tmp_path, monkeypatch):
    """master-source.md should contain episode title and summary text."""
    monkeypatch.chdir(tmp_path)
    _make_fixture(tmp_path)

    subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    content = (tmp_path / "notebooklm" / "master-source.md").read_text()
    assert "Test Episode One" in content
    assert "AI in the workforce" in content


def test_notebooklm_topic_guides_created(tmp_path, monkeypatch):
    """Topic guide files should be created for categories with episodes."""
    monkeypatch.chdir(tmp_path)
    _make_fixture(tmp_path)

    subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    guides_dir = tmp_path / "notebooklm" / "topic-guides"
    # "Agentic AI" and "Future of Work" both have 1 episode each
    assert (guides_dir / "agentic-ai.md").exists(), "agentic-ai.md not created"
    assert (guides_dir / "future-of-work.md").exists(), "future-of-work.md not created"
    # "Leadership" has no episodes — should not be created
    assert not (guides_dir / "leadership.md").exists(), "leadership.md should not exist"


def test_notebooklm_glossary_content(tmp_path, monkeypatch):
    """glossary.md should contain terms from entities."""
    monkeypatch.chdir(tmp_path)
    _make_fixture(tmp_path)

    subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    content = (tmp_path / "notebooklm" / "glossary.md").read_text()
    assert "Glossary" in content
    # Terms from concepts/technologies
    assert "automation" in content.lower() or "Automation" in content


def test_notebooklm_frameworks_content(tmp_path, monkeypatch):
    """frameworks.md should list frameworks and methodologies."""
    monkeypatch.chdir(tmp_path)
    _make_fixture(tmp_path)

    subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    content = (tmp_path / "notebooklm" / "frameworks.md").read_text()
    assert "DORA" in content
    assert "agile" in content.lower() or "Agile" in content
