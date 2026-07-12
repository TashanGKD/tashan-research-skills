#!/usr/bin/env python3
"""Migrate source-review scores into an evidence-layered CriticAgent scorecard."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import tempfile


SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_INPUT = SKILL_DIR / "data" / "science_skill_critic_scores.json"
DEFAULT_OUTPUT = DEFAULT_INPUT
DEFAULT_CATALOG = SKILL_DIR / "data" / "science_skill_catalog.json"
SCHEMA = "science_skill_critic_scores_v2"


def atomic_write_json(path: pathlib.Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def is_directory_name_error(message: object) -> bool:
    return isinstance(message, str) and message.startswith("Directory name '")


def is_security_error(message: object) -> bool:
    return isinstance(message, str) and message.startswith("Security (")


def _evaluation(record: dict, field: str) -> dict:
    value = record.get(field)
    if not isinstance(value, dict):
        return {"status": "not_run"}
    status = value.get("status")
    if status not in {"pass", "fail", "not_run", "unverifiable"}:
        return {**value, "status": "unverifiable"}
    return value


def decision_for_layers(
    *,
    static_status: str,
    static_errors: list,
    source_review_verdict: str | None,
    behavior: dict,
    trigger: dict,
) -> tuple[str, str, bool, bool]:
    behavior_tested = behavior.get("status") in {"pass", "fail"}
    trigger_tested = trigger.get("status") in {"pass", "fail"}

    if static_status == "source_unavailable":
        return "unverified", "unverified", behavior_tested, trigger_tested
    if any(is_security_error(error) for error in static_errors):
        return "security_failed", "reject", behavior_tested, trigger_tested
    if static_status == "fail":
        return "static_failed", "fix_first", behavior_tested, trigger_tested
    if static_status != "pass":
        return "static_not_checked", "unverified", behavior_tested, trigger_tested
    if not behavior_tested and not trigger_tested:
        recommendation = (
            "not_yet_evaluated" if source_review_verdict == "recommend" else "fix_first"
        )
        return "needs_behavior_and_trigger", recommendation, False, False
    if not behavior_tested:
        return "needs_behavior", "not_yet_evaluated", False, trigger_tested
    if not trigger_tested:
        return "needs_trigger", "not_yet_evaluated", behavior_tested, False
    if behavior["status"] == "fail" or trigger["status"] == "fail":
        return "behavior_or_trigger_failed", "fix_first", True, True
    recommendation = (
        "recommend_install" if source_review_verdict == "recommend" else "fix_first"
    )
    return "complete", recommendation, True, True


def finalize_record(record: dict) -> dict:
    """Separate model review, static validity, behavior, and trigger evidence."""

    evidence_level = record.get("critic_evidence_level")
    legacy_score = record.get("critic_content_score")
    source_review_score = legacy_score if evidence_level == "full_source" else None
    legacy_metadata_score = legacy_score if evidence_level == "metadata_only" else None
    source_review_verdict = record.get("critic_verdict")

    original_status = record.get("critic_package_status", "not_checked")
    original_errors = list(record.get("errors") or [])
    warnings = list(record.get("warnings") or [])
    substantive_errors = [error for error in original_errors if not is_directory_name_error(error)]
    normalized_directory = len(substantive_errors) < len(original_errors)

    if original_status == "source_unavailable" or evidence_level == "metadata_only":
        static_status = "source_unavailable"
        static_mode = "not_run"
        static_errors = []
    elif original_status == "not_checked":
        static_status = "not_checked"
        static_mode = "not_run"
        static_errors = original_errors
    else:
        static_errors = substantive_errors
        static_status = "fail" if static_errors else "pass"
        static_mode = (
            "normalized_install_directory"
            if normalized_directory
            else "source_directory"
        )

    behavior = _evaluation(record, "behavior_evaluation")
    trigger = _evaluation(record, "trigger_evaluation")
    evaluation_status, recommendation, behavior_tested, trigger_tested = (
        decision_for_layers(
            static_status=static_status,
            static_errors=static_errors,
            source_review_verdict=source_review_verdict,
            behavior=behavior,
            trigger=trigger,
        )
    )

    excluded = {
        "critic_content_score",
        "critic_verdict",
        "critic_package_status",
        "errors",
        "warnings",
        "behavior_evaluation",
        "trigger_evaluation",
    }
    preserved = {key: value for key, value in record.items() if key not in excluded}
    return {
        **preserved,
        "model_source_review_score": source_review_score,
        "legacy_metadata_score": legacy_metadata_score,
        "model_source_review_verdict": source_review_verdict,
        "static_checked": static_status in {"pass", "fail"},
        "static_validation_status": static_status,
        "static_validation_mode": static_mode,
        "static_validation_errors": static_errors,
        "static_validation_warnings": warnings,
        "behavior_tested": behavior_tested,
        "behavior_evaluation": behavior,
        "trigger_tested": trigger_tested,
        "trigger_evaluation": trigger,
        "evaluation_status": evaluation_status,
        "install_recommendation": recommendation,
    }


def build_scorecard(source: dict, catalog_path: pathlib.Path) -> dict:
    catalog_sha = hashlib.sha256(catalog_path.read_bytes()).hexdigest()
    if source.get("catalog_sha256") != catalog_sha:
        raise ValueError("input scorecard catalog hash does not match the current catalog")
    records = [finalize_record(record) for record in source.get("scores", [])]
    ids = [record.get("id") for record in records]
    if not all(isinstance(skill_id, str) for skill_id in ids):
        raise ValueError("all score records require string ids")
    if len(ids) != len(set(ids)):
        raise ValueError("input scorecard contains duplicate ids")
    return {
        "schema": SCHEMA,
        "catalog_sha256": catalog_sha,
        "model": source.get("model"),
        "rubric_version": source.get("rubric_version"),
        "finalization_version": "critic-evidence-contract-v2",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "score_count": len(records),
        "failures": list(source.get("failures") or []),
        "scores": records,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="将源码评审分迁移为分层、不可误读的 CriticAgent v2 证据。"
    )
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    args = parser.parse_args(argv)
    input_path = pathlib.Path(args.input)
    output_path = pathlib.Path(args.output)
    source = json.loads(input_path.read_text(encoding="utf-8"))
    if source.get("schema") != "science_skill_critic_scores_v1":
        raise SystemExit("input must be the immutable v1 source-review scorecard")
    payload = build_scorecard(source, pathlib.Path(args.catalog))
    atomic_write_json(output_path, payload)
    print(f"Wrote {payload['score_count']} records to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
