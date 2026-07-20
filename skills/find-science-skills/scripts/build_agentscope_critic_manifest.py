#!/usr/bin/env python3
"""Build a CriticAgent runs manifest from validated AgentScope reports."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


DEFAULT_ARTIFACT = "outputs/verification-report.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_report(
    report: dict[str, Any],
    workspace: Path,
    artifact: str | None = DEFAULT_ARTIFACT,
    allow_missing_artifact: bool = False,
) -> None:
    reasons = []
    if report.get("status") != "pass":
        reasons.append(f"status={report.get('status')}")
    if report.get("source_unchanged") is not True:
        reasons.append("source changed")
    if Path(str(report.get("workspace", ""))).resolve() != workspace.resolve():
        reasons.append("workspace mismatch")
    artifact_exists = bool(artifact and (workspace / artifact).is_file())
    expected_changes = [artifact] if artifact_exists else []
    if report.get("workspace_changes") != expected_changes:
        reasons.append(f"unexpected changes={report.get('workspace_changes')}")
    if artifact and not artifact_exists and not allow_missing_artifact:
        reasons.append("declared artifact missing")
    if reasons:
        raise ValueError("provider report is not gradeable: " + "; ".join(reasons))


def _blocks(report: dict[str, Any]):
    for message in report.get("context") or []:
        for block in message.get("content") or []:
            if isinstance(block, dict):
                yield message, block


def provider_prompt(report: dict[str, Any]) -> str:
    for message, block in _blocks(report):
        if message.get("role") == "user" and block.get("type") == "text":
            return str(block.get("text", ""))
    return ""


def openai_tool_calls(report: dict[str, Any]) -> list[dict[str, Any]]:
    calls = []
    for _, block in _blocks(report):
        if block.get("type") != "tool_call":
            continue
        arguments = block.get("input", "")
        if not isinstance(arguments, str):
            arguments = json.dumps(arguments, ensure_ascii=False, separators=(",", ":"))
        calls.append(
            {
                "id": str(block.get("id", "")),
                "type": "function",
                "function": {
                    "name": str(block.get("name", "")),
                    "arguments": arguments,
                },
            }
        )
    return calls


def _mode_spec(
    workspace: Path,
    artifact: str | None,
    grade_artifact_output: bool = False,
    allow_missing_artifact: bool = False,
) -> dict[str, Any]:
    report_path = workspace / "provider-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    validate_report(report, workspace, artifact, allow_missing_artifact)
    artifact_exists = bool(artifact and (workspace / artifact).is_file())
    spec = {
        "outputs_dir": str((workspace / "outputs").resolve()),
        "tool_calls": openai_tool_calls(report),
        "provider_prompt": provider_prompt(report),
        "provider_final_text": str(report.get("final_text", "")),
        "provider_report": str(report_path.resolve()),
        "provider_report_sha256": sha256(report_path),
        "artifact_requirement": (
            "pass" if artifact_exists else "missing" if artifact else "not_applicable"
        ),
    }
    if grade_artifact_output and artifact_exists:
        if not artifact:
            raise ValueError("artifact output grading requires a declared artifact")
        artifact_path = (workspace / artifact).resolve()
        spec["output_file"] = str(artifact_path)
    else:
        spec["output"] = str(report.get("final_text", ""))
    return spec


def build_manifest(
    skill_dir: Path,
    run_root: Path,
    attempts: list[str],
    artifacts: list[str] | None = None,
    grade_artifact_output: bool = False,
    artifact_required: bool = True,
    derive_case_contracts: bool = False,
):
    evals_path = skill_dir / "evals" / "evals.json"
    payload = json.loads(evals_path.read_text(encoding="utf-8"))
    cases = payload.get("evals") or []
    if len(cases) != len(attempts):
        raise ValueError(
            f"expected {len(cases)} attempt directories, received {len(attempts)}"
        )
    if derive_case_contracts:
        if artifacts:
            raise ValueError("explicit artifacts conflict with derived case contracts")
        artifacts = [case.get("artifact_path") for case in cases]
        grade_artifact_outputs = [case.get("mode") == "artifact" for case in cases]
    else:
        grade_artifact_outputs = [grade_artifact_output] * len(cases)
    if not artifact_required and artifacts and not derive_case_contracts:
        raise ValueError("artifacts cannot be declared when artifact_required is false")
    artifacts = artifacts or (
        [DEFAULT_ARTIFACT] * len(cases)
        if artifact_required and not derive_case_contracts
        else [None] * len(cases)
    )
    if len(artifacts) != len(cases):
        raise ValueError(
            f"expected {len(cases)} artifact paths, received {len(artifacts)}"
        )
    runs = []
    for case, attempt, artifact, grade_output in zip(
        cases, attempts, artifacts, grade_artifact_outputs
    ):
        runs.append(
            {
                "case_id": str(case.get("id", "")),
                "prompt": str(case.get("prompt", "")),
                "with_skill": _mode_spec(
                    run_root / "with_skill" / attempt,
                    artifact,
                    grade_output,
                ),
                "without_skill": _mode_spec(
                    run_root / "without_skill" / attempt,
                    artifact,
                    grade_output,
                    allow_missing_artifact=True,
                ),
            }
        )
    return {
        "schema_version": 1,
        "source": "agentscope_provider_reports",
        "eval_skill": str(skill_dir.resolve()),
        "evals_sha256": sha256(evals_path),
        "runs": runs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir", type=Path)
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--attempt", action="append", required=True)
    artifact_group = parser.add_mutually_exclusive_group()
    artifact_group.add_argument("--artifact", action="append")
    artifact_group.add_argument(
        "--no-artifacts",
        action="store_true",
        help="guidance-only run: require no workspace changes and grade host final text",
    )
    parser.add_argument(
        "--grade-artifact-output",
        action="store_true",
        help="grade text assertions against the declared artifact instead of host final text",
    )
    parser.add_argument(
        "--derive-case-contracts",
        action="store_true",
        help="derive per-case artifact requirements from eval mode and artifact_path",
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    manifest = build_manifest(
        args.skill_dir,
        args.run_root,
        args.attempt,
        args.artifact,
        args.grade_artifact_output,
        artifact_required=not args.no_artifacts,
        derive_case_contracts=args.derive_case_contracts,
    )
    rendered = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
