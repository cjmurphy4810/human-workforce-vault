import json
import subprocess
import sys
from pathlib import Path

def test_metadata_produces_index(tmp_path, monkeypatch):
    """Run script against a known short public video and verify index.json is written."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "youtube" / "metadata").mkdir(parents=True)
    config = {
        "channel_url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        "model_bulk": "claude-haiku-4-5-20251001",
        "model_report": "claude-sonnet-4-6",
        "speakers": [],
        "primary_categories": []
    }
    (tmp_path / "config.json").write_text(json.dumps(config))

    result = subprocess.run(
        [sys.executable, str(Path(__file__).parents[1] / "scripts" / "01_collect_metadata.py")],
        cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    index = json.loads((tmp_path / "youtube" / "metadata" / "index.json").read_text())
    assert len(index) >= 1
    assert "video_id" in index[0]
    assert "title" in index[0]
    assert "metadata_file" in index[0]
