#!/usr/bin/env python3
"""Apply a reviewed behavior/trigger report to the v2 critic scorecard."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from finalize_critic_scores import atomic_write_json, decision_for_layers  # noqa: E402


SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_SCORECARD = SKILL_DIR / "data" / "science_skill_critic_scores.json"


def apply_report(scorecard: dict, report: dict) -> dict:
    if scorecard.get("schema") != "science_skill_critic_scores_v2":
        raise ValueError("scorecard must use science_skill_critic_scores_v2")
    if report.get("schema") != "science_skill_critic_evaluation_v1":
        raise ValueError("report must use science_skill_critic_evaluation_v1")
    skill_id = report.get("id")
    matches = [record for record in scorecard["scores"] if record.get("id") == skill_id]
    if len(matches) != 1:
        raise ValueError(f"scorecard must contain exactly one record for {skill_id!r}")
    record = matches[0]
    if record.get("critic_source_sha256") != report.get("critic_source_sha256"):
        raise ValueError("evaluation source hash does not match the scorecard")
    if record.get("static_validation_status") != "pass":
        raise ValueError("behavior evaluation cannot override a static validation failure")

    behavior = report.get("behavior_evaluation")
    trigger = report.get("trigger_evaluation")
    allowed = {"pass", "fail", "unverifiable"}
    if not isinstance(behavior, dict) or behavior.get("status") not in allowed:
        raise ValueError("behavior_evaluation requires pass, fail, or unverifiable status")
    if not isinstance(trigger, dict) or trigger.get("status") not in allowed:
        raise ValueError("trigger_evaluation requires pass, fail, or unverifiable status")
    status, recommendation, behavior_tested, trigger_tested = decision_for_layers(
        static_status=record["static_validation_status"],
        static_errors=record.get("static_validation_errors", []),
        source_review_verdict=record.get("model_source_review_verdict"),
        behavior=behavior,
        trigger=trigger,
    )
    if report.get("formal_kernel_run") is not True:
        status = "provisional_behavior_and_trigger"
        recommendation = "not_yet_evaluated"
    record.update(
        {
            "behavior_tested": behavior_tested,
            "behavior_evaluation": behavior,
            "trigger_tested": trigger_tested,
            "trigger_evaluation": trigger,
            "evaluation_provenance": {
                key: report[key]
                for key in (
                    "evaluated_at",
                    "method",
                    "formal_kernel_run",
                    "known_limit",
                    "kernel_probe",
                    "agents",
                )
                if key in report
            },
            "evaluation_status": status,
            "install_recommendation": recommendation,
        }
    )
    return scorecard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    parser.add_argument("--scorecard", default=str(DEFAULT_SCORECARD))
    args = parser.parse_args(argv)
    scorecard_path = pathlib.Path(args.scorecard)
    scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
    report = json.loads(pathlib.Path(args.report).read_text(encoding="utf-8"))
    apply_report(scorecard, report)
    atomic_write_json(scorecard_path, scorecard)
    print(f"Applied evaluation for {report['id']} to {scorecard_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
