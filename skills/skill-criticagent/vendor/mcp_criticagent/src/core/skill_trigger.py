"""Deterministic trigger-quality grading for recorded catalog decisions."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class TriggerQuery:
    query: str
    should_trigger: bool


@dataclass(frozen=True)
class CatalogEntry:
    name: str
    description: str
    path: str


@dataclass
class TriggerEvalResult:
    results: list[dict[str, Any]]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"results": self.results, "summary": self.summary}


class DecisionProvider(Protocol):
    def complete(self, prompt: str) -> str: ...


def _frontmatter(skill_file: Path) -> dict[str, str]:
    content = skill_file.read_text(encoding="utf-8")
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{skill_file} is missing frontmatter")
    values: dict[str, str] = {}
    block_key: str | None = None
    block_style = ""
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1].isspace():
            if block_key is not None:
                separator = "\n" if block_style.startswith("|") else " "
                values[block_key] = f"{values[block_key]}{separator}{line.strip()}".strip()
            continue
        if ":" not in line:
            continue
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
    return values


def load_catalog_entry(skill_dir: str | Path) -> CatalogEntry:
    root = Path(skill_dir)
    values = _frontmatter(root / "SKILL.md")
    name = values.get("name", "").strip()
    if not name:
        raise ValueError(f"{root}/SKILL.md has no name")
    return CatalogEntry(name=name, description=values.get("description", ""), path=str(root.resolve()))


def load_distractor_entries(root: str | Path, target_name: str) -> list[CatalogEntry]:
    base = Path(root)
    entries: list[CatalogEntry] = []
    for skill_file in sorted(base.rglob("SKILL.md")):
        try:
            entry = load_catalog_entry(skill_file.parent)
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        if entry.name != target_name:
            entries.append(entry)
    return entries


def _decision_names(raw: object) -> set[str]:
    if isinstance(raw, list):
        return {str(item).strip() for item in raw if str(item).strip()}
    text = str(raw or "").strip()
    if not text:
        return set()
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        decoded = None
    if isinstance(decoded, list):
        return {str(item).strip() for item in decoded if str(item).strip()}
    if isinstance(decoded, dict):
        candidate = decoded.get("skills") or decoded.get("decisions") or decoded.get("name")
        if isinstance(candidate, list):
            return {str(item).strip() for item in candidate if str(item).strip()}
        if candidate:
            return {str(candidate).strip()}
    return {token for token in re.split(r"[,\s]+", text) if token and token.casefold() != "none"}


def run_trigger_evals(
    skill_dir: str | Path,
    *,
    provider: DecisionProvider,
    queries: list[TriggerQuery],
    distractors: list[CatalogEntry] | None = None,
    runs_per_query: int = 1,
    threshold: float = 0.5,
) -> TriggerEvalResult:
    if runs_per_query < 1:
        raise ValueError("runs_per_query must be positive")
    if not 0 < threshold <= 1:
        raise ValueError("threshold must be in (0, 1]")
    target = load_catalog_entry(skill_dir)
    catalog = [target, *(distractors or [])]
    catalog_text = "\n".join(f"- {entry.name}: {entry.description}" for entry in catalog)

    results: list[dict[str, Any]] = []
    for query in queries:
        raw_decisions: list[str] = []
        activations: list[bool] = []
        for _ in range(runs_per_query):
            raw = str(
                provider.complete(
                    "Choose the applicable skill name from the catalog, or none.\n"
                    f"Catalog:\n{catalog_text}\n\nUser query:\n{query.query}"
                )
            )
            raw_decisions.append(raw)
            activations.append(target.name in _decision_names(raw))
        activation_rate = sum(activations) / len(activations)
        predicted = activation_rate >= threshold
        results.append(
            {
                "query": query.query,
                "should_trigger": query.should_trigger,
                "predicted_trigger": predicted,
                "activation_rate": activation_rate,
                "decisions": raw_decisions,
                "passed": predicted is query.should_trigger,
            }
        )
    passed = sum(bool(item["passed"]) for item in results)
    total = len(results)
    return TriggerEvalResult(
        results=results,
        summary={"passed": passed, "total": total, "accuracy": passed / total if total else 0.0},
    )
