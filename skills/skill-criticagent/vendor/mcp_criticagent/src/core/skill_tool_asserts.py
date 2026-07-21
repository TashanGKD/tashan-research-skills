"""Tool-call normalization and assertions for recorded host executions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "arguments": self.arguments}


def parse_tool_calls(raw_calls: object) -> list[ToolCall]:
    if raw_calls is None:
        return []
    if not isinstance(raw_calls, list):
        raise ValueError("tool_calls must be a list")

    parsed: list[ToolCall] = []
    for index, raw in enumerate(raw_calls):
        if not isinstance(raw, dict):
            raise ValueError(f"tool_calls[{index}] must be an object")
        function = raw.get("function") if isinstance(raw.get("function"), dict) else raw
        name = str(function.get("name") or "").strip()
        if not name:
            raise ValueError(f"tool_calls[{index}] is missing a name")
        arguments = function.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError as exc:
                raise ValueError(f"tool_calls[{index}] has invalid JSON arguments") from exc
        if not isinstance(arguments, dict):
            raise ValueError(f"tool_calls[{index}] arguments must be an object")
        parsed.append(ToolCall(name=name, arguments=arguments))
    return parsed


def nested_argument(arguments: dict[str, Any], path: str) -> tuple[bool, Any]:
    value: Any = arguments
    for segment in path.split("."):
        if not isinstance(value, dict) or segment not in value:
            return False, None
        value = value[segment]
    return True, value
