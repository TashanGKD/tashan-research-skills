#!/usr/bin/env python3
"""LLM judge for free-form rubric assertions.

Grading protocol modeled on darkrishabh/agent-skills-eval `src/grade.ts`:
strict-JSON judge prompt, one retry on unparseable output, fail-closed
when the judge cannot be parsed, and per-assertion evidence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, List


@dataclass
class RubricGradeResult:
    text: str
    passed: bool
    evidence: str


JUDGE_PROMPT_HEADER = [
    "You are grading an Agent Skill evaluation run.",
    "",
    "Grading principles:",
    "- Require concrete evidence for every PASS; quote or reference the output.",
    "- Do not give the benefit of the doubt.",
    "- PASS an assertion only if every condition in the assertion text holds.",
    "- A label without substance is a FAIL.",
    "",
    "Return STRICT JSON only. No markdown. Shape:",
    '{"assertion_results":[{"text":"...","passed":true,"evidence":"..."}]}',
    "",
    "Rules:",
    "- Include every assertion exactly once and copy the full assertion text verbatim into text.",
    "- Use short concrete evidence: quote, snippet, or file reference.",
]


def render_rubric_prompt(
    assertions: List[str],
    model_output: str,
    previous_bad_response: str | None = None,
) -> str:
    parts = JUDGE_PROMPT_HEADER[:]
    if previous_bad_response:
        parts.append(
            "Previous response was not parseable JSON. Try again. "
            f"Bad response: {_truncate(previous_bad_response, 500)}"
        )
    parts.extend(
        [
            "",
            "Assertions:",
            json.dumps(assertions, ensure_ascii=False, indent=2),
            "",
            "Model output:",
            model_output or "(empty output)",
        ]
    )
    return "\n".join(parts)


def extract_json_object(value: str) -> str:
    trimmed = value.strip()
    if trimmed.startswith("{") and trimmed.endswith("}"):
        return trimmed
    first = trimmed.find("{")
    last = trimmed.rfind("}")
    if 0 <= first < last:
        return trimmed[first : last + 1]
    return trimmed


def normalize_rubric_grading(
    raw: Any, assertions: List[str]
) -> List[RubricGradeResult]:
    if not isinstance(raw, dict):
        raise ValueError("grading response must be an object")
    raw_results = raw.get("assertion_results")
    if not isinstance(raw_results, list):
        raise ValueError("grading response missing assertion_results")

    results = []
    for index, text in enumerate(assertions):
        entry = raw_results[index] if index < len(raw_results) else None
        if not isinstance(entry, dict):
            results.append(
                RubricGradeResult(
                    text=text,
                    passed=False,
                    evidence="judge omitted this assertion result",
                )
            )
            continue
        evidence = entry.get("evidence")
        results.append(
            RubricGradeResult(
                text=text,
                passed=entry.get("passed") is True,
                evidence=(
                    evidence.strip()
                    if isinstance(evidence, str) and evidence.strip()
                    else "judge did not provide concrete evidence"
                ),
            )
        )
    return results


def fail_closed(assertions: List[str], response: str) -> List[RubricGradeResult]:
    evidence = f"judge returned unparseable response: {_truncate(response, 500)}"
    return [
        RubricGradeResult(text=text, passed=False, evidence=evidence)
        for text in assertions
    ]


def grade_with_judge(judge_provider, assertions: List[str], model_output: str):
    """Grade free-form assertions with an LLM judge; fail closed on bad JSON.

    Returns (results, judge_prompt, judge_response).
    """

    if not assertions:
        return [], "", ""

    bad_response = ""
    last_prompt = ""
    last_text = ""
    for _attempt in range(2):
        last_prompt = render_rubric_prompt(
            assertions, model_output, previous_bad_response=bad_response or None
        )
        result = judge_provider.complete(last_prompt)
        last_text = result if isinstance(result, str) else result.output
        try:
            parsed = json.loads(extract_json_object(last_text))
            return normalize_rubric_grading(parsed, assertions), last_prompt, last_text
        except (ValueError, TypeError):
            bad_response = last_text

    return fail_closed(assertions, bad_response), last_prompt, last_text


def _truncate(value: str, max_length: int) -> str:
    return value if len(value) <= max_length else value[:max_length] + "..."
