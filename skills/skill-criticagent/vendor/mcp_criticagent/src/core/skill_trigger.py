#!/usr/bin/env python3
"""Trigger-accuracy evaluation for Agent Skill descriptions.

Methodology follows agentskills docs (`optimizing-descriptions.mdx`) and the
aggregation logic of anthropics/skills skill-creator `scripts/run_eval.py`:
each query runs N times, producing a trigger_rate; should-trigger queries pass
when trigger_rate >= threshold, should-not-trigger queries pass when it is
below. The skill catalog shown to the model uses the official
`<available_skills>` format from `client-implementation/adding-skills-support.mdx`.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List

from src.core.skill_validator import discover_skill_dirs


@dataclass
class TriggerQuery:
    query: str
    should_trigger: bool


@dataclass
class SkillCatalogEntry:
    name: str
    description: str


@dataclass
class TriggerQueryResult:
    query: str
    should_trigger: bool
    triggers: int
    runs: int
    trigger_rate: float
    passed: bool


@dataclass
class TriggerEvalResult:
    skill_path: str
    skill_name: str
    total_queries: int
    runs_per_query: int
    threshold: float
    results: List[TriggerQueryResult] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def load_trigger_queries(path: str | Path) -> List[TriggerQuery]:
    """Load a skill-creator style eval set: [{query, should_trigger}, ...]."""

    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict) and isinstance(raw.get("queries"), list):
        raw = raw["queries"]
    if not isinstance(raw, list):
        raise ValueError("Trigger eval set must be a JSON array of query objects")

    queries = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"queries[{index}] must be an object")
        query = entry.get("query")
        should_trigger = entry.get("should_trigger")
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"queries[{index}].query must be a non-empty string")
        if not isinstance(should_trigger, bool):
            raise ValueError(f"queries[{index}].should_trigger must be a boolean")
        queries.append(TriggerQuery(query=query, should_trigger=should_trigger))

    if not queries:
        raise ValueError("Trigger eval set contains no queries")
    return queries


def load_catalog_entry(skill_dir: str | Path) -> SkillCatalogEntry:
    skill_md = Path(skill_dir) / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"Missing required file: {skill_md}")

    metadata = _parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    return SkillCatalogEntry(
        name=metadata.get("name") or Path(skill_dir).name,
        description=metadata.get("description") or "",
    )


def load_distractor_entries(
    root: str | Path, exclude_name: str
) -> List[SkillCatalogEntry]:
    """Collect sibling skills as catalog distractors, excluding the target."""

    entries = []
    for skill_dir in discover_skill_dirs(root):
        try:
            entry = load_catalog_entry(skill_dir)
        except (FileNotFoundError, UnicodeDecodeError):
            continue
        if entry.name != exclude_name:
            entries.append(entry)
    return entries


def build_skill_catalog(entries: List[SkillCatalogEntry]) -> str:
    """Render the official <available_skills> catalog block."""

    parts = ["<available_skills>"]
    for entry in entries:
        parts.extend(
            [
                "  <skill>",
                f"    <name>{_escape_xml(entry.name)}</name>",
                f"    <description>{_escape_xml(entry.description)}</description>",
                "  </skill>",
            ]
        )
    parts.append("</available_skills>")
    return "\n".join(parts)


def render_trigger_prompt(catalog: str, query: str) -> str:
    return (
        "The following skills provide specialized instructions for specific "
        "tasks. When a task matches a skill's description, you would activate "
        "that skill before answering.\n\n"
        f"{catalog}\n\n"
        "Decide which skill, if any, you would activate for the user request "
        "below. Reply with only the skill name, or the word none if no skill "
        "applies. Do not answer the request itself.\n\n"
        f"---USER REQUEST---\n{query}"
    )


def detect_triggered(output: str, skill_name: str) -> bool:
    return skill_name.lower() in output.lower()


def run_trigger_evals(
    skill_dir: str | Path,
    provider,
    queries: List[TriggerQuery],
    distractors: List[SkillCatalogEntry] | None = None,
    runs_per_query: int = 3,
    threshold: float = 0.5,
) -> TriggerEvalResult:
    """Evaluate whether the skill's description triggers on the right queries."""

    target = load_catalog_entry(skill_dir)
    catalog = build_skill_catalog([target, *(distractors or [])])

    results = []
    for item in queries:
        prompt = render_trigger_prompt(catalog, item.query)
        triggers = 0
        for _run in range(runs_per_query):
            response = provider.complete(prompt)
            output = response if isinstance(response, str) else response.output
            if detect_triggered(output, target.name):
                triggers += 1
        trigger_rate = triggers / runs_per_query
        passed = (
            trigger_rate >= threshold
            if item.should_trigger
            else trigger_rate < threshold
        )
        results.append(
            TriggerQueryResult(
                query=item.query,
                should_trigger=item.should_trigger,
                triggers=triggers,
                runs=runs_per_query,
                trigger_rate=trigger_rate,
                passed=passed,
            )
        )

    return TriggerEvalResult(
        skill_path=str(skill_dir),
        skill_name=target.name,
        total_queries=len(queries),
        runs_per_query=runs_per_query,
        threshold=threshold,
        results=results,
        summary=_summarize(results),
    )


def _summarize(results: List[TriggerQueryResult]) -> dict:
    positives = [result for result in results if result.should_trigger]
    negatives = [result for result in results if not result.should_trigger]
    passed = sum(1 for result in results if result.passed)

    summary = {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "accuracy": passed / len(results) if results else 0.0,
    }
    if positives:
        summary["should_trigger_pass_rate"] = sum(
            1 for result in positives if result.passed
        ) / len(positives)
    if negatives:
        summary["should_not_trigger_pass_rate"] = sum(
            1 for result in negatives if result.passed
        ) / len(negatives)
    return summary


def _parse_frontmatter(content: str) -> dict:
    if not content.startswith("---"):
        return {}

    metadata = {}
    for line in content.splitlines()[1:]:
        if line.strip() == "---":
            break
        if ":" not in line or line.startswith((" ", "\t")):
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip("'\"")
    return metadata


def _escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
