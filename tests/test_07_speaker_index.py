import json
import sys
import subprocess
from pathlib import Path


def test_speaker_index_basic(tmp_path, monkeypatch):
    """Test that speaker index finds speakers in transcripts."""
    monkeypatch.chdir(tmp_path)

    # Create fixture data
    index = [
        {
            "index": 1,
            "video_id": "vid1",
            "title": "Episode 1",
            "url": "https://youtube.com/watch?v=vid1",
            "transcript_file": "youtube/transcripts/vid1.md",
        },
        {
            "index": 2,
            "video_id": "vid2",
            "title": "Episode 2",
            "url": "https://youtube.com/watch?v=vid2",
            "transcript_file": "youtube/transcripts/vid2.md",
        },
    ]

    topics = {
        "vid1": ["AI", "Machine Learning"],
        "vid2": ["Data Science"],
    }

    config = {
        "speakers": ["Alice Smith", "Bob Jones", "Charlie Davis"],
        "channel_url": "https://youtube.com/channel/test",
        "model_bulk": "test",
        "model_report": "test",
        "primary_categories": []
    }

    # Create required directories
    (tmp_path / "youtube" / "metadata").mkdir(parents=True)
    (tmp_path / "youtube" / "transcripts").mkdir(parents=True)
    (tmp_path / "taxonomy").mkdir(parents=True)
    (tmp_path / "speaker-index").mkdir(parents=True)

    # Write fixture files
    (tmp_path / "config.json").write_text(json.dumps(config))
    (tmp_path / "youtube" / "metadata" / "index.json").write_text(json.dumps(index))
    (tmp_path / "taxonomy" / "topics.json").write_text(json.dumps(topics))

    # Create transcript files with speaker mentions
    transcript1 = """This is the first episode. Alice Smith discusses artificial intelligence.
    Alice Smith mentions that machine learning is important.
    The discussion covers various AI topics."""
    (tmp_path / "youtube" / "transcripts" / "vid1.md").write_text(transcript1)

    transcript2 = """This is the second episode. Bob Jones talks about data science.
    Bob Jones explains statistical methods.
    Charlie Davis also contributes to the discussion."""
    (tmp_path / "youtube" / "transcripts" / "vid2.md").write_text(transcript2)

    # Run the script
    script_path = Path(__file__).parents[1] / "scripts" / "07_build_speaker_index.py"
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr

    # Verify output file exists
    output_file = tmp_path / "speaker-index" / "speaker-index.md"
    assert output_file.exists()

    content = output_file.read_text()
    assert "Speaker Index" in content
    assert "Alice Smith" in content
    assert "Bob Jones" in content
    assert "Charlie Davis" in content


def test_speaker_index_episode_count(tmp_path, monkeypatch):
    """Test that speaker episodes are counted correctly."""
    monkeypatch.chdir(tmp_path)

    index = [
        {
            "index": 1,
            "video_id": "vid1",
            "title": "Episode 1",
            "url": "https://youtube.com/watch?v=vid1",
            "transcript_file": "youtube/transcripts/vid1.md",
        },
        {
            "index": 2,
            "video_id": "vid2",
            "title": "Episode 2",
            "url": "https://youtube.com/watch?v=vid2",
            "transcript_file": "youtube/transcripts/vid2.md",
        },
    ]

    topics = {
        "vid1": ["AI"],
        "vid2": ["AI"],
    }

    config = {
        "speakers": ["Simon Carver"],
        "channel_url": "https://youtube.com/channel/test",
        "model_bulk": "test",
        "model_report": "test",
        "primary_categories": []
    }

    # Create required directories
    (tmp_path / "youtube" / "metadata").mkdir(parents=True)
    (tmp_path / "youtube" / "transcripts").mkdir(parents=True)
    (tmp_path / "taxonomy").mkdir(parents=True)
    (tmp_path / "speaker-index").mkdir(parents=True)

    # Write fixture files
    (tmp_path / "config.json").write_text(json.dumps(config))
    (tmp_path / "youtube" / "metadata" / "index.json").write_text(json.dumps(index))
    (tmp_path / "taxonomy" / "topics.json").write_text(json.dumps(topics))

    # Create transcript files with speaker mentions in both
    transcript1 = "Simon Carver talks about AI. This is important."
    (tmp_path / "youtube" / "transcripts" / "vid1.md").write_text(transcript1)

    transcript2 = "Simon Carver explains more about AI concepts."
    (tmp_path / "youtube" / "transcripts" / "vid2.md").write_text(transcript2)

    # Run the script
    script_path = Path(__file__).parents[1] / "scripts" / "07_build_speaker_index.py"
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr

    output_file = tmp_path / "speaker-index" / "speaker-index.md"
    content = output_file.read_text()

    # Should mention Simon Carver in 2 episodes
    assert "Simon Carver" in content
    assert "Episodes mentioned in:** 2" in content


def test_speaker_index_not_mentioned(tmp_path, monkeypatch):
    """Test that speakers not mentioned are marked as such."""
    monkeypatch.chdir(tmp_path)

    index = [
        {
            "index": 1,
            "video_id": "vid1",
            "title": "Episode 1",
            "url": "https://youtube.com/watch?v=vid1",
            "transcript_file": "youtube/transcripts/vid1.md",
        },
    ]

    topics = {
        "vid1": ["AI"],
    }

    config = {
        "speakers": ["Alice Smith", "Bob Jones"],
        "channel_url": "https://youtube.com/channel/test",
        "model_bulk": "test",
        "model_report": "test",
        "primary_categories": []
    }

    # Create required directories
    (tmp_path / "youtube" / "metadata").mkdir(parents=True)
    (tmp_path / "youtube" / "transcripts").mkdir(parents=True)
    (tmp_path / "taxonomy").mkdir(parents=True)
    (tmp_path / "speaker-index").mkdir(parents=True)

    # Write fixture files
    (tmp_path / "config.json").write_text(json.dumps(config))
    (tmp_path / "youtube" / "metadata" / "index.json").write_text(json.dumps(index))
    (tmp_path / "taxonomy" / "topics.json").write_text(json.dumps(topics))

    # Create transcript with only Alice mentioned
    transcript1 = "Alice Smith talks about AI today."
    (tmp_path / "youtube" / "transcripts" / "vid1.md").write_text(transcript1)

    # Run the script
    script_path = Path(__file__).parents[1] / "scripts" / "07_build_speaker_index.py"
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr

    output_file = tmp_path / "speaker-index" / "speaker-index.md"
    content = output_file.read_text()

    # Alice should be mentioned with 1 episode
    assert "Alice Smith" in content
    assert "Episodes mentioned in:** 1" in content

    # Bob should be marked as not mentioned
    assert "Bob Jones" in content
    assert "Not yet mentioned in transcripts" in content


def test_speaker_index_theme_tracking(tmp_path, monkeypatch):
    """Test that speaker themes are tracked from episode topics."""
    monkeypatch.chdir(tmp_path)

    index = [
        {
            "index": 1,
            "video_id": "vid1",
            "title": "Episode 1",
            "url": "https://youtube.com/watch?v=vid1",
            "transcript_file": "youtube/transcripts/vid1.md",
        },
        {
            "index": 2,
            "video_id": "vid2",
            "title": "Episode 2",
            "url": "https://youtube.com/watch?v=vid2",
            "transcript_file": "youtube/transcripts/vid2.md",
        },
    ]

    topics = {
        "vid1": ["AI", "Machine Learning", "Deep Learning"],
        "vid2": ["AI", "Machine Learning", "Data Science"],
    }

    config = {
        "speakers": ["Expert Speaker"],
        "channel_url": "https://youtube.com/channel/test",
        "model_bulk": "test",
        "model_report": "test",
        "primary_categories": []
    }

    # Create required directories
    (tmp_path / "youtube" / "metadata").mkdir(parents=True)
    (tmp_path / "youtube" / "transcripts").mkdir(parents=True)
    (tmp_path / "taxonomy").mkdir(parents=True)
    (tmp_path / "speaker-index").mkdir(parents=True)

    # Write fixture files
    (tmp_path / "config.json").write_text(json.dumps(config))
    (tmp_path / "youtube" / "metadata" / "index.json").write_text(json.dumps(index))
    (tmp_path / "taxonomy" / "topics.json").write_text(json.dumps(topics))

    # Create transcript files
    transcript1 = "Expert Speaker discusses advanced AI topics."
    (tmp_path / "youtube" / "transcripts" / "vid1.md").write_text(transcript1)

    transcript2 = "Expert Speaker continues the AI discussion."
    (tmp_path / "youtube" / "transcripts" / "vid2.md").write_text(transcript2)

    # Run the script
    script_path = Path(__file__).parents[1] / "scripts" / "07_build_speaker_index.py"
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr

    output_file = tmp_path / "speaker-index" / "speaker-index.md"
    content = output_file.read_text()

    # Should contain theme section with AI appearing in both episodes
    assert "Primary Expertise Areas" in content
    assert "AI" in content
