#!/usr/bin/env python3
"""Phase 10: Generate Human Workforce Intelligence Report using Claude Sonnet."""

import json
import os
import sys
from collections import Counter
from pathlib import Path

import anthropic

FORCE = "--force" in sys.argv
DRY_RUN = "--dry-run" in sys.argv

ROOT = Path(__file__).parent.parent

# cwd-first config pattern for testability
_config_path = (
    Path.cwd() / "config.json"
    if (Path.cwd() / "config.json").exists()
    else ROOT / "config.json"
)
CONFIG = json.loads(_config_path.read_text())

# Resolve paths relative to config location so tests work in tmp_path
_base = _config_path.parent
MASTER_SOURCE = _base / "notebooklm" / "master-source.md"
TOPICS_PATH = _base / "taxonomy" / "topics.json"
OUTPUT_PATH = _base / "exports" / "human-workforce-intelligence-report.md"

REPORT_PROMPT = """\
You are a senior research analyst for The Human Workforce — a platform on AI, Agentic AI, \
Workforce Transformation, Future of Work, Business Continuity, Operational Resilience, \
Technology Risk, Cybersecurity, AI Governance, Human-Machine Collaboration, and Executive Leadership.

You have access to the complete vault of Human Workforce podcast content. Produce a comprehensive \
intelligence report in this exact structure:

# Human Workforce Intelligence Report

## Executive Summary
[3–5 paragraphs distilling the most important findings across all content]

## Top 25 Themes
[Numbered list of the 25 most dominant themes with a 1-sentence description each]

## Most Important Findings
[10 bullet points — the most significant insights discovered across all episodes]

## Emerging Trends
[5–8 trends identified from recent content, with evidence]

## Workforce Predictions
[5 specific, evidence-based predictions for the workforce]

## AI Predictions
[5 specific, evidence-based predictions for AI adoption and impact]

## Governance Predictions
[5 specific, evidence-based predictions for AI governance and regulation]

## Recommended Future Books
[5 book ideas with working title, thesis, and target audience]

## Recommended Future Podcast Series
[5 podcast series ideas with concept and first 3 episode titles]

## Recommended Future Courses
[5 course ideas with title, audience, and key learning outcomes]

## Recommended Future Research Areas
[5 research areas that need more investigation]

---

Content vault summary (first 120,000 characters):
{vault_content}

---

Topic distribution:
{topic_summary}
"""


def main() -> None:
    if DRY_RUN:
        print(f"[dry-run] Would generate intelligence report -> {OUTPUT_PATH}")
        print(f"[dry-run] MASTER_SOURCE exists: {MASTER_SOURCE.exists()}")
        print(f"[dry-run] Skipping API call and file write.")
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    if not MASTER_SOURCE.exists():
        print(
            "ERROR: master-source.md not found. Run script 09 first.", file=sys.stderr
        )
        sys.exit(1)

    if OUTPUT_PATH.exists() and not FORCE:
        print(f"SKIP: {OUTPUT_PATH} already exists. Use --force to overwrite.")
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic(api_key=api_key)
    model = CONFIG["model_report"]

    vault_content = MASTER_SOURCE.read_text(encoding="utf-8")[:120_000]

    topics = json.loads(TOPICS_PATH.read_text()) if TOPICS_PATH.exists() else {}
    topic_counter: Counter = Counter()
    for topic_list in topics.values():
        topic_counter.update(topic_list)
    topic_summary = "\n".join(
        f"- {t}: {c} episodes" for t, c in topic_counter.most_common(20)
    )

    print(f"Generating intelligence report using {model}...")
    message = client.messages.create(
        model=model,
        max_tokens=8192,
        messages=[
            {
                "role": "user",
                "content": REPORT_PROMPT.format(
                    vault_content=vault_content,
                    topic_summary=topic_summary,
                ),
            }
        ],
    )

    OUTPUT_PATH.write_text(message.content[0].text, encoding="utf-8")
    print(f"Report saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
