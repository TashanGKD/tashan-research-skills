#!/usr/bin/env python3
"""Validate and materialize model-authored CriticAgent quick eval packs."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import pathlib
import re
import shutil
from collections import Counter
from typing import Any


SCHEMA = "critic_eval_author_v1"
REVIEW_SCHEMA = "critic_eval_review_v1"
EXECUTION_MODE_REVIEW_SCHEMA = "critic_execution_mode_review_v1"
SKILL_TYPES = {"guidance", "hybrid", "executable"}
EXECUTION_MODE_TO_SKILL_TYPE = {
    "guidance": "guidance",
    "artifact": "executable",
    "tool": "executable",
    "hybrid": "hybrid",
}
CASE_MODES = {"guidance", "artifact", "tool"}
ASSERTION_TYPES = {"contains", "not_contains", "regex", "equals"}
FILE_ASSERTION_TYPES = {
    "file-exists",
    "file-not-exists",
    "file-contains",
    "file-matches",
}
TOOL_ASSERTION_TYPES = {
    "tool-called",
    "tool-not-called",
    "tool-arg-equals",
    "tool-arg-contains",
    "tool-arg-matches",
    "tool-call-count",
}
BROAD_NEGATIVE_SIDE_EFFECT_WORDS = {
    "apply",
    "bash",
    "delete",
    "install",
    "remove",
    "update",
    "write",
}
GENERIC_POSITIVE_STATUS_LABELS = {
    "claim",
    "evidence",
    "contribution",
    "supported",
    "needs evidence",
    "提示",
    "相关",
    "主要问题",
    "仍需确认",
}
MAX_CONTAINS_ANCHOR_WORDS = 5
MAX_CONTAINS_ANCHOR_CHARS = 48
CITATION_YEAR_RE = re.compile(r"\(\s*(?:19|20)\d{2}[a-z]?\s*\)", re.IGNORECASE)
VARIABLE_PROSE_PUNCTUATION_RE = re.compile(r"[()\[\]{}.,;:!?\"“”‘’]")
DYNAMIC_NUMERIC_REGEX_RE = re.compile(r"\\d|\[0-9\]")
PROMPT_DIGIT_RE = re.compile(r"\d")
GUIDANCE_REPAIR_CONTRACT = """For guidance skills, guidance cases MUST use exactly
`artifact_path: null`, `allowed_commands: []`, `file_assertions: []`,
`tool_assertions: []`, and `fixtures: []`. Do not add artifact paths, commands,
file assertions, tool assertions, or fixtures in a guidance repair."""


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def tree_manifest(root: pathlib.Path) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "size": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]


def manifest_sha256(manifest: list[dict[str, Any]]) -> str:
    return hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_execution_mode_review(
    review_path: pathlib.Path,
    skill_id: str,
    source_dir: pathlib.Path,
) -> dict[str, str]:
    """Load a source-bound execution-mode verdict without reclassifying it."""
    review_path = review_path.resolve()
    source_dir = source_dir.resolve()
    review = load_json(review_path)
    if (
        review.get("schema") != EXECUTION_MODE_REVIEW_SCHEMA
        or review.get("skill_id") != skill_id
    ):
        raise ValueError("execution-mode review identity or schema is invalid")
    current_source_sha = manifest_sha256(tree_manifest(source_dir))
    if review.get("source_tree_sha256") != current_source_sha:
        raise ValueError("execution-mode review source tree hash does not match")
    if review.get("review_status") == "needs_mode_review":
        raise ValueError("skill needs independent mode review before eval authoring")
    if review.get("review_status") != "source_reviewed":
        raise ValueError("execution-mode review status is invalid")
    execution_mode = review.get("execution_mode")
    if execution_mode not in EXECUTION_MODE_TO_SKILL_TYPE:
        raise ValueError("execution-mode review has no supported verdict")
    provider_sha = review.get("provider_report_sha256")
    if not isinstance(provider_sha, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", provider_sha):
        raise ValueError("execution-mode review lacks a provider report SHA-256")
    return {
        "execution_mode": execution_mode,
        "skill_type": EXECUTION_MODE_TO_SKILL_TYPE[execution_mode],
        "source_tree_sha256": current_source_sha,
        "provider_report_sha256": provider_sha.lower(),
        "review_sha256": sha256(review_path),
    }


def resolve_execution_mode_review(
    review_path: pathlib.Path,
    skill_id: str,
    source_dir: pathlib.Path,
    requested_skill_type: str,
    run_root: pathlib.Path,
) -> dict[str, str]:
    """Fail closed and archive any stale skill-type disagreement."""
    resolved = load_execution_mode_review(review_path, skill_id, source_dir)
    if resolved["skill_type"] == requested_skill_type:
        return resolved
    atomic_json(
        run_root / "execution-mode-conflict.json",
        {
            "schema": "critic_execution_mode_conflict_v1",
            "skill_id": skill_id,
            "requested_skill_type": requested_skill_type,
            "source_backed_skill_type": resolved["skill_type"],
            "source_backed_execution_mode": resolved["execution_mode"],
            "source_tree_sha256": resolved["source_tree_sha256"],
            "execution_mode_review_sha256": resolved["review_sha256"],
            "provider_report_sha256": resolved["provider_report_sha256"],
            "disposition": "staged_fix_first",
        },
    )
    raise ValueError(
        f"requested skill type {requested_skill_type!r} conflicts with source-backed "
        f"type {resolved['skill_type']!r}"
    )


def build_source_snapshot(
    source_dir: pathlib.Path,
    *,
    max_text_bytes: int = 262_144,
) -> str:
    """Embed all UTF-8 source text with paths and hashes; never silently truncate."""
    source_dir = source_dir.resolve()
    if not (source_dir / "SKILL.md").is_file():
        raise ValueError("source package requires SKILL.md")
    sections: list[str] = []
    text_bytes = 0
    for item in tree_manifest(source_dir):
        path = source_dir / pathlib.PurePosixPath(item["path"])
        raw = path.read_bytes()
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            content = "[binary file: content omitted; hash and size retained]"
        else:
            text_bytes += len(raw)
            if text_bytes > max_text_bytes:
                raise ValueError(
                    f"source text exceeds snapshot limit ({max_text_bytes} bytes)"
                )
        sections.append(
            f"FILE: {item['path']}\nSHA256: {item['sha256']}\nSIZE: {item['size']}\n"
            f"CONTENT:\n{content.rstrip()}"
        )
    return "\n\n---\n\n".join(sections)


def atomic_json(path: pathlib.Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def extract_json_object(text: str) -> str:
    stripped = text.strip()
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.S | re.I)
    if fenced:
        for candidate in fenced:
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and payload.get("schema") in {SCHEMA, REVIEW_SCHEMA}:
                return candidate
        return fenced[0]
    start = stripped.find("{")
    end = stripped.rfind("}")
    return stripped[start : end + 1] if 0 <= start < end else stripped


def parse_author_response(text: str) -> dict[str, Any]:
    payload = json.loads(extract_json_object(text))
    if not isinstance(payload, dict):
        raise ValueError("author response must contain a JSON object")
    return payload


def normalize_author_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize unambiguous schema aliases without changing evaluation meaning."""
    normalized = copy.deepcopy(payload)
    cases = normalized.get("cases")
    if isinstance(cases, list):
        for case in cases:
            if not isinstance(case, dict):
                continue
            if case.get("mode") == "guidance" and case.get("artifact_path") == "":
                case["artifact_path"] = None
            assertions = case.get("assertions")
            if not isinstance(assertions, list):
                continue
            file_assertions = case.get("file_assertions")
            if isinstance(file_assertions, list):
                misplaced = [
                    assertion
                    for assertion in assertions
                    if isinstance(assertion, dict)
                    and assertion.get("type") in FILE_ASSERTION_TYPES
                ]
                if misplaced:
                    case["assertions"] = [
                        assertion for assertion in assertions if assertion not in misplaced
                    ]
                    case["file_assertions"] = [*file_assertions, *misplaced]
                    assertions = case["assertions"]
            if (
                case.get("mode") == "tool"
                and not case.get("tool_assertions")
                and case.get("artifact_path")
                and case.get("file_assertions")
            ):
                case["mode"] = "artifact"
            for assertion in assertions:
                if not isinstance(assertion, dict) or "expected" not in assertion:
                    continue
                alias = assertion["expected"]
                if "value" in assertion and assertion["value"] != alias:
                    raise ValueError("assertion has conflicting assertion values")
                assertion["value"] = alias
                del assertion["expected"]
    triggers = normalized.get("triggers")
    if not isinstance(triggers, list):
        return normalized
    for index, trigger in enumerate(triggers):
        if not isinstance(trigger, dict) or "expected_match" not in trigger:
            continue
        alias = trigger["expected_match"]
        if "should_trigger" in trigger and trigger["should_trigger"] != alias:
            raise ValueError(f"triggers[{index}] has conflicting trigger labels")
        trigger["should_trigger"] = alias
        del trigger["expected_match"]
    return normalized


def normalize_review_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Unwrap an unambiguous schema-named review envelope."""
    normalized = copy.deepcopy(payload)
    if set(normalized) != {REVIEW_SCHEMA}:
        return normalized
    inner = normalized.get(REVIEW_SCHEMA)
    if not isinstance(inner, dict):
        return normalized
    inner_schema = inner.get("schema")
    if inner_schema not in {None, REVIEW_SCHEMA}:
        return normalized
    inner["schema"] = REVIEW_SCHEMA
    return inner


def build_author_prompt(
    skill_id: str,
    skill_type: str,
    *,
    native_eval: Any | None = None,
    source_snapshot: str | None = None,
    mode_contract: dict[str, Any] | None = None,
) -> str:
    if skill_type not in SKILL_TYPES:
        raise ValueError(f"unsupported skill type: {skill_type}")
    native_section = (
        json.dumps(native_eval, ensure_ascii=False, indent=2)
        if native_eval is not None
        else "(none)"
    )
    source_instruction = (
        "The complete hash-backed source package is embedded below. Do not call tools; "
        "read every embedded source section before writing tests."
        if source_snapshot is not None
        else f"Load the mounted skill `{skill_id}` and read its complete SKILL.md before writing tests."
    )
    source_section = source_snapshot if source_snapshot is not None else "(mounted source)"
    mode_section = (
        json.dumps(mode_contract, ensure_ascii=False, indent=2)
        if mode_contract is not None
        else "(not provided)"
    )
    return f"""You are the Eval Author stage of Skill-CriticAgent.
Return one compact JSON object only. Do not emit analysis, reasoning, commentary, or Markdown fences.
Do not repeat or summarize the embedded source. Keep author_rationale and self_review.notes to one concise sentence each.
{source_instruction}
Create exactly three distinct, realistic behavior cases and exactly eight trigger queries.
Trigger queries must contain four positives and four near-miss negatives.
Behavior prompts must be natural paraphrases and must not duplicate any trigger query.
Do not put expected answer phrases in the user prompt. Every case needs at least one
positive deterministic assertion that does not already match its prompt.
Use only assertion types contains, not_contains, regex, equals. Regex must compile.
Use source-backed requirements only; do not invent capabilities, dependencies, files,
commands, or install instructions. A native eval shown below is reference material, not an answer table.
The execution environment is offline and isolated. It contains only the mounted
skill source plus fixtures and exact commands declared by the case. If the skill
needs an unavailable dependency, API, sibling skill, network service, hardware,
or user dataset, test its documented prerequisite/fallback behavior instead of
pretending the dependency exists. Prefer robust regex alternatives over exact
formatting phrases. Never use a broad side-effect word such as delete, update,
write, install, or apply as a standalone not_contains assertion.
Each `contains` assertion must be a short semantic anchor: at most five whitespace
tokens and 48 characters, with no citation year, sentence punctuation, brackets,
or Markdown syntax. Split independent requirements into multiple short anchors;
use a deliberately flexible regex when punctuation or formatting is meaningful.
Code identifiers must use regex, not contains; reserve contains for natural-language
semantic anchors rather than names with underscores, dots, slashes, or code syntax.
Do not use generic headings or status labels such as `Claim`, `Evidence`,
`contribution`, `supported`, `needs evidence`, `提示`, `相关`, `主要问题`, or
`仍需确认` as positive assertions; choose a source-specific concept or outcome
that should distinguish the requested case.
Do not use bare task verbs or generic nouns such as `shorten`, `tradeoff`,
`variant`, or `acronym` as positive assertions; combine them with a source-specific outcome
or concept. A positive assertion must name an observable source-specific outcome, not
a generic phrase whose words could apply to many unrelated tasks.
If the source says to stop when a prerequisite is unavailable, every offline case
that needs it must test that stop/fallback path.
Follow the source-backed execution-mode contract below exactly. An artifact case
must test a file that the source names as a normal primary output. Do not invent a
notice, refusal, or fallback file merely to satisfy the executable schema. A
conversational prerequisite/fallback is a guidance case. A tool case must use an
exact source-documented command that is available in the isolated environment;
otherwise the skill is not behavior-verifiable in this environment.
Every case must preserve the source-backed execution mode and observed modes in
the contract. Do not relabel a primary artifact path as guidance or a tool path as
guidance. Use the exact source-documented primary output path; when the harness
stores that output under `outputs/`, preserve the source-relative filename instead
of inventing a different basename or directory.
Never assert a successful analysis, scan, clean result, or report unless declared local fixtures and tools make that
result observable. In self_review.notes, enumerate the offline path for every case.
For script-backed cases, derive output assertions from the exact executed code path,
not from documentation prose or a different subcommand. A stdout anchor must occur in
that branch's emitted text. A file regex must match the complete record shape actually
written by the source, including CSV columns or delimiters, rather than an isolated field.
For fallback or refusal cases, prefer positive prerequisite, limitation, or next-step
assertions; do not use not_contains on requested task terms or report section names,
because a correct explanation may repeat what it cannot perform.

Skill type: {skill_type}
For guidance skills, all cases use mode `guidance` and no artifacts or commands.
For hybrid/executable skills, at least one case must use mode `artifact` or `tool`.
Artifact paths must be safe relative paths under `outputs/`. Commands, when needed,
must be exact argv/command templates supported by the mounted skill and local fixtures.
Every command path must exist in the source snapshot; never invent a runner script from
an illustrative command. Fixture target format must match its source file content; do
not rename a Markdown reference into a CSV or other incompatible input type.
Use only `{{skill_dir}}` for the mounted implementation root and `{{workspace}}` for
the isolated run root. For example: `python "{{skill_dir}}/scripts/run.py"
"{{workspace}}/inputs/sample.txt" --output "{{workspace}}/outputs/report.json"`.
Declared inputs are staged identically for with-skill and without-skill, while
implementation commands are available only to the with-skill run. Never put an
implementation script in fixtures; fixtures are user inputs only.

Native eval reference:
{native_section}

Source-backed execution-mode contract:
{mode_section}

Hash-backed source package:
{source_section}

Return strict JSON only as one compact JSON object with schema `{SCHEMA}` and keys:
schema, skill_id, skill_type, author_rationale, self_review, cases, triggers.
Each case requires id, prompt, mode, assertions, file_assertions, tool_assertions,
artifact_path, allowed_commands, fixtures. Fixtures are objects with a source_path
inside the source package and a unique target_path under `inputs/`; use [] when none.
`tool_assertions` is a flat array of typed checks, never a command object wrapping a
nested `assertions` array. Allowed types are `tool-called`, `tool-not-called`,
`tool-arg-equals`, `tool-arg-contains`, `tool-arg-matches`, and `tool-call-count`;
argument checks use the source-documented tool `name` and argument `path`.
Every output assertion must contain a non-empty string `value`. Never emit an empty
string, null, or a key named `pattern` for output assertions. `contains` values must
follow the short semantic-anchor contract above; a `not_contains` value must not occur in its case prompt.
For guidance skills, guidance cases must use exactly
`artifact_path: null`, `allowed_commands: []`, `file_assertions: []`,
`tool_assertions: []`, and `fixtures: []`. For non-guidance cases, every fixture must
use `{{"source_path":"<existing source-relative file>","target_path":"inputs/<filename>"}}`.
Artifact paths start with `outputs/`, while each
file_assertions.path is relative to that outputs directory and must omit `outputs/`.
`file_assertions` is a flat array, never an object containing another assertions array.
Use forms such as `{{"type":"file-exists","path":"report.json"}}`,
`{{"type":"file-contains","path":"report.json","value":"finding"}}`, or
`{{"type":"file-matches","path":"report.json","pattern":"finding.*major"}}`.
Do not wrap the JSON in explanatory prose. Use compact strings and no optional commentary.
Each trigger object requires exactly `query` and boolean `should_trigger` fields.
Before returning, complete self_review with boolean true values for source_fidelity,
offline_feasibility, prompt_trigger_separation, assertion_robustness, and
artifact_evidence, plus a non-empty notes string. A false check means revise first.
Run this schema preflight before returning: exactly 3 cases; exactly 8 triggers split
4/4; every assertion value is non-empty; no negative assertion repeats prompt text;
all guidance empty fields use the canonical values above; every fixture target begins
with `inputs/`; and every self-review field is true.
"""


def build_review_prompt(
    skill_id: str,
    skill_type: str,
    authored_payload: dict[str, Any],
    *,
    source_snapshot: str,
    mode_contract: dict[str, Any],
) -> str:
    return f"""You are the Eval Reviewer stage of Skill-CriticAgent.
The complete hash-backed source package is embedded below. Do not call tools.
Check the proposed pack only against this source. Do not use or request behavior-run outputs.
Review source fidelity, offline feasibility, case diversity, prompt-echo risk,
deterministic assertion robustness, broad not_contains collisions, artifact/tool
evidence, and four-positive/four-negative trigger balance.
Reject long, citation-form, sentence-punctuation, bracketed, or Markdown-sensitive
`contains` values. Require short semantic anchors or a deliberately flexible regex.
Reject bare task verbs or generic nouns as positive assertions unless they are
combined with a source-specific outcome or concept. Prefer an observable source-specific
outcome over a generic phrase whose words could apply to many unrelated tasks.
Reject any artifact or tool case that conflicts with the source-backed execution
mode, invents a fallback/notice file, or substitutes a conversational stop message
for the source's normal primary output.
Behavior prompts must remain varied natural requests, not copies of trigger queries.
Guidance cases correctly omit file assertions when they produce no artifact; do not
invent file checks merely to test whether packaged source references exist.

The harness stores artifacts under `outputs/`; file_assertions paths are relative to that directory. When the source documents a relative primary output filename, the authored `artifact_path` should use the same filename with the harness `outputs/` prefix, and file assertions should omit that prefix; preserve the source-relative filename and do not reject this harness prefix as a source-path change.

The execution host is offline and isolated: only mounted source, declared fixtures,
exact allowed commands, and declared outputs exist. Cases requiring unavailable
dependencies must test the documented prerequisite or fallback instead.

Return strict JSON only with schema `{REVIEW_SCHEMA}`, skill_id, verdict
(`approved` or `rejected`), issues, reviewed_payload, and review_rationale.
For approved, reviewed_payload must be an exact semantic copy of the proposed
`{SCHEMA}` payload. Never rewrite cases, prompts, assertions, fixtures, commands,
or triggers. If any change is needed, reject the pack and set reviewed_payload to
null. Do not quote or infer any behavior-run result.

Skill type: {skill_type}
Proposed pack:
{json.dumps(authored_payload, ensure_ascii=False, indent=2)}

Source-backed execution-mode contract:
{json.dumps(mode_contract, ensure_ascii=False, indent=2)}

Hash-backed source package:
{source_snapshot}
"""


def build_repair_prompt(
    skill_id: str,
    skill_type: str,
    invalid_payload: dict[str, Any],
    validation_error: str,
) -> str:
    """Request one schema repair without re-supplying source or expected answers."""
    return f"""You are the one-attempt schema repair stage of Skill-CriticAgent.
The Eval Author payload below failed the deterministic validator. Correct only the
reported contract violation and any directly dependent schema fields. Preserve the
three behavior tasks, their scientific meaning, trigger intent, and source-backed
claims. Do not add source facts, capabilities, dependencies, commands, expected
answers, or new test cases. Do not delete an assertion merely to make validation pass;
replace an invalid assertion with a source-neutral, non-empty assertion that preserves
the original requirement. Do not weaken a positive check into a negative-only check.
When replacing a generic status label, choose a source-specific, non-prompt-echo positive assertion from the same case. Before returning, verify that every case retains at least one discriminating positive assertion that does not occur in its prompt.
Do not keep bare task verbs or generic nouns as positive assertions; combine them with
a source-specific outcome or concept. Prefer an observable source-specific outcome over
a generic phrase whose words could apply to many unrelated tasks.

Skill identity: {skill_id}
Skill type: {skill_type}
Deterministic validation error:
{validation_error}

Original invalid payload:
{json.dumps(invalid_payload, ensure_ascii=False, indent=2)}

Return one complete corrected `critic_eval_author_v1` payload as strict JSON only.
Set the top-level schema field exactly to `critic_eval_author_v1`. Preserve all
required top-level keys: schema, skill_id, skill_type, author_rationale,
self_review, cases, and triggers. For file checks, the only allowed types are
file-exists, file-not-exists, file-contains, or file-matches. Every artifact case
requires both a non-empty artifact_path beginning with `outputs/` and at least one
file assertion. file_assertions must be a flat array; each path is relative to the
outputs directory and must omit the `outputs/` prefix. file-contains requires a
non-empty `value`; file-matches requires a non-empty `pattern`.
`tool_assertions` must be a flat array of typed checks, never a command object
wrapping a nested `assertions` array. Use only `tool-called`, `tool-not-called`,
`tool-arg-equals`, `tool-arg-contains`, `tool-arg-matches`, or `tool-call-count`,
with the source-documented tool name and argument path.
Fixtures may not contain inline content. Each fixture must use `source_path` for an
existing source-relative file and a unique target_path beginning with `inputs/`;
use an empty fixture array when the source package has no suitable input.
Every command path must exist in the source snapshot; never invent a runner script.
Fixture target format must match its source file content; do not rename Markdown into
a CSV or another incompatible input type.
It must retain exactly three behavior cases and eight triggers split four positive and
four negative. Every output assertion requires a non-empty string `value`; broad
standalone negative side-effect words are forbidden; negative assertions must not
repeat their case prompt; guidance cases use null artifact_path and empty command,
fixture, file-assertion, and tool-assertion arrays. {GUIDANCE_REPAIR_CONTRACT}
A `contains` value must be a short
semantic anchor of at most five whitespace tokens and 48 characters, without a
citation year, sentence punctuation, brackets, or Markdown syntax. This is the only
repair attempt. Code identifiers must use regex, not contains; contains is reserved
for natural-language semantic anchors.
"""


def build_unparseable_repair_prompt(
    skill_id: str,
    skill_type: str,
    invalid_response: str,
    validation_error: str,
) -> str:
    """Request the same one repair when the first response is not valid JSON."""
    return f"""You are the one-attempt schema repair stage of Skill-CriticAgent.
The Eval Author response below could not be parsed as complete JSON. Reconstruct only
the response that was already attempted. Preserve its behavior tasks, scientific
meaning, trigger intent, source-backed claims, assertions, fixtures, and commands.
Do not add source facts, capabilities, dependencies, commands, expected answers, or
new test cases. Do not delete assertions or weaken positive checks. Return no prose.

Skill identity: {skill_id}
Skill type: {skill_type}
Deterministic validation error:
{validation_error}

Original invalid response:
<original_response>
{invalid_response}
</original_response>

Return one complete corrected `critic_eval_author_v1` payload as strict JSON only.
Set the schema and identity fields exactly, retain exactly three behavior cases and
eight triggers split four positive and four negative, and obey the unchanged
assertion, artifact, fixture, and execution-mode contracts from the original request.
{GUIDANCE_REPAIR_CONTRACT}
This is the only repair attempt.
"""


def build_review_repair_prompt(
    skill_id: str,
    skill_type: str,
    invalid_review: dict[str, Any],
    validation_error: str,
) -> str:
    """Request one envelope-only repair without reopening review semantics."""
    return f"""You are the one-attempt schema repair stage for an Eval Reviewer response.
Correct only the review envelope schema violation reported below. The verdict,
reviewed_payload, and review_rationale must remain exactly unchanged. Do not add,
remove, or alter behavior cases, assertions, triggers, source claims, or review
conclusions. If issues are strings, wrap each one as an object with case_id, code,
and detail while preserving its full text.

Skill identity: {skill_id}
Skill type: {skill_type}
Deterministic validation error:
{validation_error}

Original invalid review:
{json.dumps(invalid_review, ensure_ascii=False, indent=2)}

Return one complete corrected `critic_eval_review_v1` object as strict JSON only.
This is the only review repair attempt.
"""


def _validate_output_assertion(assertion: Any, where: str, prompt: str) -> None:
    if not isinstance(assertion, dict) or assertion.get("type") not in ASSERTION_TYPES:
        raise ValueError(f"{where} requires a supported deterministic assertion")
    value = assertion.get("value")
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}.value must be a non-empty string")
    if assertion["type"] in {"contains", "equals"} and value.strip().casefold() in {
        item.casefold() for item in GENERIC_POSITIVE_STATUS_LABELS
    }:
        raise ValueError(f"{where} uses a generic status label as a positive assertion")
    if assertion["type"] == "regex":
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError(f"{where} contains invalid regex: {exc}") from exc
        if DYNAMIC_NUMERIC_REGEX_RE.search(value) and not PROMPT_DIGIT_RE.search(prompt):
            raise ValueError(
                f"{where} requires a numeric identifier absent from its prompt"
            )
    if assertion["type"] == "contains":
        stripped = value.strip()
        brittle = (
            len(stripped) > MAX_CONTAINS_ANCHOR_CHARS
            or len(stripped.split()) > MAX_CONTAINS_ANCHOR_WORDS
            or CITATION_YEAR_RE.search(stripped) is not None
            or VARIABLE_PROSE_PUNCTUATION_RE.search(stripped) is not None
            or any(marker in stripped for marker in ("*", "_", "`"))
        )
        if brittle:
            raise ValueError(
                f"{where} uses a brittle contains anchor; use a short semantic anchor or regex"
            )
    if (
        assertion["type"] == "not_contains"
        and value.strip().casefold() in BROAD_NEGATIVE_SIDE_EFFECT_WORDS
    ):
        raise ValueError(f"{where} uses a broad negative side-effect word")


def _positive_assertion_matches_prompt(assertion: dict[str, Any], prompt: str) -> bool:
    kind = assertion["type"]
    value = assertion["value"]
    if kind == "not_contains":
        return False
    if kind == "regex":
        return re.search(value, prompt) is not None
    return value.casefold() in prompt.casefold()


def _validate_artifact_path(value: Any, where: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where} must be a relative path or null")
    normalized = value.replace("\\", "/")
    path = pathlib.PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != "outputs":
        raise ValueError(f"{where} must stay under outputs/")
    if normalized.endswith("/"):
        raise ValueError(f"{where} must name a file, not a directory")
    return path.as_posix()


def _validate_output_relative_path(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where} must be a non-empty outputs-relative path")
    path = pathlib.PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"{where} must be relative to outputs/")
    if path.parts[0] == "outputs":
        raise ValueError(f"{where} is already relative to outputs/; omit outputs/")
    return path.as_posix()


def _validate_file_assertions(value: Any, where: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{where} must be an array")
    for index, assertion in enumerate(value):
        if not isinstance(assertion, dict) or assertion.get("type") not in FILE_ASSERTION_TYPES:
            raise ValueError(f"{where}[{index}] has unsupported type")
        _validate_output_relative_path(
            assertion.get("path"), f"{where}[{index}].path"
        )
        if assertion["type"] == "file-contains" and not isinstance(assertion.get("value"), str):
            raise ValueError(f"{where}[{index}].value is required")
        if assertion["type"] == "file-matches":
            pattern = assertion.get("pattern")
            if not isinstance(pattern, str):
                raise ValueError(f"{where}[{index}].pattern is required")
            re.compile(pattern)
    return value


def _validate_tool_assertions(value: Any, where: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{where} must be an array")
    for index, assertion in enumerate(value):
        if not isinstance(assertion, dict) or assertion.get("type") not in TOOL_ASSERTION_TYPES:
            raise ValueError(f"{where}[{index}] has unsupported type")
    return value


def _validate_fixtures(value: Any, where: str) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{where} must be an array")
    normalized: list[dict[str, str]] = []
    targets: set[str] = set()
    for index, fixture in enumerate(value):
        if not isinstance(fixture, dict):
            raise ValueError(f"{where}[{index}] must be an object")
        source = fixture.get("source_path")
        target = fixture.get("target_path")
        if not isinstance(source, str) or not source.strip():
            raise ValueError("fixture source_path must be a safe relative path")
        source_path = pathlib.PurePosixPath(source.replace("\\", "/"))
        if source_path.is_absolute() or ".." in source_path.parts or ":" in source_path.parts[0]:
            raise ValueError("fixture source_path must be a safe relative path")
        if not isinstance(target, str) or not target.strip():
            raise ValueError("fixtures must target inputs/")
        target_path = pathlib.PurePosixPath(target.replace("\\", "/"))
        if (
            target_path.is_absolute()
            or ".." in target_path.parts
            or not target_path.parts
            or target_path.parts[0] != "inputs"
        ):
            raise ValueError("fixtures must target inputs/")
        target_value = target_path.as_posix()
        if target_value in targets:
            raise ValueError("fixture target_path values must be unique")
        targets.add(target_value)
        normalized.append(
            {
                "source_path": source_path.as_posix(),
                "target_path": target_value,
            }
        )
    return normalized


def validate_author_payload(
    payload: dict[str, Any],
    skill_id: str,
    skill_type: str,
) -> dict[str, Any]:
    if payload.get("schema") != SCHEMA:
        raise ValueError(f"author payload must use schema {SCHEMA}")
    if payload.get("skill_id") != skill_id or payload.get("skill_type") != skill_type:
        raise ValueError("author payload identity does not match the requested skill")
    if skill_type not in SKILL_TYPES:
        raise ValueError(f"unsupported skill type: {skill_type}")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != 3:
        raise ValueError("author payload requires exactly three behavior cases")
    ids = []
    behavior_prompts = []
    modes = Counter()
    echo_risks = []
    for index, case in enumerate(cases):
        where = f"cases[{index}]"
        if not isinstance(case, dict):
            raise ValueError(f"{where} must be an object")
        case_id = case.get("id")
        prompt = case.get("prompt")
        mode = case.get("mode")
        if not isinstance(case_id, str) or not case_id.strip() or case_id in ids:
            raise ValueError("case IDs must be non-empty and unique")
        ids.append(case_id)
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"{where}.prompt must be non-empty")
        behavior_prompts.append(prompt.strip())
        if mode not in CASE_MODES:
            raise ValueError(f"{where}.mode must be guidance, artifact, or tool")
        modes[mode] += 1
        assertions = case.get("assertions")
        if not isinstance(assertions, list):
            raise ValueError(f"{where}.assertions must be an array")
        assertion_errors = []
        for assertion_index, assertion in enumerate(assertions):
            try:
                _validate_output_assertion(
                    assertion,
                    f"{where}.assertions[{assertion_index}]",
                    prompt,
                )
            except ValueError as exc:
                assertion_errors.append(str(exc))
                continue
            if (
                assertion["type"] == "not_contains"
                and assertion["value"].casefold() in prompt.casefold()
            ):
                raise ValueError(f"{where} negative assertion conflicts with its prompt")
        if assertion_errors:
            raise ValueError("; ".join(assertion_errors))
        file_assertions = _validate_file_assertions(
            case.get("file_assertions"), f"{where}.file_assertions"
        )
        tool_assertions = _validate_tool_assertions(
            case.get("tool_assertions"), f"{where}.tool_assertions"
        )
        _validate_fixtures(case.get("fixtures"), f"{where}.fixtures")
        artifact_path = _validate_artifact_path(case.get("artifact_path"), f"{where}.artifact_path")
        commands = case.get("allowed_commands")
        if not isinstance(commands, list) or not all(
            isinstance(command, str) and command.strip() for command in commands
        ):
            raise ValueError(f"{where}.allowed_commands must contain strings")
        if mode == "guidance" and (artifact_path or commands or file_assertions or tool_assertions):
            raise ValueError("guidance cases cannot declare artifacts or tool effects")
        if mode == "artifact" and (not artifact_path or not file_assertions):
            raise ValueError("artifact cases require artifact_path and file_assertions")
        if mode == "tool" and not tool_assertions:
            raise ValueError("tool cases require tool_assertions")
        positive = [a for a in assertions if a["type"] != "not_contains"]
        non_echo = [a for a in positive if not _positive_assertion_matches_prompt(a, prompt)]
        if not non_echo and not file_assertions and not tool_assertions:
            echo_risks.append(case_id)
    if len(set(ids)) != 3:
        raise ValueError("case IDs must be unique")
    if echo_risks:
        raise ValueError(f"prompt-echo risk leaves no discriminating assertion: {echo_risks}")
    if skill_type == "guidance" and set(modes) != {"guidance"}:
        raise ValueError("guidance skills require guidance cases only")
    if skill_type in {"hybrid", "executable"} and not (modes["artifact"] or modes["tool"]):
        raise ValueError("hybrid/executable skills require an artifact or tool case")
    triggers = payload.get("triggers")
    if not isinstance(triggers, list) or len(triggers) != 8:
        raise ValueError("author payload requires exactly eight trigger queries")
    queries = []
    for index, trigger in enumerate(triggers):
        if not isinstance(trigger, dict):
            raise ValueError(f"triggers[{index}] must be an object")
        query = trigger.get("query")
        if not isinstance(query, str) or not query.strip() or query in queries:
            raise ValueError("trigger queries must be non-empty and unique")
        if trigger.get("should_trigger") not in {True, False}:
            raise ValueError("trigger should_trigger must be boolean")
        queries.append(query)
    counts = Counter(trigger["should_trigger"] for trigger in triggers)
    if counts[True] != 4 or counts[False] != 4:
        raise ValueError("trigger queries must contain four positive and four negative cases")
    trigger_text = {query.casefold() for query in queries}
    if any(prompt.casefold() in trigger_text for prompt in behavior_prompts):
        raise ValueError("behavior prompts must differ from trigger queries")
    if not isinstance(payload.get("author_rationale"), str) or not payload["author_rationale"].strip():
        raise ValueError("author_rationale is required")
    self_review = payload.get("self_review")
    review_checks = (
        "source_fidelity",
        "offline_feasibility",
        "prompt_trigger_separation",
        "assertion_robustness",
        "artifact_evidence",
    )
    if not isinstance(self_review, dict) or any(
        self_review.get(check) is not True for check in review_checks
    ):
        raise ValueError("self_review checks must all be true")
    if not isinstance(self_review.get("notes"), str) or not self_review["notes"].strip():
        raise ValueError("self_review notes are required")
    return {
        "case_count": 3,
        "trigger_count": 8,
        "execution_modes": dict(sorted(modes.items())),
        "prompt_echo_risks": [],
    }


def validate_review_payload(
    payload: dict[str, Any],
    skill_id: str,
    skill_type: str,
    authored_payload: dict[str, Any],
) -> dict[str, Any]:
    normalized = normalize_review_payload(payload)
    if normalized.get("schema") != REVIEW_SCHEMA or normalized.get("skill_id") != skill_id:
        raise ValueError("review payload identity or schema is invalid")
    verdict = normalized.get("verdict")
    if verdict not in {"approved", "rejected"}:
        raise ValueError("review verdict must be approved or rejected")
    issues = normalized.get("issues")
    if not isinstance(issues, list) or not all(isinstance(issue, dict) for issue in issues):
        raise ValueError("review issues must be an array of objects")
    rationale = normalized.get("review_rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("review_rationale is required")
    reviewed = normalized.get("reviewed_payload")
    if verdict == "rejected":
        if reviewed is not None:
            raise ValueError("rejected review must not provide reviewed_payload")
    else:
        if not isinstance(reviewed, dict):
            raise ValueError("approved review requires reviewed_payload")
        reviewed = normalize_author_payload(reviewed)
        validate_author_payload(reviewed, skill_id, skill_type)
        authored = normalize_author_payload(authored_payload)
        if reviewed != authored:
            raise ValueError("approved review must preserve authored_payload")
    normalized["reviewed_payload"] = reviewed
    return normalized


def consume_single_repair_report(
    run_root: pathlib.Path,
    report_path: pathlib.Path,
    skill_id: str,
    skill_type: str,
) -> tuple[dict[str, Any], str]:
    """Consume one immutable repair response and reject a different second attempt."""
    run_root = run_root.resolve()
    report_path = report_path.resolve()
    report_sha = sha256(report_path)
    marker_path = run_root / "repair-attempt.json"
    if marker_path.is_file():
        marker = load_json(marker_path)
        if marker.get("repair_report_sha256") != report_sha:
            raise ValueError("a repair attempt was already consumed for this run")
    else:
        atomic_json(
            marker_path,
            {
                "schema": "critic_eval_repair_attempt_v1",
                "attempt_count": 1,
                "repair_report_sha256": report_sha,
            },
        )

    report = load_json(report_path)
    try:
        if report.get("status") != "pass" or report.get("source_unchanged") is not True:
            raise ValueError("repair provider report did not pass source invariants")
        payload = normalize_author_payload(
            parse_author_response(str(report.get("final_text") or ""))
        )
        validate_author_payload(payload, skill_id, skill_type)
    except (ValueError, json.JSONDecodeError) as exc:
        atomic_json(
            run_root / "repair-validation-error.json",
            {
                "schema": "critic_eval_validation_error_v1",
                "stage": "repair",
                "repair_report_sha256": report_sha,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        raise
    return payload, report_sha


def consume_single_review_repair_report(
    run_root: pathlib.Path,
    report_path: pathlib.Path,
    original_review: dict[str, Any],
    skill_id: str,
    skill_type: str,
    authored_payload: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    """Consume one reviewer-envelope repair and forbid semantic changes."""
    report_sha = sha256(report_path)
    marker_path = run_root / "review-repair-attempt.json"
    if marker_path.exists():
        marker = load_json(marker_path)
        if marker.get("repair_report_sha256") != report_sha:
            raise ValueError("a review repair attempt was already consumed for this run")
    else:
        atomic_json(
            marker_path,
            {
                "schema": "critic_eval_review_repair_attempt_v1",
                "attempt_count": 1,
                "repair_report_sha256": report_sha,
            },
        )
    report = load_json(report_path)
    try:
        if report.get("status") != "pass" or report.get("source_unchanged") is not True:
            raise ValueError("review repair provider report did not pass source invariants")
        repaired = validate_review_payload(
            parse_author_response(str(report.get("final_text") or "")),
            skill_id,
            skill_type,
            authored_payload,
        )
        original_normalized = normalize_review_payload(original_review)
        for field in ("verdict", "reviewed_payload", "review_rationale"):
            if repaired.get(field) != original_normalized.get(field):
                raise ValueError(f"review repair changed {field}")
    except (ValueError, json.JSONDecodeError) as exc:
        atomic_json(
            run_root / "review-repair-validation-error.json",
            {
                "schema": "critic_eval_validation_error_v1",
                "stage": "review_repair",
                "repair_report_sha256": report_sha,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        raise
    return repaired, report_sha


def materialize_pack(
    source_dir: pathlib.Path,
    output_dir: pathlib.Path,
    payload: dict[str, Any],
    *,
    author_report_sha256: str,
    native_eval_sha256: str | None,
    reviewer_report_sha256: str | None = None,
    reviewer_repair_report_sha256: str | None = None,
    repair_report_sha256: str | None = None,
    execution_mode_review: dict[str, str] | None = None,
) -> dict[str, Any]:
    source_dir = source_dir.resolve()
    output_dir = output_dir.resolve()
    if not (source_dir / "SKILL.md").is_file():
        raise ValueError("source package requires SKILL.md")
    if output_dir.exists():
        raise ValueError(f"refusing to overwrite eval package: {output_dir}")
    validate_author_payload(payload, payload["skill_id"], payload["skill_type"])
    source_files = tree_manifest(source_dir)
    shutil.copytree(source_dir, output_dir)
    evals = {"evals": []}
    for case in payload["cases"]:
        fixtures = _validate_fixtures(case.get("fixtures"), "case.fixtures")
        for fixture in fixtures:
            fixture_source = (source_dir / fixture["source_path"]).resolve()
            try:
                fixture_source.relative_to(source_dir)
            except ValueError as exc:
                raise ValueError("fixture source escapes the source package") from exc
            if not fixture_source.is_file():
                raise ValueError(
                    f"fixture source does not exist: {fixture['source_path']}"
                )
        evals["evals"].append(
            {
                "id": case["id"],
                "prompt": case["prompt"],
                "mode": case["mode"],
                "artifact_path": case["artifact_path"],
                "allowed_commands": case["allowed_commands"],
                "assertions": case["assertions"],
                "file_assertions": case["file_assertions"],
                "tool_assertions": case["tool_assertions"],
                "fixtures": fixtures,
            }
        )
    atomic_json(output_dir / "evals" / "evals.json", evals)
    atomic_json(output_dir / "evals" / "trigger_queries.json", {"queries": payload["triggers"]})
    manifest = {
        "schema": "critic_eval_pack_manifest_v1",
        "skill_id": payload["skill_id"],
        "skill_type": payload["skill_type"],
        "source_file_count": len(source_files),
        "source_files": source_files,
        "source_tree_sha256": hashlib.sha256(
            json.dumps(source_files, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "author_report_sha256": author_report_sha256,
        "repair_report_sha256": repair_report_sha256,
        "reviewer_report_sha256": reviewer_report_sha256,
        "reviewer_repair_report_sha256": reviewer_repair_report_sha256,
        "native_eval_sha256": native_eval_sha256,
        "execution_mode": (
            execution_mode_review["execution_mode"]
            if execution_mode_review
            else None
        ),
        "execution_mode_review_sha256": (
            execution_mode_review["review_sha256"]
            if execution_mode_review
            else None
        ),
        "execution_mode_provider_report_sha256": (
            execution_mode_review["provider_report_sha256"]
            if execution_mode_review
            else None
        ),
        "author_rationale": payload["author_rationale"],
    }
    atomic_json(output_dir.parent / "pack_manifest.json", manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True)
    parser.add_argument("--skill-type", choices=sorted(SKILL_TYPES), required=True)
    parser.add_argument("--source-skill", type=pathlib.Path, required=True)
    parser.add_argument("--run-root", type=pathlib.Path, required=True)
    parser.add_argument("--execution-mode-review", type=pathlib.Path, required=True)
    parser.add_argument("--native-eval", type=pathlib.Path)
    parser.add_argument("--provider-report", type=pathlib.Path)
    parser.add_argument("--repair-provider-report", type=pathlib.Path)
    parser.add_argument("--review-provider-report", type=pathlib.Path)
    parser.add_argument("--review-repair-provider-report", type=pathlib.Path)
    args = parser.parse_args(argv)
    source_skill = args.source_skill.resolve()
    source_dir = source_skill.parent
    args.run_root.mkdir(parents=True, exist_ok=True)
    try:
        execution_mode_review = resolve_execution_mode_review(
            args.execution_mode_review,
            args.id,
            source_dir,
            args.skill_type,
            args.run_root,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    native_payload = (
        json.loads(args.native_eval.read_text(encoding="utf-8"))
        if args.native_eval and args.native_eval.is_file()
        else None
    )
    prompt = build_author_prompt(
        args.id,
        args.skill_type,
        native_eval=native_payload,
        source_snapshot=build_source_snapshot(source_dir),
        mode_contract=load_json(args.execution_mode_review),
    )
    prompt_path = args.run_root / "author-prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    if not args.provider_report:
        print(prompt_path)
        return 0
    report = json.loads(args.provider_report.read_text(encoding="utf-8"))
    if report.get("status") != "pass" or report.get("source_unchanged") is not True:
        raise SystemExit("author provider report did not pass source invariants")
    repair_sha = None
    try:
        payload = normalize_author_payload(
            parse_author_response(str(report.get("final_text") or ""))
        )
    except ValueError as exc:
        atomic_json(
            args.run_root / "author-validation-error.json",
            {
                "schema": "critic_eval_validation_error_v1",
                "stage": "author",
                "author_report_sha256": sha256(args.provider_report),
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        repair_prompt = build_unparseable_repair_prompt(
            args.id,
            args.skill_type,
            str(report.get("final_text") or ""),
            str(exc),
        )
        repair_prompt_path = args.run_root / "repair-prompt.txt"
        repair_prompt_path.write_text(repair_prompt, encoding="utf-8")
        if not args.repair_provider_report:
            print(repair_prompt_path)
            return 2
        payload, repair_sha = consume_single_repair_report(
            args.run_root,
            args.repair_provider_report,
            args.id,
            args.skill_type,
        )
    else:
        try:
            validate_author_payload(payload, args.id, args.skill_type)
        except ValueError as exc:
            atomic_json(args.run_root / "author-payload.invalid.json", payload)
            atomic_json(
                args.run_root / "author-validation-error.json",
                {
                    "schema": "critic_eval_validation_error_v1",
                    "stage": "author",
                    "author_report_sha256": sha256(args.provider_report),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            repair_prompt = build_repair_prompt(args.id, args.skill_type, payload, str(exc))
            repair_prompt_path = args.run_root / "repair-prompt.txt"
            repair_prompt_path.write_text(repair_prompt, encoding="utf-8")
            if not args.repair_provider_report:
                print(repair_prompt_path)
                return 2
            payload, repair_sha = consume_single_repair_report(
                args.run_root,
                args.repair_provider_report,
                args.id,
                args.skill_type,
            )
        else:
            if args.repair_provider_report:
                raise SystemExit("repair is not allowed after a valid first author response")
    atomic_json(args.run_root / "author-payload.json", payload)
    review_prompt = build_review_prompt(
        args.id,
        args.skill_type,
        payload,
        source_snapshot=build_source_snapshot(source_dir),
        mode_contract=load_json(args.execution_mode_review),
    )
    review_prompt_path = args.run_root / "review-prompt.txt"
    review_prompt_path.write_text(review_prompt, encoding="utf-8")
    if not args.review_provider_report:
        print(review_prompt_path)
        return 0
    reviewer_sha = None
    reviewer_repair_sha = None
    review_report = load_json(args.review_provider_report)
    if review_report.get("status") != "pass" or review_report.get("source_unchanged") is not True:
        raise SystemExit("review provider report did not pass source invariants")
    raw_review = parse_author_response(str(review_report.get("final_text") or ""))
    try:
        review_payload = validate_review_payload(
            raw_review, args.id, args.skill_type, payload
        )
    except ValueError as exc:
        atomic_json(args.run_root / "review-payload.invalid.json", raw_review)
        atomic_json(
            args.run_root / "review-validation-error.json",
            {
                "schema": "critic_eval_validation_error_v1",
                "stage": "review",
                "review_report_sha256": sha256(args.review_provider_report),
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        review_repair_prompt = build_review_repair_prompt(
            args.id, args.skill_type, raw_review, str(exc)
        )
        review_repair_prompt_path = args.run_root / "review-repair-prompt.txt"
        review_repair_prompt_path.write_text(review_repair_prompt, encoding="utf-8")
        if not args.review_repair_provider_report:
            print(review_repair_prompt_path)
            return 2
        review_payload, reviewer_repair_sha = consume_single_review_repair_report(
            args.run_root,
            args.review_repair_provider_report,
            raw_review,
            args.id,
            args.skill_type,
            payload,
        )
    else:
        if args.review_repair_provider_report:
            raise SystemExit("review repair is not allowed after a valid review response")
    atomic_json(args.run_root / "review-payload.json", review_payload)
    if review_payload["verdict"] == "rejected":
        raise SystemExit("eval reviewer rejected the authored pack")
    payload = review_payload["reviewed_payload"]
    reviewer_sha = sha256(args.review_provider_report)
    materialize_pack(
        source_dir,
        args.run_root / "eval_skill",
        payload,
        author_report_sha256=sha256(args.provider_report),
        native_eval_sha256=sha256(args.native_eval) if args.native_eval else None,
        reviewer_report_sha256=reviewer_sha,
        reviewer_repair_report_sha256=reviewer_repair_sha,
        repair_report_sha256=repair_sha,
        execution_mode_review=execution_mode_review,
    )
    print(args.run_root / "eval_skill")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
