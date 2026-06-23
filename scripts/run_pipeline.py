#!/usr/bin/env python3
"""Master pipeline runner — executes all vault-building scripts in sequence."""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
STATE_FILE = ROOT / "pipeline-state.json"

SCRIPTS = [
    ("01_collect_metadata", "scripts/01_collect_metadata.py"),
    ("02_collect_transcripts", "scripts/02_collect_transcripts.py"),
    ("03_summarize_episodes", "scripts/03_summarize_episodes.py"),
    ("04_extract_entities_topics", "scripts/04_extract_entities_topics.py"),
    ("05_build_knowledge_graph", "scripts/05_build_knowledge_graph.py"),
    ("06_build_master_index", "scripts/06_build_master_index.py"),
    ("07_build_speaker_index", "scripts/07_build_speaker_index.py"),
    ("08_generate_shorts", "scripts/08_generate_shorts.py"),
    ("09_prepare_notebooklm", "scripts/09_prepare_notebooklm.py"),
    ("10_generate_report", "scripts/10_generate_report.py"),
]

RESUME = "--resume" in sys.argv
FROM_STEP = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--from=")), 1)


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"completed": [], "runs": []}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def main() -> None:
    state = load_state()
    completed = set(state["completed"]) if RESUME else set()
    if not RESUME:
        state["completed"] = []  # reset for this run, preserve run history

    run_record = {"started": datetime.now().isoformat(), "steps": []}
    state["runs"].append(run_record)

    for i, (name, script_path) in enumerate(SCRIPTS, start=1):
        if i < FROM_STEP:
            print(f"[{i:02d}/{len(SCRIPTS)}] SKIP (--from={FROM_STEP}): {name}")
            continue
        if RESUME and name in completed:
            print(f"[{i:02d}/{len(SCRIPTS)}] SKIP (already done): {name}")
            continue

        print(f"\n{'='*60}")
        print(f"[{i:02d}/{len(SCRIPTS)}] Running: {name}")
        print(f"{'='*60}")

        result = subprocess.run(
            [sys.executable, str(ROOT / script_path)],
            cwd=ROOT
        )

        step_record = {
            "name": name,
            "returncode": result.returncode,
            "timestamp": datetime.now().isoformat()
        }
        run_record["steps"].append(step_record)

        if result.returncode == 0:
            state["completed"].append(name)
            save_state(state)
            print(f"✓ {name} completed successfully")
        else:
            save_state(state)
            print(f"\nPipeline stopped at step {i}: {name} failed (exit code {result.returncode})")
            print("Fix the issue and re-run with: python scripts/run_pipeline.py --resume")
            sys.exit(result.returncode)

    print(f"\n{'='*60}")
    print("PIPELINE COMPLETE")
    print(f"{'='*60}")
    print(f"All {len(SCRIPTS)} steps finished. Vault ready at: {ROOT}")


if __name__ == "__main__":
    main()
