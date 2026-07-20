#!/usr/bin/env python3
"""Create and validate source-backed CriticAgent execution-mode reviews."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import pathlib
import re
from typing import Any


SCHEMA = "critic_execution_mode_review_v1"
MODES = {"guidance", "artifact", "tool", "hybrid"}
OBSERVED_MODES = {"guidance", "artifact", "tool"}
OUTPUT_KINDS = {
    "guidance": "conversation",
    "artifact": "file",
    "tool": "tool_result",
    "hybrid": "mixed",
}
EVIDENCE_PURPOSES = {"primary_output", "runtime", "side_effect", "boundary"}


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_manifest(root: pathlib.Path) -> list[dict[str, Any]]:
    root = root.resolve()
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


def build_source_snapshot(root: pathlib.Path, max_text_bytes: int = 262_144) -> str:
    root = root.resolve()
    if not (root / "SKILL.md").is_file():
        raise ValueError("source package requires SKILL.md")
    sections: list[str] = []
    total = 0
    for item in tree_manifest(root):
        path = root / pathlib.PurePosixPath(item["path"])
        raw = path.read_bytes()
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            content = "[binary file: content omitted; hash and size retained]"
        else:
            total += len(raw)
            if total > max_text_bytes:
                raise ValueError(
                    f"source text exceeds snapshot limit ({max_text_bytes} bytes)"
                )
            content = "\n".join(
                f"{line_number:05d}|{line}"
                for line_number, line in enumerate(content.splitlines(), 1)
            )
        sections.append(
            f"FILE: {item['path']}\nSHA256: {item['sha256']}\n"
            f"SIZE: {item['size']}\nCONTENT:\n{content.rstrip()}"
        )
    return "\n\n---\n\n".join(sections)


def atomic_json(path: pathlib.Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.S | re.I)
    candidate = fenced.group(1) if fenced else stripped[stripped.find("{") : stripped.rfind("}") + 1]
    payload = json.loads(candidate)
    if not isinstance(payload, dict):
        raise ValueError("execution-mode response must be a JSON object")
    return payload


def build_review_prompt(skill_id: str, source_root: pathlib.Path) -> str:
    manifest = tree_manifest(source_root)
    source_hash = manifest_sha256(manifest)
    snapshot = build_source_snapshot(source_root)
    return f"""You are the source-review stage of Skill-CriticAgent.
Your first action must call the mounted Skill tool exactly once. Do not begin
classification or analysis before that tool call succeeds. Do not analyze the
embedded source snapshot before that call returns; use the snapshot afterward
only to verify the complete package, hashes, and exact line evidence.

Classify the skill by its primary user-visible delivery semantics, not its name,
directory, agent/toolkit/API/workflow implementation form, or research taxonomy.

- guidance: the primary deliverable is conversational advice or analysis and the
  documented normal path requires neither a tool call nor a file modification.
- artifact: the primary deliverable requires creating or modifying one or more files.
- tool: the primary deliverable requires a named runtime/tool/API call, while a file
  is not the main user deliverable.
- hybrid: at least two of guidance, artifact, and tool are genuine primary delivery
  modes, rather than an optional convenience or fallback.

A stop/fallback message does not turn a tool-dependent or artifact-producing normal
path into guidance. Classify the documented successful primary path; record fallback
behavior as boundary evidence. A conversational explanation accompanying a required
file or tool result is not a second primary mode by itself.
Derive the mode from the required successful path: artifact only => artifact; tool
only => tool; artifact + tool => hybrid; conversation only => guidance. Include
guidance in observed_modes only when conversation is itself an independent primary
deliverable. List required primary-path side effects only; describe optional saves
or failure-path behavior in boundary evidence instead.

Read the complete hash-backed source below. Examine documented outputs, procedures,
commands, required runtimes, failure modes, and side effects. Every conclusion must
cite a source file, its SHA-256, and an exact inclusive line range. The validator
materializes the exact excerpt from those immutable lines. If the
source is contradictory or insufficient, set review_status to needs_mode_review,
execution_mode to null, confidence to low, and explain the uncertainty. Do not guess.

Return strict JSON only with schema {SCHEMA} and these keys:
schema, skill_id, source_tree_sha256, review_status, execution_mode,
observed_modes, confidence, primary_output, required_runtime, side_effects,
evidence, rationale.

Use the contract literally, without aliases or pluralized enum values:
- review_status must be exactly "source_reviewed" or "needs_mode_review".
- execution_mode must be exactly one of "guidance", "artifact", "tool", "hybrid",
  or null only when review_status is "needs_mode_review".
- observed_modes must be a JSON array containing only "guidance", "artifact", or
  "tool". required_runtime and side_effects must always be JSON arrays of strings;
  use [] when none. Never return null or a prose string for these array fields.
- Every evidence object returned by the model must contain path, sha256, line_start,
  line_end, and supports. line_start and line_end are one-based inclusive integers.
  Do not copy source prose into the JSON. The validator will use the key `excerpt`
  exactly when it materializes the cited lines. Its supports value must be exactly
  primary_output, runtime, side_effect, or boundary. The resulting exact excerpt is
  one contiguous source span: no ellipsis, paraphrase, or merged lines. Prefer a
  single complete source line that directly proves the claim.
- guidance must use primary_output.kind "conversation"; artifact must use "file";
  tool must use "tool_result"; hybrid must use primary_output.kind "mixed".

For source_reviewed, execution_mode is guidance/artifact/tool/hybrid; confidence is
high or medium; primary_output is an object with kind and description; evidence has
at least two items. Each evidence item has path, sha256, line_start, line_end, and supports
(primary_output/runtime/side_effect/boundary). observed_modes contains only
guidance/artifact/tool. Use conversation/file/tool_result/mixed as the primary output
kind corresponding to the selected execution mode. For needs_mode_review, do not
invent a mode or primary output.

Skill ID: {skill_id}
Source tree SHA-256: {source_hash}

Hash-backed source package:
{snapshot}
"""


def build_repair_prompt(
    skill_id: str,
    source_root: pathlib.Path,
    invalid_response: Any,
    validation_error: str,
) -> str:
    return f"""You are repairing one source-backed execution-mode review after a
deterministic validator rejected it. This is the only repair attempt. Preserve
the original classification unless the hash-backed source proves it wrong.
Correct only the reported validation defect and any directly dependent fields.
Do not weaken the schema, omit evidence, invent source text, or paraphrase an
evidence excerpt. Every excerpt must be one exact contiguous source span.
Your first action must call the mounted Skill tool exactly once. Do not begin
repair or analysis before that tool call succeeds. Do not analyze the embedded
source snapshot before that call returns.

Skill ID: {skill_id}
Validator error: {validation_error}

Invalid payload:
{json.dumps(invalid_response, ensure_ascii=False, indent=2)}

Hash-backed source package:
{build_source_snapshot(source_root)}

Return one complete corrected {SCHEMA} object as strict JSON only.
"""


def _string_list(value: Any, where: str) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ValueError(f"{where} must be an array of non-empty strings")
    return value


def materialize_line_evidence(
    payload: dict[str, Any],
    source_root: pathlib.Path,
) -> dict[str, Any]:
    """Resolve model-selected line anchors into exact source excerpts."""
    normalized = copy.deepcopy(payload)
    evidence = normalized.get("evidence")
    if not isinstance(evidence, list):
        return normalized
    source_root = source_root.resolve()
    for index, item in enumerate(evidence):
        if not isinstance(item, dict) or item.get("excerpt"):
            continue
        relative = str(item.get("path") or "").replace("\\", "/")
        pure = pathlib.PurePosixPath(relative)
        if not relative or pure.is_absolute() or ".." in pure.parts:
            continue
        path = (source_root / pathlib.Path(*pure.parts)).resolve()
        try:
            path.relative_to(source_root)
        except ValueError:
            continue
        if not path.is_file():
            continue
        start = item.get("line_start")
        end = item.get("line_end")
        lines = path.read_text(encoding="utf-8").splitlines()
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or start < 1
            or end < start
            or end > len(lines)
        ):
            raise ValueError(f"evidence[{index}] line range is invalid")
        item["excerpt"] = "\n".join(lines[start - 1 : end])
    return normalized


def validate_review_payload(
    payload: dict[str, Any],
    skill_id: str,
    source_root: pathlib.Path,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    payload = materialize_line_evidence(payload, source_root)
    manifest = tree_manifest(source_root)
    if payload.get("schema") != SCHEMA or payload.get("skill_id") != skill_id:
        raise ValueError("execution-mode review identity or schema is invalid")
    if payload.get("source_tree_sha256") != manifest_sha256(manifest):
        raise ValueError("execution-mode review source tree hash does not match")

    status = payload.get("review_status")
    if status not in {"source_reviewed", "needs_mode_review"}:
        raise ValueError("review_status is invalid")
    confidence = payload.get("confidence")
    if confidence not in {"high", "medium", "low"}:
        raise ValueError("confidence is invalid")
    rationale = payload.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("rationale is required")

    required_runtime = _string_list(payload.get("required_runtime"), "required_runtime")
    side_effects = _string_list(payload.get("side_effects"), "side_effects")
    observed_modes = _string_list(payload.get("observed_modes"), "observed_modes")
    if len(observed_modes) != len(set(observed_modes)) or not set(observed_modes).issubset(OBSERVED_MODES):
        raise ValueError("observed_modes contains duplicates or unsupported modes")

    evidence = payload.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("at least one source evidence item is required")
    if status == "source_reviewed" and len(evidence) < 2:
        raise ValueError("source_reviewed requires at least two evidence items")
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            raise ValueError(f"evidence[{index}] must be an object")
        relative = str(item.get("path") or "").replace("\\", "/")
        pure = pathlib.PurePosixPath(relative)
        if not relative or pure.is_absolute() or ".." in pure.parts:
            raise ValueError(f"evidence[{index}].path is unsafe")
        path = (source_root / pathlib.Path(*pure.parts)).resolve()
        try:
            path.relative_to(source_root)
        except ValueError as exc:
            raise ValueError(f"evidence[{index}].path escapes source") from exc
        if not path.is_file() or item.get("sha256") != sha256(path):
            raise ValueError(f"evidence[{index}] file or SHA-256 does not match")
        excerpt = item.get("excerpt")
        if not isinstance(excerpt, str) or not excerpt.strip():
            raise ValueError(f"evidence[{index}].excerpt is required")
        try:
            source_text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"evidence[{index}] cannot cite binary content") from exc
        if excerpt not in source_text:
            raise ValueError(f"evidence[{index}] excerpt is not present in source")
        if item.get("supports") not in EVIDENCE_PURPOSES:
            raise ValueError(f"evidence[{index}].supports is invalid")

    mode = payload.get("execution_mode")
    primary = payload.get("primary_output")
    if status == "needs_mode_review":
        if mode is not None or primary is not None or confidence != "low":
            raise ValueError("needs_mode_review must not guess a mode or primary output")
        return payload

    if mode not in MODES or confidence == "low":
        raise ValueError("source_reviewed requires a supported mode and non-low confidence")
    if not isinstance(primary, dict):
        raise ValueError("primary_output must be an object")
    if primary.get("kind") != OUTPUT_KINDS[mode]:
        raise ValueError("primary_output.kind conflicts with execution_mode")
    if not isinstance(primary.get("description"), str) or not primary["description"].strip():
        raise ValueError("primary_output.description is required")
    if mode == "guidance" and required_runtime:
        raise ValueError("guidance mode cannot require runtime dependencies")
    if mode == "guidance" and side_effects:
        raise ValueError("guidance mode cannot declare side effects")
    if mode == "artifact" and ("artifact" not in observed_modes or not side_effects):
        raise ValueError("artifact mode requires artifact evidence and file side effects")
    if mode == "tool" and ("tool" not in observed_modes or not required_runtime):
        raise ValueError("tool mode requires tool evidence and runtime dependencies")
    if mode == "hybrid" and len(set(observed_modes)) < 2:
        raise ValueError("hybrid mode requires at least two observed delivery modes")
    return payload


def write_validated_review(
    skill_id: str,
    source_root: pathlib.Path,
    provider_report: pathlib.Path,
    output: pathlib.Path,
) -> dict[str, Any]:
    report = json.loads(provider_report.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError("provider report must be an object")
    if report.get("status") != "pass" or report.get("source_unchanged") is not True:
        raise ValueError("provider report did not pass source invariants")
    payload: dict[str, Any] | None = None
    try:
        payload = extract_json(str(report.get("final_text") or ""))
        validate_review_payload(payload, skill_id, source_root)
    except (ValueError, json.JSONDecodeError) as exc:
        if payload is not None:
            atomic_json(output.parent / "execution-mode-payload.invalid.json", payload)
        invalid_response: Any = payload
        if invalid_response is None:
            invalid_response = {
                "unparsed_response": str(report.get("final_text") or "")
            }
        (output.parent / "execution-mode-repair-prompt.txt").write_text(
            build_repair_prompt(
                skill_id, source_root, invalid_response, str(exc)
            ),
            encoding="utf-8",
        )
        atomic_json(
            output.parent / "execution-mode-validation-error.json",
            {
                "schema": "critic_execution_mode_validation_error_v1",
                "skill_id": skill_id,
                "provider_report_sha256": sha256(provider_report),
                "source_tree_sha256": manifest_sha256(tree_manifest(source_root)),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "disposition": "staged_fix_first",
            },
        )
        raise
    stored = dict(payload)
    stored["provider_report_sha256"] = sha256(provider_report)
    atomic_json(output, stored)
    return stored


def consume_single_repair_report(
    skill_id: str,
    source_root: pathlib.Path,
    run_root: pathlib.Path,
    provider_report: pathlib.Path,
) -> dict[str, Any]:
    marker = run_root / "execution-mode-repair-attempt.json"
    report_sha = sha256(provider_report)
    if marker.is_file():
        prior = json.loads(marker.read_text(encoding="utf-8"))
        if prior.get("provider_report_sha256") != report_sha:
            raise ValueError("execution-mode repair attempt was already consumed")
    else:
        atomic_json(
            marker,
            {
                "schema": "critic_execution_mode_repair_attempt_v1",
                "attempt_count": 1,
                "provider_report_sha256": report_sha,
            },
        )
    report = json.loads(provider_report.read_text(encoding="utf-8"))
    if report.get("status") != "pass" or report.get("source_unchanged") is not True:
        raise ValueError("execution-mode repair provider report did not pass source invariants")
    try:
        payload = extract_json(str(report.get("final_text") or ""))
        validate_review_payload(payload, skill_id, source_root)
    except (ValueError, json.JSONDecodeError) as exc:
        atomic_json(
            run_root / "execution-mode-repair-validation-error.json",
            {
                "schema": "critic_execution_mode_repair_validation_error_v1",
                "skill_id": skill_id,
                "provider_report_sha256": report_sha,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "disposition": "staged_fix_first",
            },
        )
        raise
    stored = dict(payload)
    stored["provider_report_sha256"] = report_sha
    stored["repair_attempt_count"] = 1
    atomic_json(run_root / "execution-mode-review.json", stored)
    return stored


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True)
    parser.add_argument("--source-skill", type=pathlib.Path, required=True)
    parser.add_argument("--run-root", type=pathlib.Path, required=True)
    parser.add_argument("--provider-report", type=pathlib.Path)
    parser.add_argument("--repair-provider-report", type=pathlib.Path)
    args = parser.parse_args(argv)
    source_root = args.source_skill.resolve().parent
    args.run_root.mkdir(parents=True, exist_ok=True)
    prompt_path = args.run_root / "execution-mode-prompt.txt"
    prompt_path.write_text(build_review_prompt(args.id, source_root), encoding="utf-8")
    if args.repair_provider_report:
        consume_single_repair_report(
            args.id,
            source_root,
            args.run_root,
            args.repair_provider_report,
        )
        print(args.run_root / "execution-mode-review.json")
        return 0
    if not args.provider_report:
        print(prompt_path)
        return 0
    output = args.run_root / "execution-mode-review.json"
    write_validated_review(args.id, source_root, args.provider_report, output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
