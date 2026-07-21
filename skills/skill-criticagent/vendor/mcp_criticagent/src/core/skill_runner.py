"""Deterministic paired behavior grader for recorded Skill executions."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

from .skill_file_asserts import OutputFile
from .skill_tool_asserts import ToolCall, nested_argument


@dataclass
class ProviderResult:
    output: str
    output_files: list[OutputFile] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)


class CompletionProvider(Protocol):
    def complete(self, prompt: str) -> ProviderResult: ...


@dataclass
class SkillEvalResult:
    runs: list[dict[str, Any]]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"runs": self.runs, "summary": self.summary}


def _load_evals(skill_dir: str | Path) -> list[dict[str, Any]]:
    path = Path(skill_dir) / "evals" / "evals.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("evals") if isinstance(payload, dict) else None
    if not isinstance(cases, list) or not cases:
        raise ValueError("evals/evals.json must contain a non-empty evals array")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"evals[{index}] must be an object")
        case_id = str(case.get("id") or f"case-{index + 1}").strip()
        prompt = str(case.get("prompt") or "").strip()
        if not case_id or case_id in seen or not prompt:
            raise ValueError(f"evals[{index}] needs a unique id and non-empty prompt")
        seen.add(case_id)
        normalized.append({**case, "id": case_id, "prompt": prompt})
    return normalized


def _normalize_assertion(raw: object) -> dict[str, Any]:
    if isinstance(raw, str):
        value = raw.strip()
        lowered = value.casefold()
        if lowered.startswith("contains:"):
            return {"type": "contains", "value": value.split(":", 1)[1].strip()}
        if lowered.startswith("not-contains:"):
            return {"type": "not-contains", "value": value.split(":", 1)[1].strip()}
        return {"type": "contains", "value": value}
    if not isinstance(raw, dict):
        raise ValueError("assertion must be a string or object")
    return dict(raw)


def _text_assertion(assertion: dict[str, Any], output: str) -> tuple[bool, str]:
    kind = str(assertion.get("type") or "contains").strip().lower()
    expected = str(assertion.get("value") or "")
    if kind == "contains":
        passed = bool(expected) and expected.casefold() in output.casefold()
    elif kind == "not-contains":
        passed = expected.casefold() not in output.casefold()
    elif kind == "equals":
        passed = output.strip() == expected
    elif kind == "regex":
        try:
            passed = re.search(expected, output, flags=re.MULTILINE) is not None
        except re.error:
            passed = False
    else:
        return False, f"unsupported text assertion type: {kind}"
    return passed, f"{kind}: {expected}"


def _safe_relative_path(raw: object) -> str | None:
    value = str(raw or "").replace("\\", "/").strip("/")
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts:
        return None
    return path.as_posix()


def _file_assertion(assertion: dict[str, Any], files: list[OutputFile]) -> tuple[bool, str]:
    kind = str(assertion.get("type") or "").strip().lower()
    relative = _safe_relative_path(assertion.get("path"))
    if relative is None:
        return False, f"{kind}: invalid path"
    by_path = {item.path: item for item in files}
    item = by_path.get(relative)
    if kind == "file-exists":
        passed = item is not None
    elif kind == "file-not-exists":
        passed = item is None
    elif kind == "file-contains":
        expected = str(assertion.get("value") or "")
        passed = item is not None and expected.casefold() in item.content.casefold()
    elif kind == "file-not-contains":
        expected = str(assertion.get("value") or "")
        passed = item is None or expected.casefold() not in item.content.casefold()
    elif kind == "file-regex":
        try:
            passed = item is not None and re.search(
                str(assertion.get("value") or ""), item.content, flags=re.MULTILINE
            ) is not None
        except re.error:
            passed = False
    else:
        return False, f"unsupported file assertion type: {kind}"
    return passed, f"{kind}: {relative}"


def _tool_assertion(assertion: dict[str, Any], calls: list[ToolCall]) -> tuple[bool, str]:
    kind = str(assertion.get("type") or "").strip().lower()
    name = str(assertion.get("name") or "").strip()
    matching = [call for call in calls if call.name == name]
    if kind == "tool-called":
        passed = bool(matching)
    elif kind == "tool-not-called":
        passed = not matching
    elif kind in {"tool-arg-equals", "tool-arg-contains"}:
        argument_path = str(assertion.get("path") or "").strip()
        expected = assertion.get("value")
        passed = False
        for call in matching:
            found, actual = nested_argument(call.arguments, argument_path)
            if not found:
                continue
            if kind == "tool-arg-equals" and actual == expected:
                passed = True
            elif kind == "tool-arg-contains" and str(expected).casefold() in str(actual).casefold():
                passed = True
    else:
        return False, f"unsupported tool assertion type: {kind}"
    return passed, f"{kind}: {name}"


def _run_case(case: dict[str, Any], mode: str, provider: CompletionProvider, skill_text: str) -> dict[str, Any]:
    prompt = case["prompt"]
    if mode == "with_skill":
        request = f"<skill>\n{skill_text}\n</skill>\n\nUser request:\n{prompt}"
    else:
        request = f"User request:\n{prompt}"
    response = provider.complete(request)
    if not isinstance(response, ProviderResult):
        raise TypeError("provider.complete() must return ProviderResult")

    checks: list[dict[str, Any]] = []
    raw_text_assertions = case.get("assertions")
    if raw_text_assertions is None:
        raw_text_assertions = case.get("expectations", [])
    if not isinstance(raw_text_assertions, list):
        raise ValueError(f"eval {case['id']} assertions must be a list")
    for raw in raw_text_assertions:
        assertion = _normalize_assertion(raw)
        passed, label = _text_assertion(assertion, response.output)
        checks.append({"channel": "text", "assertion": label, "passed": passed})

    for raw in case.get("file_assertions") or []:
        assertion = _normalize_assertion(raw)
        passed, label = _file_assertion(assertion, response.output_files)
        checks.append({"channel": "file", "assertion": label, "passed": passed})

    for raw in case.get("tool_assertions") or []:
        assertion = _normalize_assertion(raw)
        passed, label = _tool_assertion(assertion, response.tool_calls)
        checks.append({"channel": "tool", "assertion": label, "passed": passed})

    return {
        "case_id": case["id"],
        "mode": mode,
        "passed": bool(checks) and all(check["passed"] for check in checks),
        "checks": checks,
        "output": response.output,
        "output_files": [item.to_dict() for item in response.output_files],
        "tool_calls": [item.to_dict() for item in response.tool_calls],
    }


def run_skill_evals(
    skill_dir: str | Path,
    *,
    target_provider: CompletionProvider,
    baseline: bool = True,
) -> SkillEvalResult:
    root = Path(skill_dir)
    skill_text = (root / "SKILL.md").read_text(encoding="utf-8")
    cases = _load_evals(root)
    modes = ("with_skill", "without_skill") if baseline else ("with_skill",)
    runs = [_run_case(case, mode, target_provider, skill_text) for case in cases for mode in modes]

    summary: dict[str, Any] = {}
    for mode in modes:
        selected = [run for run in runs if run["mode"] == mode]
        summary[mode] = {
            "passed": sum(bool(run["passed"]) for run in selected),
            "total": len(selected),
            "pass_rate": sum(bool(run["passed"]) for run in selected) / len(selected),
        }
    if not baseline:
        summary["without_skill"] = {"passed": 0, "total": 0, "pass_rate": 0.0}
    summary["skill_uplift"] = {
        "pass_rate_delta": round(
            summary["with_skill"]["pass_rate"] - summary["without_skill"]["pass_rate"], 6
        )
    }

    non_discriminating: list[dict[str, str]] = []
    always_failing: list[dict[str, str]] = []
    if baseline:
        by_key: dict[tuple[str, str], dict[str, bool]] = {}
        for run in runs:
            for check in run["checks"]:
                key = (run["case_id"], f"{check['channel']}::{check['assertion']}")
                by_key.setdefault(key, {})[run["mode"]] = bool(check["passed"])
        for (case_id, assertion), outcomes in by_key.items():
            entry = {"case_id": case_id, "assertion": assertion}
            if outcomes.get("with_skill") and outcomes.get("without_skill"):
                non_discriminating.append(entry)
            elif not outcomes.get("with_skill") and not outcomes.get("without_skill"):
                always_failing.append(entry)
    summary["assertion_audit"] = {
        "non_discriminating": non_discriminating,
        "always_failing": always_failing,
    }
    return SkillEvalResult(runs=runs, summary=summary)
