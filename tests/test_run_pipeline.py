import json
import subprocess
import sys
from pathlib import Path


def test_pipeline_state_file_created(tmp_path):
    """Test that pipeline runner creates pipeline-state.json file."""
    project_root = Path(__file__).parents[1]

    # Create minimal config in tmp_path
    config = {
        "channel_url": "https://www.youtube.com/watch?v=test",
        "model_bulk": "claude-haiku-4-5-20251001",
        "model_report": "claude-sonnet-4-6",
        "speakers": [],
        "primary_categories": []
    }
    (tmp_path / "config.json").write_text(json.dumps(config))

    # Create required directories
    (tmp_path / "youtube" / "metadata").mkdir(parents=True)

    # Write a test script that mocks subprocess
    test_script = tmp_path / "test_runner.py"
    test_script.write_text(f'''
import json
import sys
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

# Set sys.argv FIRST before importing, so module-level variables are set correctly
sys.argv = ["run_pipeline.py", "--from=6"]

# Mock subprocess.run to return success
mock_result = MagicMock()
mock_result.returncode = 0

with patch("subprocess.run", return_value=mock_result):
    # Add the scripts directory to path
    sys.path.insert(0, "{str(project_root / 'scripts')}")

    # Now import the pipeline
    import run_pipeline

    # Replace ROOT with tmp_path
    run_pipeline.ROOT = Path("{str(tmp_path)}")
    run_pipeline.STATE_FILE = run_pipeline.ROOT / "pipeline-state.json"

    try:
        run_pipeline.main()
    except SystemExit:
        pass
''')

    # Run the test script
    result = subprocess.run(
        [sys.executable, str(test_script)],
        capture_output=True,
        text=True
    )

    # Verify state file was created
    state_file = tmp_path / "pipeline-state.json"
    assert state_file.exists(), f"pipeline-state.json not created. stderr: {result.stderr}"

    # Verify state structure
    state = json.loads(state_file.read_text())
    assert "completed" in state
    assert "runs" in state
    assert len(state["runs"]) >= 1
    assert "steps" in state["runs"][0]
    # Steps 6-10 = 5 steps
    assert len(state["runs"][0]["steps"]) == 5


def test_pipeline_state_has_run_metadata(tmp_path):
    """Test that pipeline state tracks run metadata (started, steps with timestamps)."""
    project_root = Path(__file__).parents[1]

    config = {
        "channel_url": "https://www.youtube.com/watch?v=test",
        "model_bulk": "claude-haiku-4-5-20251001",
        "model_report": "claude-sonnet-4-6",
        "speakers": [],
        "primary_categories": []
    }
    (tmp_path / "config.json").write_text(json.dumps(config))
    (tmp_path / "youtube" / "metadata").mkdir(parents=True)

    test_script = tmp_path / "test_runner.py"
    test_script.write_text(f'''
import json
import sys
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.argv = ["run_pipeline.py", "--from=8"]

mock_result = MagicMock()
mock_result.returncode = 0

with patch("subprocess.run", return_value=mock_result):
    sys.path.insert(0, "{str(project_root / 'scripts')}")
    import run_pipeline

    run_pipeline.ROOT = Path("{str(tmp_path)}")
    run_pipeline.STATE_FILE = run_pipeline.ROOT / "pipeline-state.json"

    try:
        run_pipeline.main()
    except SystemExit:
        pass
''')

    result = subprocess.run(
        [sys.executable, str(test_script)],
        capture_output=True,
        text=True
    )

    state_file = tmp_path / "pipeline-state.json"
    assert state_file.exists()

    state = json.loads(state_file.read_text())
    run_record = state["runs"][0]

    # Verify run metadata
    assert "started" in run_record
    assert "steps" in run_record
    assert len(run_record["steps"]) == 3  # Steps 8, 9, 10

    # Verify step records
    for step in run_record["steps"]:
        assert "name" in step
        assert "returncode" in step
        assert "timestamp" in step
        assert step["returncode"] == 0


def test_pipeline_skip_output(tmp_path):
    """Test that skipped steps are printed to output."""
    project_root = Path(__file__).parents[1]

    config = {
        "channel_url": "https://www.youtube.com/watch?v=test",
        "model_bulk": "claude-haiku-4-5-20251001",
        "model_report": "claude-sonnet-4-6",
        "speakers": [],
        "primary_categories": []
    }
    (tmp_path / "config.json").write_text(json.dumps(config))
    (tmp_path / "youtube" / "metadata").mkdir(parents=True)

    test_script = tmp_path / "test_runner.py"
    test_script.write_text(f'''
import json
import sys
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.argv = ["run_pipeline.py", "--from=7"]

mock_result = MagicMock()
mock_result.returncode = 0

with patch("subprocess.run", return_value=mock_result):
    sys.path.insert(0, "{str(project_root / 'scripts')}")
    import run_pipeline

    run_pipeline.ROOT = Path("{str(tmp_path)}")
    run_pipeline.STATE_FILE = run_pipeline.ROOT / "pipeline-state.json"

    try:
        run_pipeline.main()
    except SystemExit:
        pass
''')

    result = subprocess.run(
        [sys.executable, str(test_script)],
        capture_output=True,
        text=True
    )

    # Verify skip messages appear in output
    assert "SKIP (--from=7)" in result.stdout
    assert "01_collect_metadata" in result.stdout
