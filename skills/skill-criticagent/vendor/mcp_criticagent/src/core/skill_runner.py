#!/usr/bin/env python3
"""Behavior runner for Agent Skill eval cases.

Prompt rendering, file attachment handling, and grading semantics follow
darkrishabh/agent-skills-eval (`src/run-eval.ts`, `src/fs-utils.ts`):
- skill system message includes SKILL.md body, references/ docs, and a
  scripts/ manifest (shebang first line only);
- attached eval files carry a kind (text/missing/binary-skipped/too-large)
  and are truncated at 64KB instead of failing the run;
- free-form assertions go to an LLM judge when one is configured, while
  typed assertions stay deterministic and local.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, List, Protocol

from src.core.skill_file_asserts import (
    FileAssertion,
    OutputFile,
    grade_file_assertions,
    parse_file_assertions,
)
from src.core.skill_judge import RubricGradeResult, grade_with_judge
from src.core.skill_tool_asserts import (
    ToolAssertion,
    ToolCall,
    grade_tool_assertions,
    parse_tool_assertions,
)

DETERMINISTIC_ASSERTION_TYPES = {"contains", "not_contains", "equals", "regex"}
ASSERTION_PREFIXES = {
    "contains": "contains",
    "not-contains": "not_contains",
    "not_contains": "not_contains",
    "equals": "equals",
    "regex": "regex",
}
MAX_ATTACHED_FILE_BYTES = 64 * 1024
REFERENCE_EXTENSIONS = {".md", ".mdx"}


@dataclass
class ProviderResult:
    output: str
    provider: str = "local"
    model: str = "static"
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: List[ToolCall] = field(default_factory=list)
    output_files: List[OutputFile] = field(default_factory=list)


class SkillEvalProvider(Protocol):
    def complete(self, prompt: str) -> str | ProviderResult:
        """Return a completion for a fully rendered eval prompt."""


class StaticOutputProvider:
    """Deterministic provider: outputs (and optional output files) are
    supplied up front, e.g. by the host agent after running the cases."""

    def __init__(
        self,
        with_skill_output: str,
        without_skill_output: str | None = None,
        with_skill_files: List[OutputFile] | None = None,
        without_skill_files: List[OutputFile] | None = None,
    ):
        self.with_skill_output = with_skill_output
        self.without_skill_output = without_skill_output or with_skill_output
        self.with_skill_files = with_skill_files or []
        self.without_skill_files = without_skill_files or []

    def complete(self, prompt: str) -> ProviderResult:
        with_skill = "<skill" in prompt
        return ProviderResult(
            output=self.with_skill_output if with_skill else self.without_skill_output,
            output_files=(
                self.with_skill_files if with_skill else self.without_skill_files
            ),
        )


class LlmJudge:
    """LLM judge for free-form rubric assertions; fails closed on bad JSON."""

    def __init__(self, provider: SkillEvalProvider):
        self.provider = provider
        self.model = getattr(provider, "model", None)

    def grade(self, assertions: List[str], output: str) -> List[RubricGradeResult]:
        results, _prompt, _response = grade_with_judge(
            self.provider, assertions, output
        )
        return results


@dataclass
class AttachedFile:
    """Eval file attachment; kinds follow agent-skills-eval fs-utils."""

    path: str
    content: str
    kind: str  # text | missing | binary-skipped | too-large
    bytes: int | None = None


@dataclass
class SkillAssertion:
    type: str  # deterministic types or "rubric" (LLM-judged free text)
    value: str


@dataclass
class SkillEvalCase:
    id: str
    prompt: str
    name: str | None = None
    expected_output: str | None = None
    assertions: List[SkillAssertion] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    tools: List[dict] = field(default_factory=list)
    tool_assertions: List[ToolAssertion] = field(default_factory=list)
    file_assertions: List[FileAssertion] = field(default_factory=list)


@dataclass
class AssertionResult:
    type: str
    value: str
    passed: bool
    evidence: str


@dataclass
class SkillEvalRun:
    case_id: str
    mode: str
    prompt: str
    output: str
    passed: bool
    assertions: List[AssertionResult]
    provider: str = "local"
    model: str = "static"
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    iteration: int = 1

    @property
    def assertion_pass_rate(self) -> float:
        if not self.assertions:
            return 1.0
        return sum(1 for result in self.assertions if result.passed) / len(
            self.assertions
        )


@dataclass
class SkillEvalRunResult:
    skill_path: str
    total_cases: int
    runs: List[SkillEvalRun]
    summary: dict

    def to_dict(self) -> dict:
        return asdict(self)


def run_skill_evals(
    skill_dir: str | Path,
    target_provider: SkillEvalProvider,
    baseline: bool = True,
    judge: LlmJudge | None = None,
    iterations: int = 1,
) -> SkillEvalRunResult:
    """Run evals/evals.json for a skill using an injectable target provider.

    When a judge is set, free-form assertions and expected_output are graded
    by the LLM judge; otherwise they fall back to substring checks. With
    iterations > 1 every case/mode pair runs multiple times and the summary
    gains a benchmark block with mean/stddev statistics.
    """

    if iterations < 1:
        raise ValueError("iterations must be >= 1")

    root = Path(skill_dir)
    skill = _load_skill(root)
    eval_cases = _load_eval_cases(root)
    modes = ["with_skill", "without_skill"] if baseline else ["with_skill"]
    runs: List[SkillEvalRun] = []

    for case in eval_cases:
        attached = [_read_attached_file(root, rel) for rel in case.files]
        user_message = _inline_files(case.prompt, attached)
        for mode in modes:
            system = _render_skill_system(skill) if mode == "with_skill" else None
            for iteration in range(1, iterations + 1):
                provider_result, prompt = _complete_with_fallback(
                    target_provider, system, user_message, tools=case.tools
                )
                assertions = _grade_output(
                    provider_result.output,
                    expected_output=case.expected_output,
                    assertions=case.assertions,
                    judge=judge,
                )
                if case.tool_assertions:
                    assertions.extend(
                        AssertionResult(
                            type="tool",
                            value=grade.text,
                            passed=grade.passed,
                            evidence=grade.evidence,
                        )
                        for grade in grade_tool_assertions(
                            provider_result.tool_calls, case.tool_assertions
                        )
                    )
                if case.file_assertions:
                    assertions.extend(
                        AssertionResult(
                            type="file",
                            value=grade.text,
                            passed=grade.passed,
                            evidence=grade.evidence,
                        )
                        for grade in grade_file_assertions(
                            provider_result.output_files, case.file_assertions
                        )
                    )
                runs.append(
                    SkillEvalRun(
                        case_id=case.id,
                        mode=mode,
                        prompt=prompt,
                        output=provider_result.output,
                        passed=all(result.passed for result in assertions),
                        assertions=assertions,
                        provider=provider_result.provider,
                        model=provider_result.model,
                        latency_ms=provider_result.latency_ms,
                        input_tokens=provider_result.input_tokens,
                        output_tokens=provider_result.output_tokens,
                        iteration=iteration,
                    )
                )

    return SkillEvalRunResult(
        skill_path=str(root),
        total_cases=len(eval_cases),
        runs=runs,
        summary=_summarize_runs(runs, judge=judge, iterations=iterations),
    )


def _load_skill(skill_dir: Path) -> dict:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"Missing required file: {skill_md}")

    content = skill_md.read_text(encoding="utf-8")
    metadata, body = _split_frontmatter(content)
    return {
        "name": metadata.get("name") or skill_dir.name,
        "description": metadata.get("description") or "",
        "body": body.strip(),
        "references": _read_references(skill_dir),
        "scripts": _read_scripts_manifest(skill_dir),
    }


def _read_references(skill_dir: Path) -> List[AttachedFile]:
    references_dir = skill_dir / "references"
    if not references_dir.is_dir():
        return []
    paths = sorted(
        (
            path
            for path in references_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in REFERENCE_EXTENSIONS
        ),
        key=lambda path: path.relative_to(skill_dir).as_posix(),
    )
    return [
        _read_attached_file(skill_dir, path.relative_to(skill_dir).as_posix())
        for path in paths
    ]


def _read_scripts_manifest(skill_dir: Path) -> List[AttachedFile]:
    """Scripts are listed with their shebang line only, not full bodies."""

    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return []
    manifest = []
    for path in sorted(scripts_dir.iterdir(), key=lambda p: p.name):
        if not path.is_file():
            continue
        try:
            first_line = path.read_text(encoding="utf-8").splitlines()[0]
        except (UnicodeDecodeError, IndexError):
            first_line = ""
        manifest.append(
            AttachedFile(
                path=f"scripts/{path.name}",
                content=first_line if first_line.startswith("#!") else "",
                kind="text",
                bytes=path.stat().st_size,
            )
        )
    return manifest


def _read_attached_file(
    root: Path, relative_path: str, max_bytes: int = MAX_ATTACHED_FILE_BYTES
) -> AttachedFile:
    """Read an eval file; degrade to kind markers instead of failing the run."""

    skill_root = root.resolve()
    resolved = (skill_root / relative_path).resolve()
    if skill_root not in resolved.parents and resolved != skill_root:
        raise ValueError(f"Eval file escapes skill directory: {relative_path}")

    normalized = relative_path.replace("\\", "/")
    if not resolved.is_file():
        return AttachedFile(path=normalized, content="", kind="missing")

    raw = resolved.read_bytes()
    if 0 in raw[:4096]:
        return AttachedFile(
            path=normalized, content="", kind="binary-skipped", bytes=len(raw)
        )
    if len(raw) > max_bytes:
        return AttachedFile(
            path=normalized,
            content=raw[:max_bytes].decode("utf-8", errors="replace"),
            kind="too-large",
            bytes=len(raw),
        )
    return AttachedFile(
        path=normalized,
        content=raw.decode("utf-8", errors="replace"),
        kind="text",
        bytes=len(raw),
    )


def _escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _attached_file_xml(tag: str, file: AttachedFile) -> str:
    attrs = f'path="{_escape_xml(file.path)}" kind="{file.kind}"'
    if file.bytes is not None:
        attrs += f' bytes="{file.bytes}"'
    if file.kind in ("text", "too-large"):
        return f"<{tag} {attrs}>\n{file.content}\n</{tag}>"
    return f"<{tag} {attrs}>{file.kind}</{tag}>"


def _render_skill_system(skill: dict) -> str:
    parts = [
        f"<skill name=\"{skill['name']}\">",
        f"<description>{skill['description']}</description>",
        "<instructions>",
        skill["body"],
        "</instructions>",
    ]
    if skill["references"]:
        parts.append("<references>")
        parts.extend(
            _attached_file_xml("reference", ref) for ref in skill["references"]
        )
        parts.append("</references>")
    if skill["scripts"]:
        parts.append("<scripts>")
        parts.extend(
            _attached_file_xml("script", script) for script in skill["scripts"]
        )
        parts.append("</scripts>")
    parts.append("</skill>")
    return "\n".join(parts)


def _inline_files(user_prompt: str, files: List[AttachedFile]) -> str:
    if not files:
        return user_prompt
    blocks = [_attached_file_xml("file", file) for file in files]
    return "\n\n".join([*blocks, "---USER PROMPT---", user_prompt])


def _complete_with_fallback(
    provider: SkillEvalProvider,
    system: str | None,
    user: str,
    tools: List[dict] | None = None,
) -> tuple[ProviderResult, str]:
    """Use system/user chat when supported; otherwise merge into one prompt.

    Tools are forwarded only to providers with chat support; plain providers
    cannot express tool definitions, matching agent-skills-eval semantics.
    """

    complete_chat = getattr(provider, "complete_chat", None)
    if complete_chat and getattr(provider, "supports_system_role", False):
        result = _normalize_provider_result(
            complete_chat(system=system, user=user, tools=tools or None)
        )
        merged = _merge_prompt(system, user)
        return result, merged

    merged = _merge_prompt(system, user)
    return _normalize_provider_result(provider.complete(merged)), merged


def _merge_prompt(system: str | None, user: str) -> str:
    if not system:
        return f"---USER REQUEST---\n{user}"
    return f"{system}\n\n---USER REQUEST---\n{user}"


def _load_eval_cases(skill_dir: Path) -> List[SkillEvalCase]:
    evals_path = skill_dir / "evals" / "evals.json"
    if not evals_path.exists():
        raise FileNotFoundError(f"Missing evals file: {evals_path}")

    raw = json.loads(evals_path.read_text(encoding="utf-8"))
    records = raw.get("evals") if isinstance(raw, dict) else None
    if not isinstance(records, list):
        raise ValueError("evals/evals.json must contain an 'evals' array")

    cases = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"evals[{index - 1}] must be an object")
        prompt = record.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"evals[{index - 1}].prompt must be a non-empty string")

        # openai/plugins skills use "expectations" for the same concept.
        raw_assertions = record.get("assertions")
        if raw_assertions is None:
            raw_assertions = record.get("expectations")

        cases.append(
            SkillEvalCase(
                id=str(record.get("id") or index),
                name=(
                    record.get("name") if isinstance(record.get("name"), str) else None
                ),
                prompt=prompt,
                expected_output=(
                    record.get("expected_output")
                    if isinstance(record.get("expected_output"), str)
                    else None
                ),
                assertions=_normalize_assertions(raw_assertions, index - 1),
                files=_normalize_files(record.get("files"), index - 1),
                tools=_normalize_tools(record.get("tools"), index - 1),
                tool_assertions=parse_tool_assertions(
                    record.get("tool_assertions"), f"evals[{index - 1}]"
                ),
                file_assertions=parse_file_assertions(
                    record.get("file_assertions"), f"evals[{index - 1}]"
                ),
            )
        )

    return cases


def _normalize_tools(value: Any, eval_index: int) -> List[dict]:
    """Validate OpenAI-style tool definitions (passed through, not executed)."""

    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"evals[{eval_index}].tools must be an array")
    for tool_index, entry in enumerate(value):
        if (
            not isinstance(entry, dict)
            or entry.get("type") != "function"
            or not isinstance(entry.get("function"), dict)
            or not isinstance(entry["function"].get("name"), str)
        ):
            raise ValueError(
                f"evals[{eval_index}].tools[{tool_index}] must be "
                '{"type": "function", "function": {"name": ...}}'
            )
    return value


def _split_frontmatter(content: str) -> tuple[dict, str]:
    if not content.startswith("---"):
        return {}, content

    lines = content.splitlines()
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return _parse_frontmatter(lines[1:index]), "\n".join(lines[index + 1 :])

    return {}, content


def _parse_frontmatter(lines: List[str]) -> dict:
    metadata = {}
    for raw_line in lines:
        if ":" not in raw_line or raw_line.startswith((" ", "\t")):
            continue
        key, value = raw_line.split(":", 1)
        metadata[key.strip()] = value.strip().strip("'\"")
    return metadata


def _normalize_assertions(value: Any, eval_index: int) -> List[SkillAssertion]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"evals[{eval_index}].assertions must be an array")

    assertions = []
    for assertion_index, entry in enumerate(value):
        if isinstance(entry, str):
            assertions.append(_parse_assertion_string(entry))
            continue
        if isinstance(entry, dict):
            assertions.append(
                _parse_assertion_object(entry, eval_index, assertion_index)
            )
            continue
        raise ValueError(
            f"evals[{eval_index}].assertions[{assertion_index}] is invalid"
        )

    return assertions


def _parse_assertion_string(text: str) -> SkillAssertion:
    """Plain strings become rubric assertions (LLM-judged when a judge exists).

    Recognized `type:` prefixes stay deterministic for backwards compatibility.
    """

    if ":" in text:
        prefix, remainder = text.split(":", 1)
        assertion_type = ASSERTION_PREFIXES.get(prefix.strip().lower())
        if assertion_type:
            return SkillAssertion(type=assertion_type, value=remainder.strip())
    return SkillAssertion(type="rubric", value=text)


def _parse_assertion_object(
    entry: dict, eval_index: int, assertion_index: int
) -> SkillAssertion:
    explicit_type = entry.get("type")
    if isinstance(explicit_type, str):
        normalized = explicit_type.strip().lower()
        assertion_type = ASSERTION_PREFIXES.get(normalized) or (
            "rubric" if normalized == "rubric" else None
        )
        if assertion_type is None:
            raise ValueError(
                f"evals[{eval_index}].assertions[{assertion_index}].type must be one of "
                f"{sorted(DETERMINISTIC_ASSERTION_TYPES | {'rubric'})}"
            )
        value = entry.get("value")
        if not isinstance(value, str):
            raise ValueError(
                f"evals[{eval_index}].assertions[{assertion_index}].value must be a string"
            )
        return SkillAssertion(type=assertion_type, value=value)

    for key in ("text", "value", "criterion"):
        if isinstance(entry.get(key), str):
            return _parse_assertion_string(entry[key])

    raise ValueError(
        f"evals[{eval_index}].assertions[{assertion_index}] must contain type/value, "
        "text, value, or criterion"
    )


def _normalize_files(value: Any, eval_index: int) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(
        isinstance(entry, str) and entry.strip() for entry in value
    ):
        raise ValueError(
            f"evals[{eval_index}].files must be an array of non-empty strings"
        )
    return [entry.strip() for entry in value]


def _normalize_provider_result(result: str | ProviderResult) -> ProviderResult:
    if isinstance(result, ProviderResult):
        return result
    return ProviderResult(output=str(result))


def _grade_output(
    output: str,
    expected_output: str | None,
    assertions: List[SkillAssertion],
    judge: LlmJudge | None = None,
) -> List[AssertionResult]:
    checks = assertions[:]
    if expected_output and not checks:
        if judge:
            checks.append(
                SkillAssertion(
                    type="rubric",
                    value=(
                        "The output satisfies this expected output: "
                        f"{expected_output}"
                    ),
                )
            )
        else:
            checks.append(SkillAssertion(type="contains", value=expected_output))

    deterministic = [check for check in checks if check.type != "rubric"]
    rubric = [check for check in checks if check.type == "rubric"]

    results = [_grade_deterministic(output, assertion) for assertion in deterministic]

    if rubric and judge:
        graded = judge.grade([assertion.value for assertion in rubric], output)
        results.extend(
            AssertionResult(
                type="rubric",
                value=grade.text,
                passed=grade.passed,
                evidence=grade.evidence,
            )
            for grade in graded
        )
    elif rubric:
        # No judge configured: degrade rubric text to a substring check.
        results.extend(
            _grade_deterministic(
                output, SkillAssertion(type="contains", value=assertion.value)
            )
            for assertion in rubric
        )

    return results


def _grade_deterministic(output: str, assertion: SkillAssertion) -> AssertionResult:
    if assertion.type == "contains":
        passed = assertion.value.lower() in output.lower()
        evidence = (
            f"Output contains {assertion.value!r}"
            if passed
            else f"Output does not contain {assertion.value!r}"
        )
    elif assertion.type == "not_contains":
        passed = assertion.value.lower() not in output.lower()
        evidence = (
            f"Output correctly omits {assertion.value!r}"
            if passed
            else f"Output unexpectedly contains {assertion.value!r}"
        )
    elif assertion.type == "equals":
        passed = output.strip() == assertion.value.strip()
        evidence = (
            f"Output equals {assertion.value!r}"
            if passed
            else f"Output does not equal {assertion.value!r}"
        )
    elif assertion.type == "regex":
        try:
            matched = re.search(assertion.value, output)
        except re.error as exc:
            return AssertionResult(
                type=assertion.type,
                value=assertion.value,
                passed=False,
                evidence=f"Invalid regex {assertion.value!r}: {exc}",
            )
        passed = matched is not None
        evidence = (
            f"Output matches regex {assertion.value!r}"
            if passed
            else f"Output does not match regex {assertion.value!r}"
        )
    else:
        return AssertionResult(
            type=assertion.type,
            value=assertion.value,
            passed=False,
            evidence=f"Unsupported assertion type: {assertion.type}",
        )

    return AssertionResult(
        type=assertion.type,
        value=assertion.value,
        passed=passed,
        evidence=evidence,
    )


def _summarize_runs(
    runs: List[SkillEvalRun],
    judge: LlmJudge | None = None,
    iterations: int = 1,
) -> dict:
    summary: dict = {}
    for mode in sorted({run.mode for run in runs}):
        mode_runs = [run for run in runs if run.mode == mode]
        passed = sum(1 for run in mode_runs if run.passed)
        total = len(mode_runs)
        summary[mode] = {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total if total else 0.0,
            "total_tokens": sum(
                run.input_tokens + run.output_tokens for run in mode_runs
            ),
            "duration_ms": sum(run.latency_ms for run in mode_runs),
        }

    with_mode = summary.get("with_skill")
    without_mode = summary.get("without_skill")
    if with_mode and without_mode:
        summary["skill_uplift"] = {
            "pass_rate_delta": with_mode["pass_rate"] - without_mode["pass_rate"],
            "total_tokens_delta": with_mode["total_tokens"]
            - without_mode["total_tokens"],
            "duration_ms_delta": with_mode["duration_ms"] - without_mode["duration_ms"],
            "improved": with_mode["pass_rate"] > without_mode["pass_rate"],
        }

    summary["iterations"] = iterations
    summary["benchmark"] = _build_benchmark(runs)
    summary["provider_usage"] = _summarize_provider_usage(runs)
    summary["grading"] = {
        "judge_enabled": judge is not None,
        "judge_model": judge.model if judge else None,
    }
    summary["assertion_audit"] = _audit_assertions(runs)
    return summary


def _audit_assertions(runs: List[SkillEvalRun]) -> dict:
    """Flag assertions that cannot discriminate skill value.

    Analysis rules from the agentskills evaluating-skills guide: an assertion
    that passes in BOTH modes tells you nothing (the model handles it without
    the skill); one that fails in BOTH modes is broken, too hard, or checks
    the wrong thing. Only meaningful when a baseline mode is present.
    """

    modes = {run.mode for run in runs}
    if "with_skill" not in modes or "without_skill" not in modes:
        return {"non_discriminating": [], "always_failing": [], "checked": False}

    # (case_id, assertion text) -> {mode: [passed, ...]}
    outcomes: dict = {}
    for run in runs:
        for assertion in run.assertions:
            key = (run.case_id, assertion.value)
            outcomes.setdefault(key, {}).setdefault(run.mode, []).append(
                assertion.passed
            )

    non_discriminating = []
    always_failing = []
    for (case_id, text), by_mode in outcomes.items():
        with_results = by_mode.get("with_skill", [])
        without_results = by_mode.get("without_skill", [])
        if not with_results or not without_results:
            continue
        entry = {"case_id": case_id, "assertion": text}
        if all(with_results) and all(without_results):
            non_discriminating.append(entry)
        elif not any(with_results) and not any(without_results):
            always_failing.append(entry)

    return {
        "non_discriminating": non_discriminating,
        "always_failing": always_failing,
        "checked": True,
    }


def _build_benchmark(runs: List[SkillEvalRun]) -> dict:
    """Aggregate per-run statistics into skill-creator style run_summary."""

    run_summary: dict = {}
    for mode in ("with_skill", "without_skill"):
        mode_runs = [run for run in runs if run.mode == mode]
        if not mode_runs:
            continue
        run_summary[mode] = {
            "pass_rate": _agg([run.assertion_pass_rate for run in mode_runs]),
            "time_seconds": _agg([run.latency_ms / 1000 for run in mode_runs]),
            "tokens": _agg(
                [float(run.input_tokens + run.output_tokens) for run in mode_runs]
            ),
        }

    with_stats = run_summary.get("with_skill")
    without_stats = run_summary.get("without_skill")
    if with_stats and without_stats:
        run_summary["delta"] = {
            "pass_rate": _round6(
                with_stats["pass_rate"]["mean"] - without_stats["pass_rate"]["mean"]
            ),
            "time_seconds": _round6(
                with_stats["time_seconds"]["mean"]
                - without_stats["time_seconds"]["mean"]
            ),
            "tokens": _round6(
                with_stats["tokens"]["mean"] - without_stats["tokens"]["mean"]
            ),
        }

    return {"run_summary": run_summary}


def _agg(values: List[float]) -> dict:
    return {
        "mean": _round6(_mean(values)),
        "stddev": _round6(_stddev(values)),
        "min": _round6(min(values)),
        "max": _round6(max(values)),
    }


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _stddev(values: List[float]) -> float:
    if not values:
        return 0.0
    avg = _mean(values)
    return (_mean([(value - avg) ** 2 for value in values])) ** 0.5


def _round6(value: float) -> float:
    return round(value, 6)


def _summarize_provider_usage(runs: List[SkillEvalRun]) -> dict:
    return {
        "providers": sorted({run.provider for run in runs}),
        "models": sorted({run.model for run in runs}),
        "calls": len(runs),
        "total_input_tokens": sum(run.input_tokens for run in runs),
        "total_output_tokens": sum(run.output_tokens for run in runs),
        "total_latency_ms": sum(run.latency_ms for run in runs),
    }
