#!/usr/bin/env python3
"""Static validation for Agent Skills directories."""

from __future__ import annotations

import ast
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.core.skill_security import scan_skill_security


ALLOWED_FRONTMATTER_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
MAX_SKILL_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_COMPATIBILITY_LENGTH = 500
REFERENCE_PATTERN = re.compile(
    r"(?P<path>(?:scripts|references|assets)/[A-Za-z0-9._/\-]+)"
)
IGNORED_DISCOVERY_DIRS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}


@dataclass
class SkillValidationResult:
    """Result of static Agent Skill validation."""

    path: str
    valid: bool
    name: str | None = None
    description: str | None = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SkillCollectionValidationResult:
    """Aggregated validation result for a directory containing many skills."""

    path: str
    valid: bool
    total_skills: int
    valid_count: int
    invalid_count: int
    skills: List[SkillValidationResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def validate_skill_dir(
    skill_dir: str | Path, strict: bool = True
) -> SkillValidationResult:
    """Validate a local Agent Skill directory without requiring model/API access."""

    root = Path(skill_dir)
    errors: List[str] = []
    warnings: List[str] = []
    skill_md = root / "SKILL.md"

    if not root.exists():
        return SkillValidationResult(
            path=str(root),
            valid=False,
            errors=[f"Skill directory does not exist: {root}"],
            summary=_empty_summary(),
        )

    if not root.is_dir():
        return SkillValidationResult(
            path=str(root),
            valid=False,
            errors=[f"Skill path is not a directory: {root}"],
            summary=_empty_summary(),
        )

    if not skill_md.exists():
        return SkillValidationResult(
            path=str(root),
            valid=False,
            errors=["Missing required file: SKILL.md"],
            summary=_empty_summary(),
        )

    content = skill_md.read_text(encoding="utf-8")
    metadata, body, has_frontmatter, parse_errors = _parse_frontmatter(content)
    errors.extend(parse_errors)

    if strict and not has_frontmatter:
        errors.append("SKILL.md must start with YAML frontmatter")

    if strict:
        errors.extend(_validate_frontmatter(metadata, root))

    referenced_files = _find_referenced_files(body)
    for relative_path in referenced_files:
        if not (root / relative_path).exists():
            errors.append(f"Referenced file does not exist: {relative_path}")

    script_errors, script_warnings = _check_scripts_health(root)
    errors.extend(script_errors)
    warnings.extend(script_warnings)

    security_findings = scan_skill_security(root)
    for finding in security_findings:
        message = (
            f"Security ({finding.rule}) at {finding.path}:{finding.line}: "
            f"{finding.evidence}"
        )
        if finding.severity == "high":
            errors.append(message)
        else:
            warnings.append(message)

    summary = {
        "skill_md_lines": len(content.splitlines()),
        "referenced_files": referenced_files,
        "scripts_count": _count_files(root / "scripts"),
        "references_count": _count_files(root / "references"),
        "assets_count": _count_files(root / "assets"),
        "security_findings": [finding.to_dict() for finding in security_findings],
    }

    if summary["skill_md_lines"] > 500:
        warnings.append(
            "SKILL.md is over 500 lines; consider moving detail into references/"
        )

    return SkillValidationResult(
        path=str(root),
        valid=not errors,
        name=_string_value(metadata.get("name")),
        description=_string_value(metadata.get("description")),
        errors=errors,
        warnings=warnings,
        summary=summary,
    )


def _check_scripts_health(root: Path) -> Tuple[List[str], List[str]]:
    """Resource-resolution station of the loading pipeline: bundled scripts
    must at least be parseable, otherwise activation-time execution fails."""

    errors: List[str] = []
    warnings: List[str] = []
    scripts_dir = root / "scripts"
    if not scripts_dir.is_dir():
        return errors, warnings

    for path in sorted(scripts_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        raw = path.read_bytes()
        if not raw.strip():
            warnings.append(f"Script is empty: {relative}")
            continue
        if path.suffix.lower() == ".py":
            try:
                ast.parse(raw.decode("utf-8", errors="replace"), filename=relative)
            except SyntaxError as exc:
                errors.append(
                    f"Script has a Python syntax error: {relative} "
                    f"(line {exc.lineno}: {exc.msg})"
                )
    return errors, warnings


def discover_skill_dirs(root_dir: str | Path) -> List[Path]:
    """Find skill directories under root_dir, skipping dependency/cache folders."""

    root = Path(root_dir)
    if not root.exists() or not root.is_dir():
        return []

    if (root / "SKILL.md").exists():
        return [root]

    skill_dirs = []
    for skill_md in root.rglob("SKILL.md"):
        if _is_ignored_path(skill_md.relative_to(root)):
            continue
        skill_dirs.append(skill_md.parent)

    return sorted(skill_dirs, key=lambda path: path.as_posix())


def validate_skill_collection(
    root_dir: str | Path, strict: bool = True
) -> SkillCollectionValidationResult:
    """Validate every discovered skill under root_dir."""

    root = Path(root_dir)
    if not root.exists():
        return SkillCollectionValidationResult(
            path=str(root),
            valid=False,
            total_skills=0,
            valid_count=0,
            invalid_count=0,
            errors=[f"Skill collection path does not exist: {root}"],
        )

    if not root.is_dir():
        return SkillCollectionValidationResult(
            path=str(root),
            valid=False,
            total_skills=0,
            valid_count=0,
            invalid_count=0,
            errors=[f"Skill collection path is not a directory: {root}"],
        )

    skills = [
        validate_skill_dir(path, strict=strict) for path in discover_skill_dirs(root)
    ]
    valid_count = sum(1 for skill in skills if skill.valid)
    invalid_count = len(skills) - valid_count

    return SkillCollectionValidationResult(
        path=str(root),
        valid=bool(skills) and invalid_count == 0,
        total_skills=len(skills),
        valid_count=valid_count,
        invalid_count=invalid_count,
        skills=skills,
        errors=[] if skills else ["No Agent Skill directories found"],
    )


def _parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str, bool, List[str]]:
    if not content.startswith("---"):
        return {}, content, False, []

    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, content, False, []

    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break

    if end_index is None:
        return {}, content, False, ["SKILL.md frontmatter is not closed with ---"]

    metadata, errors = _parse_simple_yaml(lines[1:end_index])
    body = "\n".join(lines[end_index + 1 :])
    return metadata, body, True, errors


BLOCK_SCALAR_PATTERN = re.compile(r"^[>|][+-]?$")


def _parse_simple_yaml(lines: List[str]) -> Tuple[Dict[str, Any], List[str]]:
    metadata: Dict[str, Any] = {}
    errors: List[str] = []
    current_mapping_key: str | None = None
    index = 0

    while index < len(lines):
        raw_line = lines[index]
        line_number = index + 2
        index += 1

        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        if raw_line.startswith((" ", "\t")):
            if current_mapping_key is None:
                errors.append(
                    f"Unsupported frontmatter indentation at line {line_number}"
                )
                continue
            key, value = _split_key_value(raw_line.strip(), line_number, errors)
            if key:
                metadata.setdefault(current_mapping_key, {})[key] = value
            continue

        key, value = _split_key_value(raw_line, line_number, errors)
        if not key:
            continue

        if isinstance(value, str) and BLOCK_SCALAR_PATTERN.match(value):
            block_lines = []
            while index < len(lines) and (
                not lines[index].strip() or lines[index].startswith((" ", "\t"))
            ):
                block_lines.append(lines[index].strip())
                index += 1
            joiner = " " if value.startswith(">") else "\n"
            metadata[key] = joiner.join(line for line in block_lines if line)
            current_mapping_key = None
        elif value == "":
            metadata[key] = {}
            current_mapping_key = key
        else:
            metadata[key] = value
            current_mapping_key = None

    return metadata, errors


def _split_key_value(line: str, line_number: int, errors: List[str]) -> Tuple[str, Any]:
    if ":" not in line:
        errors.append(f"Invalid frontmatter line {line_number}: {line}")
        return "", None

    key, value = line.split(":", 1)
    key = key.strip()
    value = value.strip()

    if not key:
        errors.append(f"Invalid frontmatter key at line {line_number}")
        return "", None

    return key, _unquote(value)


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _validate_frontmatter(metadata: Dict[str, Any], skill_dir: Path) -> List[str]:
    errors: List[str] = []

    extra_fields = sorted(set(metadata) - ALLOWED_FRONTMATTER_FIELDS)
    if extra_fields:
        errors.append(f"Unexpected fields in frontmatter: {', '.join(extra_fields)}")

    if "name" not in metadata:
        errors.append("Missing required field in frontmatter: name")
    else:
        errors.extend(_validate_name(metadata["name"], skill_dir))

    if "description" not in metadata:
        errors.append("Missing required field in frontmatter: description")
    else:
        errors.extend(_validate_description(metadata["description"]))

    if "compatibility" in metadata:
        compatibility = metadata["compatibility"]
        if not isinstance(compatibility, str) or not compatibility.strip():
            errors.append(
                "Field 'compatibility' must be a non-empty string when provided"
            )
        elif len(compatibility) > MAX_COMPATIBILITY_LENGTH:
            errors.append("Field 'compatibility' exceeds 500 character limit")

    if "metadata" in metadata and not isinstance(metadata["metadata"], dict):
        errors.append("Field 'metadata' must be a mapping when provided")

    return errors


def _validate_name(name: Any, skill_dir: Path) -> List[str]:
    errors: List[str] = []
    if not isinstance(name, str) or not name.strip():
        return ["Field 'name' must be a non-empty string"]

    normalized = unicodedata.normalize("NFKC", name.strip())
    if len(normalized) > MAX_SKILL_NAME_LENGTH:
        errors.append(
            f"Skill name '{normalized}' exceeds {MAX_SKILL_NAME_LENGTH} character limit"
        )
    if normalized != normalized.lower():
        errors.append(f"Skill name '{normalized}' must be lowercase")
    if normalized.startswith("-") or normalized.endswith("-"):
        errors.append("Skill name cannot start or end with a hyphen")
    if "--" in normalized:
        errors.append("Skill name cannot contain consecutive hyphens")
    if not all(char.isalnum() or char == "-" for char in normalized):
        errors.append(
            f"Skill name '{normalized}' contains invalid characters. "
            "Use lowercase letters, numbers, and hyphens only."
        )

    directory_name = unicodedata.normalize("NFKC", skill_dir.name)
    if directory_name != normalized:
        errors.append(
            f"Directory name '{skill_dir.name}' must match skill name '{normalized}'"
        )

    return errors


def _validate_description(description: Any) -> List[str]:
    if not isinstance(description, str) or not description.strip():
        return ["Field 'description' must be a non-empty string"]
    if len(description) > MAX_DESCRIPTION_LENGTH:
        return [
            f"Field 'description' exceeds {MAX_DESCRIPTION_LENGTH} character limit "
            f"({len(description)} chars)"
        ]
    return []


def _find_referenced_files(body: str) -> List[str]:
    seen = set()
    paths: List[str] = []
    for match in REFERENCE_PATTERN.finditer(body):
        relative_path = match.group("path").rstrip(".,);]")
        if relative_path not in seen:
            seen.add(relative_path)
            paths.append(relative_path)
    return paths


def _count_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for child in path.rglob("*") if child.is_file())


def _is_ignored_path(relative_path: Path) -> bool:
    return any(part in IGNORED_DISCOVERY_DIRS for part in relative_path.parts)


def _string_value(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _empty_summary() -> Dict[str, Any]:
    return {
        "skill_md_lines": 0,
        "referenced_files": [],
        "scripts_count": 0,
        "references_count": 0,
        "assets_count": 0,
        "security_findings": [],
    }
