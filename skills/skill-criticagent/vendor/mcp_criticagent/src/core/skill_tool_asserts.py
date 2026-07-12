#!/usr/bin/env python3
"""Deterministic tool-call assertions for skill evals.

Mirrors darkrishabh/agent-skills-eval `grade.ts` / `types.ts`: tool calls are
captured from the model response but never executed; assertions are graded
locally with no LLM judge involved. Supported types: tool-called,
tool-not-called, tool-arg-equals, tool-arg-contains, tool-arg-matches,
tool-call-count. `path` is dot-notation into the parsed arguments object,
e.g. "command", "input.command", "files[0]".
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, List

TOOL_ASSERTION_TYPES = {
    "tool-called",
    "tool-not-called",
    "tool-arg-equals",
    "tool-arg-contains",
    "tool-arg-matches",
    "tool-call-count",
}

_PATH_TOKEN_PATTERN = re.compile(r"[^.\[\]]+|\[(\d+)\]")
_REGEX_FLAG_MAP = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL}


@dataclass
class ToolCall:
    name: str
    arguments: str = ""
    parsed_arguments: Any = None


@dataclass
class ToolAssertion:
    type: str
    name: str | None = None
    path: str | None = None
    value: Any = None
    pattern: str | None = None
    flags: str | None = None
    min: int | None = None
    max: int | None = None
    description: str | None = None


@dataclass
class ToolGradeResult:
    text: str
    passed: bool
    evidence: str


def parse_tool_calls(raw: Any) -> List[ToolCall]:
    """Parse OpenAI-style message.tool_calls into ToolCall records."""

    if not isinstance(raw, list):
        return []

    calls = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        function = entry.get("function")
        if not isinstance(function, dict):
            continue
        name = function.get("name")
        if not isinstance(name, str) or not name:
            continue
        arguments = function.get("arguments")
        arguments = arguments if isinstance(arguments, str) else ""
        parsed: Any = None
        if arguments:
            try:
                parsed = json.loads(arguments)
            except (ValueError, TypeError):
                parsed = None
        calls.append(ToolCall(name=name, arguments=arguments, parsed_arguments=parsed))
    return calls


def parse_tool_assertions(value: Any, where: str) -> List[ToolAssertion]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{where}.tool_assertions must be an array")
    return [
        _parse_tool_assertion(entry, f"{where}.tool_assertions[{index}]")
        for index, entry in enumerate(value)
    ]


def _parse_tool_assertion(entry: Any, where: str) -> ToolAssertion:
    if not isinstance(entry, dict):
        raise ValueError(f"{where} must be an object")

    assertion_type = entry.get("type")
    if assertion_type not in TOOL_ASSERTION_TYPES:
        raise ValueError(
            f"{where}.type must be one of: {', '.join(sorted(TOOL_ASSERTION_TYPES))}"
        )

    name = entry.get("name") if isinstance(entry.get("name"), str) else None
    description = (
        entry.get("description") if isinstance(entry.get("description"), str) else None
    )

    if assertion_type in ("tool-called", "tool-not-called"):
        if not name:
            raise ValueError(f"{where}.name is required for {assertion_type}")
        return ToolAssertion(type=assertion_type, name=name, description=description)

    if assertion_type in ("tool-arg-equals", "tool-arg-contains", "tool-arg-matches"):
        if not name:
            raise ValueError(f"{where}.name is required for {assertion_type}")
        path = entry.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError(f"{where}.path is required for {assertion_type}")
        if assertion_type == "tool-arg-matches":
            pattern = entry.get("pattern")
            if not isinstance(pattern, str):
                raise ValueError(f"{where}.pattern (regex string) is required")
            flags = entry.get("flags") if isinstance(entry.get("flags"), str) else None
            return ToolAssertion(
                type=assertion_type,
                name=name,
                path=path,
                pattern=pattern,
                flags=flags,
                description=description,
            )
        if assertion_type == "tool-arg-contains" and not isinstance(
            entry.get("value"), str
        ):
            raise ValueError(f"{where}.value must be a string for tool-arg-contains")
        return ToolAssertion(
            type=assertion_type,
            name=name,
            path=path,
            value=entry.get("value"),
            description=description,
        )

    # tool-call-count
    minimum = entry.get("min") if isinstance(entry.get("min"), int) else None
    maximum = entry.get("max") if isinstance(entry.get("max"), int) else None
    if minimum is None and maximum is None:
        raise ValueError(f"{where} requires at least one of min or max")
    return ToolAssertion(
        type="tool-call-count",
        name=name,
        min=minimum,
        max=maximum,
        description=description,
    )


def grade_tool_assertions(
    tool_calls: List[ToolCall], assertions: List[ToolAssertion]
) -> List[ToolGradeResult]:
    return [_grade_one(assertion, tool_calls or []) for assertion in assertions]


def _describe(assertion: ToolAssertion) -> str:
    if assertion.description:
        return assertion.description
    if assertion.type == "tool-called":
        return f'tool "{assertion.name}" was called'
    if assertion.type == "tool-not-called":
        return f'tool "{assertion.name}" was NOT called'
    if assertion.type == "tool-arg-equals":
        return f"{assertion.name}.{assertion.path} equals {json.dumps(assertion.value)}"
    if assertion.type == "tool-arg-contains":
        return (
            f"{assertion.name}.{assertion.path} contains {json.dumps(assertion.value)}"
        )
    if assertion.type == "tool-arg-matches":
        return (
            f"{assertion.name}.{assertion.path} matches "
            f"/{assertion.pattern}/{assertion.flags or ''}"
        )
    bounds = " and ".join(
        part
        for part in (
            f">={assertion.min}" if assertion.min is not None else "",
            f"<={assertion.max}" if assertion.max is not None else "",
        )
        if part
    )
    return f"{assertion.name or 'any tool'} called {bounds} times"


def _calls_by_name(tool_calls: List[ToolCall], name: str | None) -> List[ToolCall]:
    if not name:
        return tool_calls
    return [call for call in tool_calls if call.name == name]


def _get_by_path(root: Any, path: str) -> Any:
    current = root
    for match in _PATH_TOKEN_PATTERN.finditer(path):
        token: Any = (
            int(match.group(1)) if match.group(1) is not None else match.group(0)
        )
        if isinstance(token, int):
            if not isinstance(current, list) or token >= len(current):
                return None
            current = current[token]
        else:
            if not isinstance(current, dict) or token not in current:
                return None
            current = current[token]
    return current


def _grade_one(assertion: ToolAssertion, tool_calls: List[ToolCall]) -> ToolGradeResult:
    text = _describe(assertion)
    observed = ", ".join(call.name for call in tool_calls) or "(none)"
    matches = _calls_by_name(tool_calls, assertion.name)

    if assertion.type == "tool-called":
        if matches:
            return ToolGradeResult(
                text, True, f"{assertion.name} called {len(matches)} time(s)"
            )
        return ToolGradeResult(
            text, False, f"{assertion.name} not called; observed: {observed}"
        )

    if assertion.type == "tool-not-called":
        if not matches:
            return ToolGradeResult(
                text, True, f"confirmed: {assertion.name} never called"
            )
        return ToolGradeResult(
            text, False, f"{assertion.name} was called {len(matches)} time(s)"
        )

    if assertion.type == "tool-call-count":
        count = len(matches)
        min_ok = assertion.min is None or count >= assertion.min
        max_ok = assertion.max is None or count <= assertion.max
        label = assertion.name or "tools"
        if min_ok and max_ok:
            return ToolGradeResult(text, True, f"{label} called {count} time(s)")
        return ToolGradeResult(
            text, False, f"{label} called {count} time(s); expected {text}"
        )

    # Argument assertions require at least one call to inspect.
    if not matches:
        return ToolGradeResult(
            text, False, f"{assertion.name} not called; observed: {observed}"
        )

    if assertion.type == "tool-arg-matches":
        try:
            regex_flags = 0
            for flag_char in assertion.flags or "":
                regex_flags |= _REGEX_FLAG_MAP.get(flag_char, 0)
            regex = re.compile(assertion.pattern or "", regex_flags)
        except re.error as exc:
            return ToolGradeResult(
                text,
                False,
                f"invalid regex /{assertion.pattern}/{assertion.flags or ''}: {exc}",
            )

    seen = []
    for call in matches:
        if call.parsed_arguments is None:
            continue
        actual = _get_by_path(call.parsed_arguments, assertion.path or "")
        seen.append(json.dumps(actual, ensure_ascii=False))
        if assertion.type == "tool-arg-equals":
            if actual == assertion.value:
                return ToolGradeResult(
                    text,
                    True,
                    f"{assertion.name}.{assertion.path} = "
                    f"{json.dumps(actual, ensure_ascii=False)}",
                )
        elif assertion.type == "tool-arg-contains":
            if isinstance(actual, str) and assertion.value in actual:
                return ToolGradeResult(
                    text,
                    True,
                    f"{assertion.name}.{assertion.path} = "
                    f"{json.dumps(actual, ensure_ascii=False)}",
                )
        elif assertion.type == "tool-arg-matches":
            if isinstance(actual, str) and regex.search(actual):
                return ToolGradeResult(
                    text,
                    True,
                    f"{assertion.name}.{assertion.path} = "
                    f"{json.dumps(actual, ensure_ascii=False)}",
                )

    observed_values = ", ".join(seen) or "(no parseable arguments)"
    if assertion.type == "tool-arg-equals":
        expected = json.dumps(assertion.value, ensure_ascii=False)
        return ToolGradeResult(
            text, False, f"expected {expected}; observed {observed_values}"
        )
    if assertion.type == "tool-arg-contains":
        expected = json.dumps(assertion.value, ensure_ascii=False)
        return ToolGradeResult(
            text, False, f"expected substring {expected}; observed {observed_values}"
        )
    return ToolGradeResult(
        text,
        False,
        f"did not match /{assertion.pattern}/{assertion.flags or ''}; "
        f"observed {observed_values}",
    )
