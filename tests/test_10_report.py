import json
import os
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "10_generate_report.py"


def _make_base_fixture(tmp_path: Path) -> None:
    """Create minimal config and directories for script 10."""
    (tmp_path / "notebooklm").mkdir(parents=True)
    (tmp_path / "taxonomy").mkdir(parents=True)
    (tmp_path / "exports").mkdir(parents=True)

    config = {
        "channel_url": "",
        "model_bulk": "claude-haiku-4-5-20251001",
        "model_report": "claude-sonnet-4-6",
        "speakers": [],
        "primary_categories": [],
    }
    (tmp_path / "config.json").write_text(json.dumps(config))

    topics = {"vid1": ["Agentic AI", "Future of Work"]}
    (tmp_path / "taxonomy" / "topics.json").write_text(json.dumps(topics))


def test_report_fails_without_api_key(tmp_path, monkeypatch):
    """Without ANTHROPIC_API_KEY, script should exit non-zero with a clear error."""
    monkeypatch.chdir(tmp_path)
    _make_base_fixture(tmp_path)

    # Create master-source.md so we isolate the API key failure
    (tmp_path / "notebooklm" / "master-source.md").write_text(
        "# Human Workforce Vault\n\nSample content.", encoding="utf-8"
    )

    env = {**os.environ, "ANTHROPIC_API_KEY": ""}
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode != 0
    assert "ANTHROPIC_API_KEY" in result.stderr


def test_report_fails_without_master_source(tmp_path, monkeypatch):
    """Without master-source.md, script should exit non-zero with a clear error."""
    monkeypatch.chdir(tmp_path)
    _make_base_fixture(tmp_path)

    # master-source.md intentionally NOT created

    env = {**os.environ, "ANTHROPIC_API_KEY": "fake-key-for-testing"}
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode != 0
    assert "master-source.md" in result.stderr
