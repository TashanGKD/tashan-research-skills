#!/usr/bin/env python3
"""Stage fresh CriticAgent evidence for one direct-mounted adjudication."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
FIND_SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = FIND_SKILL_DIR.parents[1]
CRITIC_DIR = REPO_ROOT / "skills" / "skill-criticagent"
VENDOR_ROOT = CRITIC_DIR / "vendor" / "mcp_criticagent"
REQUIRED_FILES = (
    "runs-manifest.json",
    "trigger-decisions.json",
    "behavior-grader.json",
    "trigger-grader.json",
    "evidence-gate.json",
)
WRITABLE_EVIDENCE_GATES = {"ready_for_scorecard", "ready_for_fix_first"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def static_validation(skill_dir: Path) -> dict[str, Any]:
    sys.path.insert(0, str(VENDOR_ROOT))
    try:
        from src.core.skill_validator import validate_skill_dir

        result = validate_skill_dir(skill_dir, strict=True)
        return result.to_dict()
    finally:
        try:
            sys.path.remove(str(VENDOR_ROOT))
        except ValueError:
            pass


def provider_reports(evidence_root: Path) -> list[tuple[str, dict[str, Any]]]:
    paths = []
    for mode in ("with_skill", "without_skill"):
        for index in range(1, 4):
            paths.append((f"{mode}/case-{index}", evidence_root / mode / f"case-{index}" / "provider-report.json"))
    paths.append(("triggers/batch-1", evidence_root / "triggers" / "batch-1" / "provider-report.json"))
    missing = [label for label, path in paths if not path.is_file()]
    if missing:
        raise ValueError(f"incomplete provider evidence: {missing}")
    return [(label, load_json(path)) for label, path in paths]


def build_source_invariants(evidence_root: Path) -> dict[str, Any]:
    reports = provider_reports(evidence_root)
    with_skill = [report for label, report in reports if label.startswith("with_skill/")]
    changed = {
        label: report.get("workspace_changes") or []
        for label, report in reports
        if report.get("workspace_changes")
    }
    source_hashes = [
        (report.get("source_before") or {}).get("sha256") for report in with_skill
    ]
    return {
        "schema": "critic_source_invariants_v2",
        "all_unchanged": (
            all(report.get("status") == "pass" for _, report in reports)
            and all(report.get("source_unchanged") is True for report in with_skill)
            and len(set(source_hashes)) == 1
            and source_hashes[0] is not None
        ),
        "provider_pass_count": sum(report.get("status") == "pass" for _, report in reports),
        "provider_report_count": len(reports),
        "with_skill_source_unchanged": sum(report.get("source_unchanged") is True for report in with_skill),
        "with_skill_report_count": len(with_skill),
        "source_tree_sha256": source_hashes[0] if source_hashes else None,
        "workspace_changes": changed,
    }


def artifact_manifest(root: Path) -> dict[str, Any]:
    artifacts = []
    for path in sorted(
        (item for item in root.rglob("*") if item.is_file() and item.name != "evidence-manifest.json"),
        key=lambda item: item.relative_to(root).as_posix().casefold(),
    ):
        artifacts.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    return {
        "schema": "critic_evidence_manifest_v2",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def grader_commands(output_root: Path, skill_id: str) -> list[str]:
    behavior = CRITIC_DIR / "scripts" / "grade_runs.py"
    triggers = CRITIC_DIR / "scripts" / "grade_triggers.py"
    return [
        f'python "{behavior}" "evidence/{skill_id}" "evidence/runs-manifest.json" --summary-only',
        f'python "{triggers}" "evidence/{skill_id}" "evidence/trigger-decisions.json" --summary-only --report-only',
    ]


def build_prompt(skill_id: str, commands: list[str]) -> str:
    return f"""Directly use the mounted skill-criticagent exactly once to adjudicate the fresh isolated execution evidence in this workspace.

The current working directory is the isolated provider workspace. Evidence is mapped
under the relative `evidence/` directory for this adjudication.
Candidate skill: evidence/{skill_id}

Read evidence/evidence-manifest.json, evidence/source-invariants.json, evidence/static_validation.json, evidence/evidence-gate.json, evidence/{skill_id}/SKILL.md, evidence/{skill_id}/evals/evals.json, and evidence/{skill_id}/evals/trigger_queries.json. This is fresh isolated execution evidence for {skill_id}, not an archived re-adjudication and not source-only review. Do not use absolute paths; all evidence reads must stay under the relative `evidence/` directory.

Run these exact compact grader commands without alteration:

{commands[0]}

{commands[1]}

Do not inspect grader source or rewrite evidence. Run only the two commands above; after they finish, do not call any other tool or issue any no-op/check command. Return a concise Chinese CriticAgent verdict. Report installability, whole-case with/without counts, trigger accuracy, non-discriminating and always-failing assertion counts, source invariants, limitations, and recommend/fix-first/reject. Do not modify files or scorecards.

End the answer with exactly one fenced JSON object using this contract. Copy factual fields from evidence-gate.json, source-invariants.json, static_validation.json, and the provider run; do not infer a provider failure that is absent from evidence:

```json
{{
  "schema": "critic_final_adjudication_v1",
  "skill_id": "{skill_id}",
  "verdict": "recommend_install|fix_first|reject",
  "execution_model": "<exact evidence-gate execution_model>",
  "provider_status": "pass|fail",
  "provider_failure_count": 0,
  "with_skill_passed": 0,
  "without_skill_passed": 0,
  "trigger_accuracy": 0.0,
  "always_failing_assertions": 0,
  "source_unchanged": true,
  "static_valid": true,
  "primary_failure_class": "none|skill_quality|eval_invalid|provider_failure|source_or_workspace_drift|static_or_security",
  "scorecard_write_recommendation": false
}}
```

Use `eval_invalid` when evidence-gate.json is neither ready_for_scorecard nor ready_for_fix_first. Use `skill_quality` when a valid ready_for_fix_first package shows that the skill itself underperforms. Set scorecard_write_recommendation true when evidence-gate.json is ready_for_scorecard or ready_for_fix_first and all provider/source/static invariants pass.
"""


def stage_replay(evidence_root: Path, output_root: Path, skill_id: str) -> dict[str, Any]:
    evidence_root = evidence_root.resolve()
    output_root = output_root.resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise ValueError(f"replay output already exists and is not empty: {output_root}")
    if not skill_id or Path(skill_id).name != skill_id or skill_id in {".", ".."}:
        raise ValueError("skill ID must be one safe path component")
    eval_skill = evidence_root / "eval_skill"
    if not (eval_skill / "SKILL.md").is_file():
        raise ValueError("evidence root has no eval_skill/SKILL.md")
    for name in REQUIRED_FILES:
        if not (evidence_root / name).is_file():
            raise ValueError(f"evidence root is missing {name}")
    evidence_gate = load_json(evidence_root / "evidence-gate.json")
    gate = str(evidence_gate.get("gate") or "").strip()
    if gate not in WRITABLE_EVIDENCE_GATES:
        raise ValueError(
            "evidence gate is not scorecard-writable: "
            f"{gate or '<missing>'}; expected one of {sorted(WRITABLE_EVIDENCE_GATES)}"
        )
    output_root.mkdir(parents=True, exist_ok=True)
    staged_skill = output_root / skill_id
    shutil.copytree(eval_skill, staged_skill)
    for name in REQUIRED_FILES:
        shutil.copy2(evidence_root / name, output_root / name)
    invariants = build_source_invariants(evidence_root)
    if not invariants["all_unchanged"]:
        raise ValueError("provider evidence failed source or execution invariants")
    validation = static_validation(staged_skill)
    if not validation.get("valid"):
        raise ValueError(f"strict static validation failed: {validation.get('errors')}")
    write_json(output_root / "source-invariants.json", invariants)
    write_json(output_root / "static_validation.json", validation)
    commands = grader_commands(output_root, skill_id)
    prompt = build_prompt(skill_id, commands)
    (output_root / "provider-prompt.txt").write_text(prompt, encoding="utf-8")
    write_json(output_root / "evidence-manifest.json", artifact_manifest(output_root))
    provider_evidence = output_root / "provider-workspace" / "evidence"
    provider_evidence.mkdir(parents=True, exist_ok=True)
    for name in (*REQUIRED_FILES, "source-invariants.json", "static_validation.json", "evidence-manifest.json"):
        shutil.copy2(output_root / name, provider_evidence / name)
    shutil.copytree(output_root / skill_id, provider_evidence / skill_id)
    return {
        "output_root": str(output_root),
        "provider_workspace": str(provider_evidence.parent),
        "source_invariants": invariants,
        "static_validation": validation,
        "allowed_commands": commands,
        "prompt": prompt,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--id", required=True)
    args = parser.parse_args()
    result = stage_replay(args.evidence_root, args.output_root, args.id)
    print(json.dumps({key: value for key, value in result.items() if key != "prompt"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
