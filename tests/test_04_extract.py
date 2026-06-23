import json
import os
import subprocess
import sys
from pathlib import Path


def test_extract_fails_without_api_key(tmp_path, monkeypatch):
    """Without ANTHROPIC_API_KEY, script should exit non-zero with a clear error."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "youtube" / "metadata").mkdir(parents=True)
    (tmp_path / "youtube" / "transcripts").mkdir(parents=True)
    (tmp_path / "taxonomy").mkdir(parents=True)

    index = [{"index": 1, "video_id": "abc", "title": "Test", "url": "",
               "upload_date": "", "duration_seconds": 0,
               "metadata_file": "", "transcript_file": None}]
    (tmp_path / "youtube" / "metadata" / "index.json").write_text(json.dumps(index))
    (tmp_path / "config.json").write_text(json.dumps({
        "channel_url": "", "model_bulk": "claude-haiku-4-5-20251001",
        "model_report": "claude-sonnet-4-6", "speakers": [], "primary_categories": []
    }))

    env = {**os.environ, "ANTHROPIC_API_KEY": ""}
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parents[1] / "scripts" / "04_extract_entities_topics.py")],
        cwd=tmp_path, capture_output=True, text=True, env=env
    )
    assert result.returncode != 0
    assert "ANTHROPIC_API_KEY" in result.stderr
