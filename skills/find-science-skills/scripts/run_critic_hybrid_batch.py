#!/usr/bin/env python3
"""Run one resumable DeepSeek CriticAgent quick batch without mutating scores."""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import hashlib
import json
import os
import pathlib
import re
import shutil
import string
import subprocess
import sys
import time
from typing import Any


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SKILL_DIR.parents[1]
DEFAULT_RUNS = SKILL_DIR / "data" / "critic_evaluation_runs"
DEFAULT_RUNNER = SCRIPT_DIR / "run_agentscope_critic_provider.py"
DEFAULT_AGENTSCOPE_SRC = pathlib.Path(
    r"C:\Users\16571\Documents\Codex\2026-06-05\topiclink-clean-context\work\open-source\agentscope\src"
)
DEFAULT_MODEL = "deepseek-v4-flash-260425"
DEFAULT_API_KEY_ENV = "ARK_API_KEY"
DETERMINISTIC_ASSERTIONS = {"contains", "not_contains", "regex", "equals"}
CASE_MODES = {"guidance", "artifact", "tool"}
FILE_ASSERTION_TYPES = {
    "file-exists",
    "file-not-exists",
    "file-contains",
    "file-matches",
}
POSITIVE_FILE_ASSERTION_TYPES = {"file-exists", "file-contains", "file-matches"}


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_case_fixtures(
    eval_skill: pathlib.Path,
    fixtures: Any,
) -> list[dict[str, str]]:
    if fixtures is None:
        return []
    if not isinstance(fixtures, list):
        raise ValueError("case fixtures must be an array")
    normalized: list[dict[str, str]] = []
    targets: set[str] = set()
    root = eval_skill.resolve()
    for fixture in fixtures:
        if not isinstance(fixture, dict):
            raise ValueError("case fixture must be an object")
        source_value = str(fixture.get("source_path") or "").replace("\\", "/")
        target_value = str(fixture.get("target_path") or "").replace("\\", "/")
        source_path = pathlib.PurePosixPath(source_value)
        target_path = pathlib.PurePosixPath(target_value)
        if (
            not source_value
            or source_path.is_absolute()
            or ".." in source_path.parts
            or ":" in source_path.parts[0]
        ):
            raise ValueError("fixture source_path must stay inside the eval skill")
        if (
            not target_value
            or target_path.is_absolute()
            or ".." in target_path.parts
            or not target_path.parts
            or target_path.parts[0] != "inputs"
        ):
            raise ValueError("fixture target_path must stay under inputs/")
        target = target_path.as_posix()
        if target in targets:
            raise ValueError("fixture target_path values must be unique")
        source = (root / source_path.as_posix()).resolve()
        try:
            source.relative_to(root)
        except ValueError as exc:
            raise ValueError("fixture source escapes the eval skill") from exc
        if not source.is_file():
            raise ValueError(f"fixture source is missing: {source_path.as_posix()}")
        targets.add(target)
        normalized.append(
            {
                "source_path": source_path.as_posix(),
                "target_path": target,
                "sha256": sha256(source),
            }
        )
    return normalized


def stage_case_fixtures(
    eval_skill: pathlib.Path,
    workspace: pathlib.Path,
    fixtures: list[dict[str, str]],
) -> None:
    for fixture in fixtures:
        source = (eval_skill / fixture["source_path"]).resolve()
        target = (workspace / fixture["target_path"]).resolve()
        try:
            target.relative_to(workspace.resolve())
        except ValueError as exc:
            raise ValueError("fixture target escapes the evaluation workspace") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if not target.is_file() or sha256(target) != fixture["sha256"]:
                raise ValueError(f"staged fixture drift: {fixture['target_path']}")
            continue
        shutil.copy2(source, target)


def declared_output_paths(case: dict[str, Any]) -> list[str]:
    """Return the exact writable files required by positive artifact checks."""
    outputs: list[str] = []
    primary = case.get("artifact_path")
    if primary:
        outputs.append(pathlib.PurePosixPath(str(primary).replace("\\", "/")).as_posix())
    for assertion in case.get("file_assertions") or []:
        if not isinstance(assertion, dict) or assertion.get("type") not in FILE_ASSERTION_TYPES:
            raise ValueError("file assertions require a supported type")
        raw_path = str(assertion.get("path") or "").replace("\\", "/")
        path = pathlib.PurePosixPath(raw_path)
        if (
            not raw_path
            or path.is_absolute()
            or ".." in path.parts
            or ":" in path.parts[0]
            or (path.parts and path.parts[0] == "outputs")
        ):
            raise ValueError("file assertion path must be relative to outputs/")
        if assertion["type"] in POSITIVE_FILE_ASSERTION_TYPES:
            output = (pathlib.PurePosixPath("outputs") / path).as_posix()
            if output not in outputs:
                outputs.append(output)
    return outputs


def expand_command_template(
    template: str,
    *,
    eval_skill: pathlib.Path,
    workspace: pathlib.Path,
) -> str:
    fields = {
        field_name
        for _, field_name, _, _ in string.Formatter().parse(template)
        if field_name is not None
    }
    if not fields.issubset({"skill_dir", "workspace"}):
        raise ValueError(f"unsupported command template fields: {sorted(fields)}")
    return template.format(
        skill_dir=eval_skill.resolve().as_posix(),
        workspace=workspace.resolve().as_posix(),
    )


def load_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: pathlib.Path, value: Any) -> None:
    rendered = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    temp = path.with_suffix(path.suffix + ".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp.write_text(rendered, encoding="utf-8")
    os.replace(temp, path)


def frontmatter_value(text: str, key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.+?)\s*$", text)
    return match.group(1).strip().strip("\"'") if match else ""


def validate_eval_pack(eval_skill: pathlib.Path) -> dict[str, Any]:
    skill_path = eval_skill / "SKILL.md"
    evals_path = eval_skill / "evals" / "evals.json"
    triggers_path = eval_skill / "evals" / "trigger_queries.json"
    if not skill_path.is_file() or not evals_path.is_file() or not triggers_path.is_file():
        raise ValueError("eval pack requires SKILL.md, evals.json, and trigger_queries.json")
    skill_text = skill_path.read_text(encoding="utf-8-sig")
    skill_name = frontmatter_value(skill_text, "name") or eval_skill.name
    evals = load_json(evals_path).get("evals")
    if not isinstance(evals, list) or len(evals) != 3:
        raise ValueError("quick eval pack must contain exactly three behavior cases")
    ids: set[str] = set()
    for index, case in enumerate(evals):
        case_id = str(case.get("id") or "")
        if not case_id or case_id in ids:
            raise ValueError("behavior case IDs must be non-empty and unique")
        ids.add(case_id)
        if not str(case.get("prompt") or "").strip():
            raise ValueError(f"behavior case {index + 1} requires a prompt")
        mode = case.get("mode") or "guidance"
        if mode not in CASE_MODES:
            raise ValueError(f"behavior case {case_id} has unsupported mode: {mode}")
        case["mode"] = mode
        artifact = case.get("artifact_path")
        commands = case.get("allowed_commands") or []
        if not isinstance(commands, list) or not all(
            isinstance(command, str) and command.strip() for command in commands
        ):
            raise ValueError(f"behavior case {case_id} has invalid allowed_commands")
        case["allowed_commands"] = commands
        case["fixtures"] = validate_case_fixtures(
            eval_skill,
            case.get("fixtures"),
        )
        if mode == "guidance" and (artifact or commands):
            raise ValueError("guidance cases cannot declare output or command permissions")
        if mode == "artifact":
            artifact_value = str(artifact or "").replace("\\", "/")
            artifact_path = pathlib.PurePosixPath(artifact_value)
            if (
                not artifact
                or artifact_path.is_absolute()
                or ".." in artifact_path.parts
                or not artifact_path.parts
                or artifact_path.parts[0] != "outputs"
            ):
                raise ValueError("artifact cases require a safe artifact_path under outputs/")
            if artifact_value.endswith("/"):
                raise ValueError("artifact_path must name a file, not a directory")
        assertions = case.get("assertions")
        file_assertions = case.get("file_assertions") or []
        tool_assertions = case.get("tool_assertions") or []
        if not isinstance(assertions, list):
            raise ValueError(f"behavior case {case_id} requires deterministic assertions")
        if not isinstance(file_assertions, list) or not isinstance(tool_assertions, list):
            raise ValueError(f"behavior case {case_id} has invalid file/tool assertions")
        if not assertions and not file_assertions and not tool_assertions:
            raise ValueError(f"behavior case {case_id} requires deterministic assertions")
        for assertion in assertions:
            if not isinstance(assertion, dict) or assertion.get("type") not in DETERMINISTIC_ASSERTIONS:
                raise ValueError("quick tier accepts deterministic typed assertions only")
            if not str(assertion.get("value") or "").strip():
                raise ValueError("deterministic assertion values must be non-empty")
        declared_output_paths(case)
    trigger_payload = load_json(triggers_path)
    triggers = (
        trigger_payload
        if isinstance(trigger_payload, list)
        else trigger_payload.get("trigger_queries") or trigger_payload.get("queries")
        if isinstance(trigger_payload, dict)
        else None
    )
    if not isinstance(triggers, list) or len(triggers) != 8:
        raise ValueError("quick eval pack must contain exactly eight trigger queries")
    positive = sum(query.get("should_trigger") is True for query in triggers)
    negative = sum(query.get("should_trigger") is False for query in triggers)
    if (positive, negative) != (4, 4):
        raise ValueError("trigger queries must contain four positive and four negative cases")
    if len({str(query.get("query") or "").strip() for query in triggers}) != 8:
        raise ValueError("trigger query text must be non-empty and unique")
    return {
        "skill_name": skill_name,
        "description": frontmatter_value(skill_text, "description"),
        "case_count": len(evals),
        "trigger_count": len(triggers),
        "evals": evals,
        "triggers": triggers,
        "case_modes": dict(
            sorted(collections.Counter(case["mode"] for case in evals).items())
        ),
        "skill_sha256": sha256(skill_path),
        "evals_sha256": sha256(evals_path),
        "triggers_sha256": sha256(triggers_path),
    }


def trigger_prompt(pack: dict[str, Any]) -> str:
    queries = [query["query"] for query in pack["triggers"]]
    return (
        "Decide whether the target Agent Skill should activate for each query. "
        "Use only the supplied name and description. Return strict JSON only as "
        "{\"decisions\":[{\"query\":<verbatim>,\"decision\":<skill-name-or-none>},...]}. "
        "Preserve order and query text exactly.\n\n"
        f"Skill name: {pack['skill_name']}\n"
        f"Skill description: {pack['description']}\n"
        f"Queries: {json.dumps(queries, ensure_ascii=False)}"
    )


def build_jobs(
    *,
    skill_id: str,
    eval_skill: pathlib.Path,
    run_root: pathlib.Path,
    model: str,
    agentscope_src: pathlib.Path,
    runner: pathlib.Path,
    base_url: str | None = None,
    api_key_env: str = DEFAULT_API_KEY_ENV,
    protocol: str = "openai",
    auth_mode: str = "api-key",
    max_output_tokens: int | None = None,
    disable_thinking: bool = False,
) -> list[dict[str, Any]]:
    pack = validate_eval_pack(eval_skill)
    jobs: list[dict[str, Any]] = []
    common = [
        str(runner),
        "--model",
        model,
        "--agentscope-src",
        str(agentscope_src),
        "--timeout",
        "120",
        "--run-timeout",
        "180",
        "--max-iters",
        "10",
        "--api-key-env",
        api_key_env,
        "--protocol",
        protocol,
        "--auth-mode",
        auth_mode,
    ]
    if base_url:
        common.extend(["--base-url", base_url])
    if max_output_tokens is not None:
        common.extend(["--max-output-tokens", str(max_output_tokens)])
    if disable_thinking:
        common.append("--disable-thinking")
    for case_index, case in enumerate(pack["evals"], start=1):
        attempt = f"case-{case_index}"
        for mode in ("with_skill", "without_skill"):
            workspace = run_root / mode / attempt
            workspace.mkdir(parents=True, exist_ok=True)
            stage_case_fixtures(eval_skill, workspace, case.get("fixtures") or [])
            prompt_path = workspace / "provider-prompt.txt"
            prompt_path.write_text(str(case["prompt"]), encoding="utf-8")
            report = workspace / "provider-report.json"
            args = [
                *common,
                "--workspace",
                str(workspace),
                "--prompt-file",
                str(prompt_path),
                "--output",
                str(report),
            ]
            case_mode = case.get("mode", "guidance")
            if case_mode == "guidance":
                args.extend(["--allow-no-tool", "--guidance-only"])
            else:
                for artifact in declared_output_paths(case):
                    args.extend(["--allow-output", artifact])
                if mode == "with_skill":
                    for command in case.get("allowed_commands") or []:
                        args.extend(
                            [
                                "--allow-command",
                                expand_command_template(
                                    str(command),
                                    eval_skill=eval_skill,
                                    workspace=workspace,
                                ),
                            ]
                        )
            if mode == "with_skill":
                args.extend(["--skill-dir", str(eval_skill)])
            jobs.append(
                {
                    "skill_id": skill_id,
                    "name": f"{skill_id}-{mode}-{attempt}",
                    "kind": "behavior",
                    "case_mode": case_mode,
                    "fixture_count": len(case.get("fixtures") or []),
                    "fixture_hashes": [
                        fixture["sha256"] for fixture in case.get("fixtures") or []
                    ],
                    "mode": mode,
                    "attempt": attempt,
                    "workspace": str(workspace),
                    "report": str(report),
                    "args": args,
                }
            )
    workspace = run_root / "triggers" / "batch-1"
    workspace.mkdir(parents=True, exist_ok=True)
    prompt_path = workspace / "provider-prompt.txt"
    prompt_path.write_text(trigger_prompt(pack), encoding="utf-8")
    report = workspace / "provider-report.json"
    jobs.append(
        {
            "skill_id": skill_id,
            "name": f"{skill_id}-triggers",
            "kind": "trigger",
            "workspace": str(workspace),
            "report": str(report),
            "args": [
                *common,
                "--allow-no-tool",
                "--guidance-only",
                "--workspace",
                str(workspace),
                "--prompt-file",
                str(prompt_path),
                "--output",
                str(report),
            ],
        }
    )
    return jobs


def classify_evidence_gate(
    *,
    provider_failures: list[str],
    invalid_attempt_count: int,
    with_passed: int,
    without_passed: int,
    trigger_accuracy: float,
    always_failing: int,
    risk_class: str,
) -> str:
    if provider_failures or invalid_attempt_count or always_failing:
        return "codex_adjudication"
    if risk_class != "low_risk_guidance":
        return "codex_adjudication"
    if with_passed != 3 or with_passed <= without_passed or trigger_accuracy < 1.0:
        return "ready_for_fix_first"
    return "ready_for_scorecard"


def archive_failed_report(report_path: pathlib.Path) -> pathlib.Path:
    """Keep invalid provider evidence before a policy-correction rerun."""
    attempt = 1
    while True:
        archived = report_path.with_name(
            f"{report_path.stem}.invalid-attempt-{attempt}{report_path.suffix}"
        )
        if not archived.exists():
            report_path.replace(archived)
            return archived
        attempt += 1


def normalize_existing_report(report_path: pathlib.Path) -> bool:
    """Apply auditable provider-policy normalizations to preserved raw context."""
    report = load_json(report_path)
    sys.path.insert(0, str(SCRIPT_DIR))
    from run_agentscope_critic_provider import classify_run, final_assistant_text

    changed = False
    clean = final_assistant_text(report.get("context") or [])
    if clean and clean != report.get("final_text"):
        archived = report_path.with_name("provider-report.pre-assistant-only.json")
        if not archived.exists():
            shutil.copy2(report_path, archived)
        report["final_text"] = clean
        report["final_text_extraction"] = "last_assistant_message"
        changed = True
    if (
        report.get("status") in {"tool_permission_denied", "tool_execution_error"}
        and report.get("source_unchanged") is True
        and report.get("workspace_changes") == []
        and report.get("allowed_commands") == []
        and report.get("allowed_outputs") == []
        and str(report.get("final_text") or "").strip()
    ):
        reclassified = classify_run(
            tool_results=report.get("tool_results") or [],
            source_unchanged=True,
            completed=True,
            allow_no_tool=True,
            read_only_probe_failures_are_nonfatal=True,
        )
        if reclassified == "pass":
            archived = report_path.with_name(
                "provider-report.pre-read-only-policy.json"
            )
            if not archived.exists():
                shutil.copy2(report_path, archived)
            report["original_status"] = report.get("status")
            report["status"] = "pass"
            report["read_only_probe_policy_applied"] = True
            changed = True
    if changed:
        atomic_json(report_path, report)
    return changed


def run_job(job: dict[str, Any], *, resume: bool) -> dict[str, Any]:
    report_path = pathlib.Path(job["report"])
    if resume and report_path.is_file():
        normalize_existing_report(report_path)
        report = load_json(report_path)
        if report.get("status") == "pass":
            return {
                "skill_id": job["skill_id"],
                "name": job["name"],
                "kind": job["kind"],
                "exit": 0,
                "status": report.get("status"),
                "seconds": report.get("elapsed_seconds"),
                "resumed": True,
            }
        archive_failed_report(report_path)
    started = time.monotonic()
    process = subprocess.run(
        [sys.executable, *job["args"]],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    report = load_json(report_path) if report_path.is_file() else {}
    return {
        "skill_id": job["skill_id"],
        "name": job["name"],
        "kind": job["kind"],
        "exit": process.returncode,
        "status": report.get("status", "missing_report"),
        "seconds": round(time.monotonic() - started, 3),
        "resumed": False,
        "stderr_tail": process.stderr[-1000:],
    }


def run_job_group(
    jobs: list[dict[str, Any]],
    *,
    concurrency: int,
    resume: bool,
) -> list[dict[str, Any]]:
    results = []
    if not jobs:
        return results
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        future_jobs = {pool.submit(run_job, job, resume=resume): job for job in jobs}
        for future in concurrent.futures.as_completed(future_jobs):
            result = future.result()
            results.append(result)
            print(f"{result['name']}: {result['status']} ({result['seconds']}s)", flush=True)
    return results


def run_first_pair_canary(
    skill_id: str,
    eval_skill: pathlib.Path,
    run_root: pathlib.Path,
) -> dict[str, Any]:
    """Run the unchanged CriticAgent assertion audit on the first paired case."""
    evals_path = eval_skill / "evals" / "evals.json"
    eval_payload = load_json(evals_path)
    cases = eval_payload.get("evals") or []
    if len(cases) != 3:
        raise ValueError("assertion canary requires the validated three-case pack")

    canary_skill = run_root / "assertion-canary-skill"
    (canary_skill / "evals").mkdir(parents=True, exist_ok=True)
    shutil.copy2(eval_skill / "SKILL.md", canary_skill / "SKILL.md")
    canary_payload = dict(eval_payload)
    canary_payload["evals"] = [cases[0]]
    atomic_json(canary_skill / "evals" / "evals.json", canary_payload)

    manifest_path = run_root / "assertion-canary-manifest.json"
    process = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_DIR / "build_agentscope_critic_manifest.py"),
            str(canary_skill),
            str(run_root),
            "--attempt",
            "case-1",
            "--derive-case-contracts",
            "--output",
            str(manifest_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if process.returncode != 0 or not manifest_path.is_file():
        raise RuntimeError(process.stderr[-1200:] or "canary manifest was not produced")

    grader_path = run_root / "assertion-canary-grader.json"
    behavior = run_checked(
        [
            str(REPO_ROOT / "skills" / "skill-criticagent" / "scripts" / "grade_runs.py"),
            str(canary_skill),
            str(manifest_path),
        ],
        grader_path,
    )
    audit = ((behavior.get("summary") or {}).get("assertion_audit") or {})
    always_failing = audit.get("always_failing") or []
    non_discriminating = audit.get("non_discriminating") or []
    evidence = {
        "schema_version": 1,
        "skill_id": skill_id,
        "status": "invalid" if always_failing else "pass",
        "case_id": str(cases[0].get("id") or ""),
        "always_failing_assertions": len(always_failing),
        "non_discriminating_assertions": len(non_discriminating),
        "audit": {
            "always_failing": always_failing,
            "non_discriminating": non_discriminating,
        },
        "remaining_jobs_released": not always_failing,
        "source_hashes": {
            "skill": sha256(eval_skill / "SKILL.md"),
            "evals": sha256(evals_path),
        },
        "hashes": {
            "canary_evals": sha256(canary_skill / "evals" / "evals.json"),
            "manifest": sha256(manifest_path),
            "grader": sha256(grader_path),
        },
    }
    atomic_json(run_root / "assertion-canary.json", evidence)
    return evidence


def run_staged_jobs(
    jobs: list[dict[str, Any]],
    roots: dict[str, tuple[pathlib.Path, pathlib.Path]],
    *,
    concurrency: int,
    resume: bool,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Run one pair first and release the remaining jobs only after its audit."""
    first_pair_jobs = [
        job
        for job in jobs
        if job["kind"] == "behavior" and job.get("attempt") == "case-1"
    ]
    remaining_jobs = [job for job in jobs if job not in first_pair_jobs]
    results = run_job_group(
        first_pair_jobs,
        concurrency=concurrency,
        resume=resume,
    )
    result_by_name = {result["name"]: result for result in results}
    canaries: dict[str, dict[str, Any]] = {}
    released_skill_ids: set[str] = set()

    for skill_id, (eval_skill, run_root) in roots.items():
        skill_first_jobs = [job for job in first_pair_jobs if job["skill_id"] == skill_id]
        first_results = [result_by_name.get(job["name"]) for job in skill_first_jobs]
        if len(first_results) != 2 or any(
            result is None or result.get("status") != "pass" for result in first_results
        ):
            evidence = {
                "schema_version": 1,
                "skill_id": skill_id,
                "status": "not_run",
                "reason": "first_pair_provider_failure",
                "always_failing_assertions": None,
                "remaining_jobs_released": False,
            }
            atomic_json(run_root / "assertion-canary.json", evidence)
        else:
            try:
                evidence = run_first_pair_canary(skill_id, eval_skill, run_root)
            except Exception as exc:
                evidence = {
                    "schema_version": 1,
                    "skill_id": skill_id,
                    "status": "error",
                    "reason": str(exc),
                    "always_failing_assertions": None,
                    "remaining_jobs_released": False,
                }
                atomic_json(run_root / "assertion-canary.json", evidence)
        canaries[skill_id] = evidence
        if evidence["status"] == "pass":
            released_skill_ids.add(skill_id)

    released_jobs = [
        job for job in remaining_jobs if job["skill_id"] in released_skill_ids
    ]
    if released_jobs:
        results.extend(
            run_job_group(released_jobs, concurrency=concurrency, resume=resume)
        )
    for job in remaining_jobs:
        if job["skill_id"] in released_skill_ids:
            continue
        canary_status = canaries[job["skill_id"]]["status"]
        results.append(
            {
                "skill_id": job["skill_id"],
                "name": job["name"],
                "kind": job["kind"],
                "exit": None,
                "status": f"skipped_canary_{canary_status}",
                "seconds": 0.0,
                "resumed": False,
            }
        )
    results.sort(key=lambda item: item["name"])
    return results, canaries


def run_checked(args: list[str], output: pathlib.Path) -> dict[str, Any]:
    process = subprocess.run(
        [sys.executable, *args, "--output", str(output)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if process.returncode not in {0, 1} or not output.is_file():
        raise RuntimeError(process.stderr[-1200:] or "grader did not produce output")
    return load_json(output)


def grade_skill(
    skill_id: str,
    eval_skill: pathlib.Path,
    run_root: pathlib.Path,
    execution_model: str,
) -> dict[str, Any]:
    attempts = ["case-1", "case-2", "case-3"]
    manifest_path = run_root / "runs-manifest.json"
    build_args = [
        str(SCRIPT_DIR / "build_agentscope_critic_manifest.py"),
        str(eval_skill),
        str(run_root),
        *sum((["--attempt", attempt] for attempt in attempts), []),
        "--derive-case-contracts",
        "--output",
        str(manifest_path),
    ]
    process = subprocess.run(
        [sys.executable, *build_args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if process.returncode != 0:
        raise RuntimeError(process.stderr[-1200:] or process.stdout[-1200:])
    behavior_path = run_root / "behavior-grader.json"
    behavior = run_checked(
        [
            str(REPO_ROOT / "skills" / "skill-criticagent" / "scripts" / "grade_runs.py"),
            str(eval_skill),
            str(manifest_path),
        ],
        behavior_path,
    )
    trigger_report = load_json(run_root / "triggers" / "batch-1" / "provider-report.json")
    trigger_payload = load_json(eval_skill / "evals" / "trigger_queries.json")
    sys.path.insert(0, str(SCRIPT_DIR))
    from build_agentscope_trigger_decisions import build_decisions

    pack = validate_eval_pack(eval_skill)
    skill_name = pack["skill_name"]
    decisions = build_decisions(trigger_report, trigger_payload, skill_name)
    decisions_path = run_root / "trigger-decisions.json"
    atomic_json(decisions_path, decisions)
    trigger_path = run_root / "trigger-grader.json"
    trigger = run_checked(
        [
            str(REPO_ROOT / "skills" / "skill-criticagent" / "scripts" / "grade_triggers.py"),
            str(eval_skill),
            str(decisions_path),
        ],
        trigger_path,
    )
    always_failing = len(
        ((behavior.get("summary") or {}).get("assertion_audit") or {}).get("always_failing") or []
    )
    provider_failures = []
    for report in run_root.rglob("provider-report.json"):
        status = load_json(report).get("status")
        if status != "pass":
            provider_failures.append(f"{report.relative_to(run_root).as_posix()}:{status}")
    invalid_attempt_count = len(list(run_root.rglob("provider-report.invalid-attempt-*.json")))
    with_passed = int(((behavior.get("summary") or {}).get("with_skill") or {}).get("passed", 0))
    without_passed = int(((behavior.get("summary") or {}).get("without_skill") or {}).get("passed", 0))
    trigger_accuracy = float(((trigger.get("summary") or {}).get("accuracy", 0.0)))
    gate = classify_evidence_gate(
        provider_failures=provider_failures,
        invalid_attempt_count=invalid_attempt_count,
        with_passed=with_passed,
        without_passed=without_passed,
        trigger_accuracy=trigger_accuracy,
        always_failing=always_failing,
        risk_class=(
            "low_risk_guidance"
            if set(pack["case_modes"]) == {"guidance"}
            else "standard_mixed"
        ),
    )
    evidence = {
        "schema_version": 1,
        "skill_id": skill_id,
        "execution_model": execution_model,
        "provider_failures": provider_failures,
        "invalid_attempt_count": invalid_attempt_count,
        "behavior": {"with_passed": with_passed, "without_passed": without_passed},
        "case_modes": pack["case_modes"],
        "trigger_accuracy": trigger_accuracy,
        "always_failing_assertions": always_failing,
        "gate": gate,
        "scorecard_write_performed": False,
        "hashes": {
            "manifest": sha256(manifest_path),
            "behavior_grader": sha256(behavior_path),
            "trigger_decisions": sha256(decisions_path),
            "trigger_grader": sha256(trigger_path),
        },
    }
    atomic_json(run_root / "evidence-gate.json", evidence)
    return evidence


def resolve_run_layout(
    skill_ids: list[str],
    *,
    run_label: str,
    eval_skill: pathlib.Path | None,
    run_root: pathlib.Path | None,
) -> tuple[
    dict[str, tuple[pathlib.Path, pathlib.Path]], pathlib.Path
]:
    """Resolve either catalog-backed runs or one external Worker run."""
    if (eval_skill is None) != (run_root is None):
        raise ValueError("--eval-skill and --run-root must be provided together")
    if eval_skill is not None and run_root is not None:
        if len(skill_ids) != 1:
            raise ValueError("external run layout requires exactly one --id")
        resolved_root = run_root.resolve()
        return {
            skill_ids[0]: (eval_skill.resolve(), resolved_root)
        }, resolved_root
    return {
        skill_id: (
            DEFAULT_RUNS / skill_id / run_label / "eval_skill",
            DEFAULT_RUNS / skill_id / run_label,
        )
        for skill_id in skill_ids
    }, DEFAULT_RUNS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", action="append", required=True, dest="ids")
    parser.add_argument("--run-label", default="quick-v1")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url")
    parser.add_argument("--protocol", choices=("openai", "anthropic"), default="openai")
    parser.add_argument("--auth-mode", choices=("api-key", "auth-token"), default="api-key")
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--agentscope-src", type=pathlib.Path, default=DEFAULT_AGENTSCOPE_SRC)
    parser.add_argument("--runner", type=pathlib.Path, default=DEFAULT_RUNNER)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--max-output-tokens", type=int)
    parser.add_argument("--disable-thinking", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--eval-skill", type=pathlib.Path)
    parser.add_argument("--run-root", type=pathlib.Path)
    args = parser.parse_args(argv)
    jobs = []
    try:
        roots, artifact_root = resolve_run_layout(
            args.ids,
            run_label=args.run_label,
            eval_skill=args.eval_skill,
            run_root=args.run_root,
        )
    except ValueError as exc:
        parser.error(str(exc))
    external_layout = args.eval_skill is not None
    artifact_root.mkdir(parents=True, exist_ok=True)
    for skill_id, (eval_skill, root) in roots.items():
        validate_eval_pack(eval_skill)
        jobs.extend(
            build_jobs(
                skill_id=skill_id,
                eval_skill=eval_skill,
                run_root=root,
                model=args.model,
                agentscope_src=args.agentscope_src,
                runner=args.runner,
                base_url=args.base_url,
                api_key_env=args.api_key_env,
                protocol=args.protocol,
                auth_mode=args.auth_mode,
                max_output_tokens=args.max_output_tokens,
                disable_thinking=args.disable_thinking,
            )
        )
    jobs_path = (
        artifact_root / "jobs.json"
        if external_layout
        else artifact_root / f"{args.run_label}-jobs.json"
    )
    atomic_json(jobs_path, jobs)
    if not args.execute:
        print(f"Prepared {len(jobs)} jobs for {len(roots)} skills")
        return 0
    results, canaries = run_staged_jobs(
        jobs,
        roots,
        concurrency=args.concurrency,
        resume=args.resume,
    )
    run_summary_path = (
        artifact_root / "run-summary.json"
        if external_layout
        else artifact_root / f"{args.run_label}-run-summary.json"
    )
    atomic_json(run_summary_path, results)
    gates = []
    for skill_id, (eval_skill, root) in roots.items():
        skill_results = [
            result
            for result in results
            if result.get("skill_id") == skill_id
        ]
        canary = canaries[skill_id]
        if canary["status"] != "pass":
            evidence = {
                "schema_version": 1,
                "skill_id": skill_id,
                "gate": "codex_adjudication",
                "evaluation_status": (
                    "eval_invalid"
                    if canary["status"] == "invalid"
                    else "provider_or_canary_blocked"
                ),
                "provider_failures": [
                    f"{result['name']}:{result['status']}"
                    for result in skill_results
                    if result["status"] not in {"pass"}
                    and not result["status"].startswith("skipped_canary_")
                ],
                "assertion_canary": canary,
                "always_failing_assertions": canary.get(
                    "always_failing_assertions"
                ),
                "remaining_jobs_executed": 0,
                "scorecard_write_performed": False,
            }
            atomic_json(root / "evidence-gate.json", evidence)
            gates.append(evidence)
        elif all(result["status"] == "pass" for result in skill_results):
            gates.append(grade_skill(skill_id, eval_skill, root, args.model))
        else:
            evidence = {
                "schema_version": 1,
                "skill_id": skill_id,
                "gate": "codex_adjudication",
                "provider_failures": [
                    f"{result['name']}:{result['status']}"
                    for result in skill_results
                    if result["status"] != "pass"
                ],
                "scorecard_write_performed": False,
            }
            atomic_json(root / "evidence-gate.json", evidence)
            gates.append(evidence)
    evidence_summary_path = (
        artifact_root / "evidence-summary.json"
        if external_layout
        else artifact_root / f"{args.run_label}-evidence-summary.json"
    )
    atomic_json(evidence_summary_path, gates)
    return 0 if all(gate["gate"] == "ready_for_scorecard" for gate in gates) else 2


if __name__ == "__main__":
    raise SystemExit(main())
