#!/usr/bin/env python3
"""Extract and validate one AgentScope trigger batch for CriticAgent grading."""

import argparse
import json
from pathlib import Path
from typing import Any


def last_decisions_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    candidates = []
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and isinstance(value.get("decisions"), list):
            candidates.append(value)
    if not candidates:
        raise ValueError("provider output contains no parseable decisions object")
    return candidates[-1]


def build_decisions(
    report: dict[str, Any],
    queries_payload: dict[str, Any] | list[dict[str, Any]],
    skill_name: str,
) -> list[dict[str, Any]]:
    if report.get("status") != "pass":
        raise ValueError(f"provider report is not gradeable: {report.get('status')}")
    expected = (
        queries_payload
        if isinstance(queries_payload, list)
        else (queries_payload.get("trigger_queries") or queries_payload.get("queries") or [])
    )
    observed = last_decisions_object(str(report.get("final_text", ""))).get(
        "decisions", []
    )
    if len(observed) != len(expected):
        raise ValueError(f"expected {len(expected)} decisions, observed {len(observed)}")
    output = []
    for index, (query, decision) in enumerate(zip(expected, observed)):
        expected_query = query.get("query")
        if decision.get("query") != expected_query:
            raise ValueError(f"decision {index} does not preserve verbatim order")
        value = decision.get("decision")
        if value not in {skill_name, "none"}:
            raise ValueError(f"decision {index} has invalid value: {value!r}")
        output.append(
            {
                "query": expected_query,
                "should_trigger": query.get("should_trigger"),
                "decisions": [value],
            }
        )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("provider_report", type=Path)
    parser.add_argument("trigger_queries", type=Path)
    parser.add_argument("--skill-name", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = json.loads(args.provider_report.read_text(encoding="utf-8"))
    queries = json.loads(args.trigger_queries.read_text(encoding="utf-8"))
    decisions = build_decisions(report, queries, args.skill_name)
    rendered = json.dumps(decisions, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
