import json
import subprocess
import sys
from pathlib import Path

KNOWN_VIDEO_ID = "jNQXAC9IVRw"  # "Me at the zoo" — first YouTube video, has captions

def test_transcript_fetched(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "youtube" / "transcripts").mkdir(parents=True)
    (tmp_path / "youtube" / "metadata").mkdir(parents=True)

    index = [{
        "index": 1,
        "video_id": KNOWN_VIDEO_ID,
        "title": "Me at the zoo",
        "upload_date": "20050423",
        "duration_seconds": 19,
        "url": f"https://www.youtube.com/watch?v={KNOWN_VIDEO_ID}",
        "metadata_file": "youtube/metadata/2005-04-23-me-at-the-zoo.md"
    }]
    (tmp_path / "youtube" / "metadata" / "index.json").write_text(json.dumps(index))

    config = {
        "channel_url": "",
        "model_bulk": "claude-haiku-4-5-20251001",
        "model_report": "claude-sonnet-4-6",
        "speakers": [],
        "primary_categories": []
    }
    (tmp_path / "config.json").write_text(json.dumps(config))

    result = subprocess.run(
        [sys.executable, str(Path(__file__).parents[1] / "scripts" / "02_collect_transcripts.py")],
        cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr

    transcript_files = list((tmp_path / "youtube" / "transcripts").glob("*.md"))
    assert len(transcript_files) == 1
    content = transcript_files[0].read_text()
    assert len(content) > 50
