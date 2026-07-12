#!/usr/bin/env python3
"""Static security scan for Agent Skill directories.

Deterministic pattern scan, no model calls. Signal sources:
aws-samples/sample-agent-skill-eval (Safety dimension: secrets, injection
surfaces, unsafe installs) and SkillLens (security as a first-class axis).
Patterns are intentionally narrow to keep false positives low on real-world
skill corpora; severity "high" findings indicate embedded secret material,
"warning" findings indicate risky instructions that deserve human review.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List

SCANNED_SUFFIXES = {
    ".md",
    ".mdx",
    ".py",
    ".sh",
    ".ps1",
    ".js",
    ".ts",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
}
MAX_SCAN_BYTES = 256 * 1024

# (name, severity, compiled pattern)
_RULES = [
    (
        "openai-style-key",
        "high",
        re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b"),
    ),
    (
        "aws-access-key",
        "high",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    (
        "github-token",
        "high",
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    ),
    (
        "private-key-block",
        "high",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ),
    (
        "hardcoded-credential",
        "high",
        re.compile(
            r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"][A-Za-z0-9_\-/+]{16,}['\"]"
        ),
    ),
    (
        "curl-pipe-shell",
        "warning",
        re.compile(r"(?i)\b(curl|wget)\b[^|\n]{0,200}\|\s*(ba|z|da)?sh\b"),
    ),
    (
        "base64-decode-exec",
        "warning",
        re.compile(r"(?i)base64\s+(-d|--decode)[^\n]{0,120}\|\s*(ba|z|da)?sh\b"),
    ),
    (
        "recursive-force-delete",
        "warning",
        re.compile(r"\brm\s+-[a-z]*rf?[a-z]*\s+(/|~)[^\s]*"),
    ),
    (
        "world-writable-chmod",
        "warning",
        re.compile(r"\bchmod\s+(-[a-zA-Z]+\s+)?0?777\b"),
    ),
    (
        "credential-exfiltration-hint",
        "warning",
        re.compile(
            r"(?i)\b(upload|send|post|exfiltrate)\b[^\n]{0,60}\b(credentials?|\.env\b|ssh[_ -]?key|api[_ -]?key)"
        ),
    ),
]


@dataclass
class SecurityFinding:
    rule: str
    severity: str  # high | warning
    path: str
    line: int
    evidence: str

    def to_dict(self) -> dict:
        return asdict(self)


def scan_skill_security(skill_dir: str | Path) -> List[SecurityFinding]:
    """Scan SKILL.md and bundled resources for embedded secrets and risky
    instructions. Returns findings sorted by severity then path."""

    root = Path(skill_dir)
    findings: List[SecurityFinding] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SCANNED_SUFFIXES:
            continue
        raw = path.read_bytes()[:MAX_SCAN_BYTES]
        if 0 in raw[:4096]:
            continue
        text = raw.decode("utf-8", errors="replace")
        relative = path.relative_to(root).as_posix()

        for line_number, line in enumerate(text.splitlines(), start=1):
            for rule, severity, pattern in _RULES:
                match = pattern.search(line)
                if match:
                    findings.append(
                        SecurityFinding(
                            rule=rule,
                            severity=severity,
                            path=relative,
                            line=line_number,
                            evidence=_redact(match.group(0)),
                        )
                    )

    findings.sort(key=lambda f: (f.severity != "high", f.path, f.line))
    return findings


def _redact(evidence: str) -> str:
    """Show enough to locate the finding without repeating secret material."""

    if len(evidence) <= 24:
        return evidence
    return evidence[:12] + "..." + evidence[-6:]
