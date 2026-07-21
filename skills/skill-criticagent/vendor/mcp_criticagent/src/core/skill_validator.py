"""Static, dependency-free validation for an Agent Skill directory."""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


MAX_FILES = 2_000
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".sh",
    ".ps1",
}
SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    (
        "assigned_secret",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"]"
            r"(?!\s*(?:example|placeholder|changeme|your[-_ ]|<))[^'\"\s]{12,}['\"]"
        ),
    ),
)


@dataclass
class ValidationResult:
    valid: bool
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "summary": self.summary,
        }


def _finding(code: str, message: str, path: str, *, severity: str = "error") -> dict[str, str]:
    return {"code": code, "message": message, "path": path, "severity": severity}


def _frontmatter(markdown: str) -> tuple[dict[str, str], str | None]:
    lines = markdown.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, "SKILL.md must start with YAML frontmatter"
    try:
        closing = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return {}, "SKILL.md frontmatter is not closed"

    values: dict[str, str] = {}
    block_key: str | None = None
    block_style = ""
    for line in lines[1:closing]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1].isspace():
            if block_key is None:
                continue
            separator = "\n" if block_style.startswith("|") else " "
            values[block_key] = f"{values[block_key]}{separator}{line.strip()}".strip()
            continue
        if ":" not in line:
            return {}, f"invalid frontmatter line: {line.strip()}"
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if re.fullmatch(r"[|>][+-]?", value):
            values[key] = ""
            block_key = key
            block_style = value
        else:
            values[key] = value.strip("'\"")
            block_key = None
            block_style = ""
    return values, None


def _is_within(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root)
        return True
    except (OSError, ValueError):
        return False


def validate_skill_dir(skill_dir: str | Path, *, strict: bool = False) -> ValidationResult:
    root = Path(skill_dir).expanduser().resolve()
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    security_findings: list[dict[str, Any]] = []
    checked_files = 0
    total_bytes = 0

    if not root.is_dir():
        errors.append(_finding("skill_dir_missing", "Skill directory does not exist", str(root)))
        return ValidationResult(False, errors, warnings, {"security_findings": []})

    skill_file = root / "SKILL.md"
    if not skill_file.is_file():
        errors.append(_finding("skill_md_missing", "SKILL.md is required", "SKILL.md"))
    else:
        try:
            markdown = skill_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(_finding("skill_md_encoding", "SKILL.md must be UTF-8", "SKILL.md"))
        else:
            meta, frontmatter_error = _frontmatter(markdown)
            if frontmatter_error:
                errors.append(_finding("frontmatter_invalid", frontmatter_error, "SKILL.md"))
            else:
                name = meta.get("name", "")
                description = meta.get("description", "")
                if not NAME_RE.fullmatch(name):
                    errors.append(_finding("name_invalid", "name must use lowercase kebab-case", "SKILL.md"))
                if strict and name and name != root.name:
                    errors.append(
                        _finding("name_mismatch", f"frontmatter name {name!r} must match directory {root.name!r}", "SKILL.md")
                    )
                if not description:
                    errors.append(_finding("description_missing", "description is required", "SKILL.md"))

    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            if not _is_within(root, path):
                finding = _finding("symlink_escape", "symlink resolves outside the Skill directory", relative, severity="high")
                errors.append(finding)
                security_findings.append(finding)
            continue
        if not path.is_file():
            continue
        checked_files += 1
        if checked_files > MAX_FILES:
            errors.append(_finding("file_count_limit", f"Skill contains more than {MAX_FILES} files", relative))
            break
        size = path.stat().st_size
        total_bytes += size
        if size > MAX_FILE_BYTES:
            errors.append(_finding("file_size_limit", "file exceeds the per-file size limit", relative))
            continue
        if total_bytes > MAX_TOTAL_BYTES:
            errors.append(_finding("total_size_limit", "Skill exceeds the total size limit", relative))
            break
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name != "SKILL.md":
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            warnings.append(_finding("non_utf8_text", "text-like file is not UTF-8", relative, severity="warning"))
            continue
        for code, pattern in SECRET_PATTERNS:
            for line in content.splitlines():
                if pattern.search(line):
                    finding = _finding(code, "possible embedded credential or private key", relative, severity="high")
                    errors.append(finding)
                    security_findings.append(finding)
                    break
        if path.suffix.lower() == ".py":
            try:
                ast.parse(content, filename=relative)
            except SyntaxError as exc:
                errors.append(_finding("python_syntax", f"Python syntax error: {exc.msg}", relative))
        elif path.suffix.lower() == ".json":
            try:
                json.loads(content)
            except json.JSONDecodeError as exc:
                errors.append(_finding("json_syntax", f"JSON syntax error: {exc.msg}", relative))

    summary = {
        "checked_files": checked_files,
        "total_bytes": total_bytes,
        "security_findings": security_findings,
    }
    return ValidationResult(not errors, errors, warnings, summary)
