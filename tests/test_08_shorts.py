import json
import os
import subprocess
import sys
from pathlib import Path


def test_shorts_fails_without_api_key(tmp_path, monkeypatch):
    """Without ANTHROPIC_API_KEY, script should exit non-zero with a clear error."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "youtube" / "metadata").mkdir(parents=True)
    (tmp_path / "shorts").mkdir(parents=True)

    index = [
        {
            "index": 1,
            "video_id": "abc123",
            "title": "Test Episode",
            "url": "https://youtube.com/watch?v=abc123",
            "upload_date": "20240101",
            "duration_seconds": 1800,
            "summary_file": None,
        }
    ]
    (tmp_path / "youtube" / "metadata" / "index.json").write_text(json.dumps(index))
    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "channel_url": "",
                "model_bulk": "claude-haiku-4-5-20251001",
                "model_report": "claude-sonnet-4-6",
                "speakers": [],
                "primary_categories": [],
            }
        )
    )

    env = {**os.environ, "ANTHROPIC_API_KEY": ""}
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parents[1] / "scripts" / "08_generate_shorts.py"),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode != 0
    assert "ANTHROPIC_API_KEY" in result.stderr
