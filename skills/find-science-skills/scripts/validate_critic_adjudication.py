#!/usr/bin/env python3
"""Validate a model CriticAgent adjudication against deterministic evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SCHEMA = "critic_final_adjudication_v1"
VERDICTS = {"recommend_install", "fix_first", "reject"}
WRITABLE_GATES = {"ready_for_scorecard", "ready_for_fix_first"}
FAILURE_CLASSES = {
    "none",
    "skill_quality",
    "eval_invalid",
    "provider_failure",
    "source_or_workspace_drift",
    "static_or_security",
}
REQUIRED_FIELDS = {
    "schema",
    "skill_id",
    "verdict",
    "execution_model",
    "provider_status",
    "provider_failure_count",
    "with_skill_passed",
    "without_skill_passed",
    "trigger_accuracy",
    "always_failing_assertions",
    "source_unchanged",
    "static_valid",
    "primary_failure_class",
    "scorecard_write_recommendation",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_decision(final_text: str) -> tuple[dict[str, Any] | None, str]:
    prose = re.sub(r"```(?:json)?\s*.*?```", "", final_text, flags=re.IGNORECASE | re.DOTALL)
    for match in reversed(
        list(re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", final_text, re.IGNORECASE | re.DOTALL))
    ):
        try:
            value = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("schema") == SCHEMA:
            return value, prose
    return None, prose


def expected_failure_class(
    *,
    verdict: str | None,
    provider_failure_count: int,
    source_unchanged: bool,
    static_valid: bool,
    gate: str,
) -> str:
    if not static_valid:
        return "static_or_security"
    if not source_unchanged:
        return "source_or_workspace_drift"
    if provider_failure_count:
        return "provider_failure"
    if gate not in WRITABLE_GATES:
        return "eval_invalid"
    if verdict == "recommend_install":
        return "none"
    return "skill_quality"


def prose_claims_provider_failure(prose: str) -> bool:
    attribution = re.compile(
        r"失败来自.{0,24}(?:provider|权限|超时|传输)"
        r"|(?:due to|caused by|because of).{0,24}(?:provider|permission|timeout|transport)"
        r"|(?:提供者|provider)[/、，,\s]+(?:权限|permission)[/、，,\s]+(?:超时|timeout)"
        r"|(?:provider|供应端|提供者).{0,20}(?:故障|崩溃|失败)",
        re.IGNORECASE,
    )
    negated = re.compile(
        r"(?:无|没有|未发生|不存在).{0,20}(?:provider|供应端|提供者)?.{0,12}(?:故障|崩溃|失败)"
        r"|(?:而非|并非|不是|不属于).{0,12}(?:provider|供应端|提供者).{0,12}(?:故障|崩溃|失败)"
        r"|provider_failures\s*[:=]\s*\[\]"
        r"|provider failures?(?: list)? (?:is |are )?(?:empty|none|zero|0)",
        re.IGNORECASE,
    )
    for line in prose.splitlines():
        if attribution.search(line) and not negated.search(line):
            return True
    return False


def validate_adjudication(
    workspace: Path,
    provider_report: Path | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace)
    report_path = Path(provider_report) if provider_report else workspace / "provider-report.json"
    report = load_json(report_path)
    evidence = load_json(workspace / "evidence-gate.json")
    invariants = load_json(workspace / "source-invariants.json")
    static = load_json(workspace / "static_validation.json")
    decision, prose = extract_decision(str(report.get("final_text") or ""))
    errors: list[str] = []

    source_unchanged = invariants.get("all_unchanged") is True
    static_valid = static.get("valid") is True
    provider_failures = evidence.get("provider_failures") or []
    provider_failure_count = len(provider_failures)
    gate = str(evidence.get("gate") or "")
    scorecard_write_allowed = (
        gate in WRITABLE_GATES
        and provider_failure_count == 0
        and source_unchanged
        and static_valid
        and report.get("status") == "pass"
    )

    if decision is None:
        errors.append("structured_decision_missing")
        return {
            "schema": "critic_adjudication_validation_v1",
            "status": "fail",
            "errors": errors,
            "scorecard_write_allowed": False,
            "decision": None,
        }

    missing = sorted(REQUIRED_FIELDS - set(decision))
    if missing:
        errors.append("structured_decision_fields_missing")
    if decision.get("verdict") not in VERDICTS:
        errors.append("verdict_invalid")
    if decision.get("primary_failure_class") not in FAILURE_CLASSES:
        errors.append("primary_failure_class_invalid")

    expected = {
        "skill_id": evidence.get("skill_id"),
        "execution_model": evidence.get("execution_model"),
        "provider_status": "pass" if provider_failure_count == 0 and report.get("status") == "pass" else "fail",
        "provider_failure_count": provider_failure_count,
        "with_skill_passed": (evidence.get("behavior") or {}).get("with_passed"),
        "without_skill_passed": (evidence.get("behavior") or {}).get("without_passed"),
        "trigger_accuracy": evidence.get("trigger_accuracy"),
        "always_failing_assertions": evidence.get("always_failing_assertions"),
        "source_unchanged": source_unchanged,
        "static_valid": static_valid,
        "scorecard_write_recommendation": scorecard_write_allowed,
    }
    error_names = {
        "skill_id": "skill_id_mismatch",
        "execution_model": "execution_model_mismatch",
        "provider_status": "provider_status_mismatch",
        "provider_failure_count": "provider_failure_count_mismatch",
        "with_skill_passed": "with_skill_passed_mismatch",
        "without_skill_passed": "without_skill_passed_mismatch",
        "trigger_accuracy": "trigger_accuracy_mismatch",
        "always_failing_assertions": "always_failing_assertions_mismatch",
        "source_unchanged": "source_unchanged_mismatch",
        "static_valid": "static_valid_mismatch",
        "scorecard_write_recommendation": "scorecard_write_recommendation_mismatch",
    }
    for field, expected_value in expected.items():
        if decision.get(field) != expected_value:
            errors.append(error_names[field])

    expected_primary_failure = expected_failure_class(
        verdict=decision.get("verdict"),
        provider_failure_count=provider_failure_count,
        source_unchanged=source_unchanged,
        static_valid=static_valid,
        gate=gate,
    )
    expected["primary_failure_class"] = expected_primary_failure
    if decision.get("primary_failure_class") != expected_primary_failure:
        errors.append("primary_failure_class_mismatch")

    if provider_failure_count == 0 and prose_claims_provider_failure(prose):
        errors.append("prose_provider_failure_contradiction")

    return {
        "schema": "critic_adjudication_validation_v1",
        "status": "pass" if not errors else "fail",
        "errors": list(dict.fromkeys(errors)),
        "scorecard_write_allowed": scorecard_write_allowed and not errors,
        "decision": decision,
        "expected": expected,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--provider-report", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate_adjudication(args.workspace, args.provider_report)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
