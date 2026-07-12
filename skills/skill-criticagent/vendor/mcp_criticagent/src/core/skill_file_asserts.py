#!/usr/bin/env python3
"""Deterministic file-output assertions for skill evals.

Covers the file-side-effect observation channel of the behavior-uplift
dimension: a run's produced files (collected by the host agent or read from
an outputs directory) are graded locally, mirroring skill-creator's grader
which evaluates assertions against the run's outputs/ directory.

Reserved convention: a file named "transcript.txt" carries the run's
execution transcript, so process-quality assertions ride the same mechanism.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, List

FILE_ASSERTION_TYPES = {
    "file-exists",
    "file-not-exists",
    "file-contains",
    "file-matches",
}


@dataclass
class OutputFile:
    path: str  # posix-style relative path
    content: str


@dataclass
class FileAssertion:
    type: str
    path: str
    value: str | None = None
    pattern: str | None = None
    description: str | None = None


@dataclass
class FileGradeResult:
    text: str
    passed: bool
    evidence: str


def parse_file_assertions(value: Any, where: str) -> List[FileAssertion]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{where}.file_assertions must be an array")
    return [
        _parse_one(entry, f"{where}.file_assertions[{index}]")
        for index, entry in enumerate(value)
    ]


def _parse_one(entry: Any, where: str) -> FileAssertion:
    if not isinstance(entry, dict):
        raise ValueError(f"{where} must be an object")

    assertion_type = entry.get("type")
    if assertion_type not in FILE_ASSERTION_TYPES:
        raise ValueError(
            f"{where}.type must be one of: {', '.join(sorted(FILE_ASSERTION_TYPES))}"
        )
    path = entry.get("path")
    if not isinstance(path, str) or not path.strip():
        raise ValueError(f"{where}.path is required")

    description = (
        entry.get("description") if isinstance(entry.get("description"), str) else None
    )

    if assertion_type == "file-contains":
        if not isinstance(entry.get("value"), str):
            raise ValueError(f"{where}.value must be a string for file-contains")
        return FileAssertion(
            type=assertion_type,
            path=path.strip(),
            value=entry["value"],
            description=description,
        )
    if assertion_type == "file-matches":
        if not isinstance(entry.get("pattern"), str):
            raise ValueError(f"{where}.pattern (regex string) is required")
        return FileAssertion(
            type=assertion_type,
            path=path.strip(),
            pattern=entry["pattern"],
            description=description,
        )
    return FileAssertion(
        type=assertion_type, path=path.strip(), description=description
    )


def grade_file_assertions(
    output_files: List[OutputFile], assertions: List[FileAssertion]
) -> List[FileGradeResult]:
    files_by_path = {file.path: file for file in output_files or []}
    observed = ", ".join(sorted(files_by_path)) or "(no files)"
    return [_grade_one(a, files_by_path, observed) for a in assertions]


def _describe(assertion: FileAssertion) -> str:
    if assertion.description:
        return assertion.description
    if assertion.type == "file-exists":
        return f"output file {assertion.path} exists"
    if assertion.type == "file-not-exists":
        return f"output file {assertion.path} does NOT exist"
    if assertion.type == "file-contains":
        return f"{assertion.path} contains {assertion.value!r}"
    return f"{assertion.path} matches /{assertion.pattern}/"


def _grade_one(
    assertion: FileAssertion, files_by_path: dict, observed: str
) -> FileGradeResult:
    text = _describe(assertion)
    normalized = assertion.path.replace("\\", "/")
    file = files_by_path.get(normalized)

    if assertion.type == "file-not-exists":
        if file is None:
            return FileGradeResult(
                text, True, f"confirmed absent; observed: {observed}"
            )
        return FileGradeResult(
            text, False, f"{normalized} exists ({len(file.content)} chars)"
        )

    if file is None:
        return FileGradeResult(
            text, False, f"{normalized} not found; observed: {observed}"
        )

    if assertion.type == "file-exists":
        return FileGradeResult(
            text, True, f"{normalized} present ({len(file.content)} chars)"
        )

    if assertion.type == "file-contains":
        if assertion.value.lower() in file.content.lower():
            return FileGradeResult(
                text, True, f"{normalized} contains the expected text"
            )
        return FileGradeResult(
            text, False, f"{normalized} does not contain {assertion.value!r}"
        )

    # file-matches
    try:
        matched = re.search(assertion.pattern or "", file.content)
    except re.error as exc:
        return FileGradeResult(
            text, False, f"invalid regex /{assertion.pattern}/: {exc}"
        )
    if matched:
        return FileGradeResult(
            text, True, f"{normalized} matches at offset {matched.start()}"
        )
    return FileGradeResult(
        text, False, f"{normalized} does not match /{assertion.pattern}/"
    )


def read_outputs_dir(directory) -> List[OutputFile]:
    """Read a run's outputs directory into OutputFile records (text only)."""

    from pathlib import Path

    root = Path(directory)
    if not root.is_dir():
        return []
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        raw = path.read_bytes()
        if 0 in raw[:4096]:
            content = f"<binary {len(raw)} bytes>"
        else:
            content = raw.decode("utf-8", errors="replace")
        files.append(
            OutputFile(path=path.relative_to(root).as_posix(), content=content)
        )
    return files
