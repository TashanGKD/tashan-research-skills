#!/usr/bin/env python3
"""Score host-agent activation decisions for a skill's trigger queries.

The host agent decides, per query and per repetition, whether it would
activate the target skill (recording the skill name or "none"). This script
replays those decisions through the deterministic trigger evaluator.

Decisions format:
[
  {"query": "...", "should_trigger": true, "decisions": ["skill-name", "none", "skill-name"]}
]
Every entry must carry the same number of decisions (the runs-per-query).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _find_repo_root() -> Path:
    """Resolve an explicit, bundled, or in-repo CriticAgent kernel."""

    import os

    env_root = os.environ.get("MCP_CRITICAGENT_ROOT")
    candidates = [
        Path(env_root) if env_root else None,
        Path(__file__).resolve().parents[1] / "vendor" / "mcp_criticagent",
        Path(__file__).resolve().parents[3],
    ]
    for candidate in candidates:
        if candidate and (candidate / "src" / "core" / "skill_trigger.py").is_file():
            return candidate

    raise SystemExit(
        "ERROR: evaluation kernel not found. Reinstall the complete skill package, "
        "run from inside MCP-CriticAgent, or set MCP_CRITICAGENT_ROOT."
    )


sys.path.insert(0, str(_find_repo_root()))

from src.core.skill_trigger import (  # noqa: E402
    TriggerQuery,
    load_distractor_entries,
    load_catalog_entry,
    run_trigger_evals,
)


class ScriptedDecisionProvider:
    """Serves the host agent's recorded decisions, matched by query text.

    Longer queries are matched first so a query that is a prefix of another
    can never steal the longer query's decisions.
    """

    def __init__(self, decisions_by_query):
        self.ordered_queries = sorted(decisions_by_query, key=len, reverse=True)
        self.decisions_by_query = decisions_by_query
        self.cursor = {}

    def complete(self, prompt: str) -> str:
        for query in self.ordered_queries:
            if query in prompt:
                decisions = self.decisions_by_query[query]
                index = self.cursor.get(query, 0)
                self.cursor[query] = index + 1
                return decisions[min(index, len(decisions) - 1)]
        raise SystemExit(f"ERROR: no decisions recorded for prompt: {prompt[-120:]!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir", help="skill directory (SKILL.md is read for name)")
    parser.add_argument("decisions", help="decisions JSON (see module docstring)")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--distractors-root", help="scan this directory for sibling-skill distractors"
    )
    parser.add_argument("--output", help="also write the full result JSON here")
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="print only pass counts and accuracy while --output retains full JSON",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help=(
            "emit quality findings without returning a failing process status; "
            "use when a supervising CriticAgent must adjudicate an imperfect result"
        ),
    )
    args = parser.parse_args()

    entries = json.loads(Path(args.decisions).read_text(encoding="utf-8"))
    if not isinstance(entries, list) or not entries:
        raise SystemExit("ERROR: decisions must be a non-empty JSON array")

    runs_per_query = None
    queries = []
    decisions_by_query = {}
    for index, entry in enumerate(entries):
        query = entry.get("query")
        should = entry.get("should_trigger")
        decisions = entry.get("decisions")
        if not isinstance(query, str) or not isinstance(should, bool):
            raise SystemExit(f"ERROR: entries[{index}] needs query + should_trigger")
        if not isinstance(decisions, list) or not decisions:
            raise SystemExit(f"ERROR: entries[{index}].decisions must be a list")
        if runs_per_query is None:
            runs_per_query = len(decisions)
        elif len(decisions) != runs_per_query:
            raise SystemExit("ERROR: all entries must have the same decisions count")
        queries.append(TriggerQuery(query=query, should_trigger=should))
        decisions_by_query[query] = [str(decision) for decision in decisions]

    distractors = []
    if args.distractors_root:
        target_name = load_catalog_entry(args.skill_dir).name
        distractors = load_distractor_entries(args.distractors_root, target_name)

    result = run_trigger_evals(
        args.skill_dir,
        provider=ScriptedDecisionProvider(decisions_by_query),
        queries=queries,
        distractors=distractors,
        runs_per_query=runs_per_query,
        threshold=args.threshold,
    )
    result_dict = result.to_dict()
    payload = json.dumps(result_dict, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    if args.summary_only:
        compact = {
            "passed": result.summary["passed"],
            "total": result.summary["total"],
            "accuracy": result.summary["accuracy"],
        }
        print(json.dumps(compact, ensure_ascii=False, indent=2))
    else:
        print(payload)

    if result.summary["accuracy"] < 1.0:
        print(
            f"\nVERDICT HINT: trigger accuracy {result.summary['accuracy']:.2f} < 1.0 "
            "— review the failed queries above.",
            file=sys.stderr,
        )
        if not args.report_only:
            sys.exit(1)


if __name__ == "__main__":
    main()
