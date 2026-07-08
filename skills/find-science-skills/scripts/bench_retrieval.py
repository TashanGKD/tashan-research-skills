#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the find-science-skills retrieval benchmark.

The benchmark is intentionally local and deterministic: no database, no network,
and no embedding service. It evaluates both the installer recommender
(`find_skills.py`) and the static Wiki search (`search_wiki.py`) against a
curated set of basic, medium, complex, and confusing scientific queries.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import defaultdict

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_BENCH = SKILL_DIR / "data" / "retrieval_bench.json"
DEFAULT_REPORT = SKILL_DIR / "data" / "retrieval_bench_report.json"
DEFAULT_HOLDOUT = SKILL_DIR / "data" / "retrieval_holdout.json"
DEFAULT_HOLDOUT_REPORT = SKILL_DIR / "data" / "retrieval_holdout_report.json"
VALID_LEVELS = {"basic", "medium", "complex"}
VALID_DIFFICULTIES = {"typical", "complex", "confusing"}
VALID_GAP_STATUSES = {"missing_skill", "ranking_gap", "data_gap"}
DEFAULT_MIN_LEVEL_CASES = {"basic": 6, "medium": 6, "complex": 6}
DEFAULT_MIN_DIFFICULTY_CASES = {"confusing": 0}

sys.path.insert(0, str(SCRIPT_DIR))
import find_skills as fs  # noqa: E402
import search_wiki as sw  # noqa: E402


def load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_bench(bench: dict) -> None:
    if bench.get("schema") != "find_science_skills_retrieval_bench_v1":
        raise ValueError("bench schema must be find_science_skills_retrieval_bench_v1")
    if not isinstance(bench.get("thresholds"), dict):
        raise ValueError("bench thresholds must be an object")
    cases = bench.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("bench cases must be a non-empty list")

    minimum_cases = bench.get("minimum_cases") or {}
    min_levels = minimum_cases.get("levels") or DEFAULT_MIN_LEVEL_CASES
    min_difficulties = minimum_cases.get("difficulties") or DEFAULT_MIN_DIFFICULTY_CASES

    seen = set()
    level_counts = defaultdict(int)
    difficulty_counts = defaultdict(int)
    for idx, case in enumerate(cases):
        prefix = f"case[{idx}]"
        cid = case.get("id")
        if not cid:
            raise ValueError(f"{prefix} missing id")
        if cid in seen:
            raise ValueError(f"duplicate case id: {cid}")
        seen.add(cid)
        if case.get("target") not in {"find", "wiki"}:
            raise ValueError(f"{cid} target must be find or wiki")
        level = case.get("level")
        if level not in VALID_LEVELS:
            raise ValueError(f"{cid} level must be basic, medium, or complex")
        level_counts[level] += 1
        difficulty = case.get("difficulty")
        if difficulty not in VALID_DIFFICULTIES:
            raise ValueError(f"{cid} difficulty must be typical, complex, or confusing")
        difficulty_counts[difficulty] += 1
        if not case.get("query"):
            raise ValueError(f"{cid} missing query")
        for key in ("expected_top1_any", "expected_top3_any"):
            value = case.get(key)
            if not isinstance(value, list) or not value:
                raise ValueError(f"{cid} {key} must be a non-empty list")
            if any(is_registry_gap_id(item) for item in value):
                raise ValueError(f"{cid} {key} cannot use a missing-skill placeholder in release bench")
        if "rationale" in case and not str(case.get("rationale") or "").strip():
            raise ValueError(f"{cid} rationale must be non-empty when provided")
        if "false_positive_risks" in case:
            risks = case.get("false_positive_risks")
            if not isinstance(risks, list) or not risks or any(not str(item).strip() for item in risks):
                raise ValueError(f"{cid} false_positive_risks must be a non-empty list when provided")

    for level, required in min_levels.items():
        if level_counts[level] < required:
            raise ValueError(f"level {level} has {level_counts[level]} cases, requires at least {required}")
    for difficulty, required in min_difficulties.items():
        if difficulty_counts[difficulty] < required:
            raise ValueError(
                f"difficulty {difficulty} has {difficulty_counts[difficulty]} cases, requires at least {required}"
            )


def validate_holdout(holdout: dict) -> None:
    if holdout.get("schema") != "find_science_skills_retrieval_holdout_v1":
        raise ValueError("holdout schema must be find_science_skills_retrieval_holdout_v1")
    cases = holdout.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("holdout cases must be a non-empty list")

    seen = set()
    for idx, case in enumerate(cases):
        prefix = f"case[{idx}]"
        cid = case.get("id")
        if not cid:
            raise ValueError(f"{prefix} missing id")
        if cid in seen:
            raise ValueError(f"duplicate holdout case id: {cid}")
        seen.add(cid)
        if case.get("target") not in {"find", "wiki"}:
            raise ValueError(f"{cid} target must be find or wiki")
        if case.get("level") not in VALID_LEVELS:
            raise ValueError(f"{cid} level must be basic, medium, or complex")
        if case.get("difficulty") not in VALID_DIFFICULTIES:
            raise ValueError(f"{cid} difficulty must be typical, complex, or confusing")
        if not case.get("query"):
            raise ValueError(f"{cid} missing query")
        if not case.get("reason"):
            raise ValueError(f"{cid} missing reason")
        expected = case.get("expected_top3_any")
        if not isinstance(expected, list) or not expected:
            raise ValueError(f"{cid} expected_top3_any must be a non-empty list")


def validate_gaps(gaps: dict) -> None:
    if gaps.get("schema") != "find_science_skills_retrieval_gaps_v1":
        raise ValueError("gaps schema must be find_science_skills_retrieval_gaps_v1")
    items = gaps.get("gaps")
    if not isinstance(items, list) or not items:
        raise ValueError("gaps must be a non-empty list")

    seen = set()
    for idx, gap in enumerate(items):
        prefix = f"gap[{idx}]"
        gid = gap.get("id")
        if not gid:
            raise ValueError(f"{prefix} missing id")
        if gid in seen:
            raise ValueError(f"duplicate gap id: {gid}")
        seen.add(gid)
        if gap.get("status") not in VALID_GAP_STATUSES:
            raise ValueError(f"{gid} status must be missing_skill, ranking_gap, or data_gap")
        if not gap.get("title"):
            raise ValueError(f"{gid} missing title")
        if not gap.get("query_examples"):
            raise ValueError(f"{gid} missing query_examples")
        if not gap.get("source_holdout_ids"):
            raise ValueError(f"{gid} missing source_holdout_ids")


def validate_gap_holdout_links(gaps: dict, holdout: dict) -> None:
    validate_gaps(gaps)
    validate_holdout(holdout)

    cases_by_id = {case["id"]: case for case in holdout["cases"]}
    for gap in gaps["gaps"]:
        gid = gap["id"]
        for case_id in gap["source_holdout_ids"]:
            case = cases_by_id.get(case_id)
            if case is None:
                raise ValueError(f"{gid} references unknown holdout case {case_id}")
            if gid not in case.get("expected_top3_any", []):
                raise ValueError(f"{gid} is not expected by referenced holdout case {case_id}")


def result_ids(hit: dict) -> list[str]:
    ids = []
    for key in ("id", "skill_id", "path"):
        value = hit.get(key)
        if value:
            ids.append(value)
    return ids


def is_registry_gap_id(value: str) -> bool:
    return value.startswith("__missing_") and value.endswith("__")


def matched_expected_ids(hits: list[dict], expected: list[str], upto: int) -> list[str]:
    expected_set = set(expected or [])
    matched = []
    for hit in hits[:upto]:
        for value in result_ids(hit):
            if value in expected_set:
                matched.append(value)
    return matched


def match_type(matched: list[str]) -> str:
    if not matched:
        return "none"
    if any(not is_registry_gap_id(value) for value in matched):
        return "real_skill"
    return "registry_gap"


def expected_match_type(case: dict) -> str:
    expected = (case.get("expected_top1_any") or []) + (case.get("expected_top3_any") or [])
    if not expected:
        return "none"
    if any(not is_registry_gap_id(value) for value in expected):
        return "real_skill"
    return "registry_gap"


def any_expected(hits: list[dict], expected: list[str], upto: int) -> bool:
    return bool(matched_expected_ids(hits, expected, upto))


def prepare_find():
    data = fs.load_graph()
    nodes = data["nodes"]
    fs.ensure_blobs(nodes)
    idf = fs.build_idf(nodes)
    return nodes, idf


def run_find_case(case: dict, nodes: dict, idf: dict) -> list[dict]:
    cap = fs.resolve_cap(case.get("capability", "")) if case.get("capability") else None
    q_tokens = fs.query_tokens(case["query"], semantic=not case.get("no_semantic", False))
    intent_cap = None if cap else fs.resolve_cap(case["query"])
    query_intent = fs.infer_intent(case["query"])
    scored = []
    gap_hits = [] if cap else fs.missing_gap_nodes(case["query"])
    for sid, node in nodes.items():
        if cap and node.get("group") != cap:
            continue
        score = fs.score_node(
            node,
            q_tokens,
            set(fs.tok((node.get("name") or "") + " " + sid)),
            idf,
            intent_cap,
            query_intent,
        )
        if score >= 0:
            scored.append((score, node))
    scored.sort(key=lambda x: (-x[0], -(x[1].get("score") or 0), -(x[1].get("stars") or 0)))
    skill_hits = [{"id": node["id"], "score": round(score, 4), "name": node.get("name")} for score, node in scored]
    return (gap_hits + skill_hits)[:5]


def prepare_wiki():
    return sw.load_index()


def run_wiki_case(case: dict, index: dict) -> list[dict]:
    hits = sw.search(index, case["query"], limit=5, doc_type=case.get("doc_type", ""))
    return [
        {
            "id": hit.get("skill_id") or hit.get("path"),
            "skill_id": hit.get("skill_id"),
            "path": hit.get("path"),
            "score": hit.get("score"),
            "title": hit.get("title"),
        }
        for hit in hits
    ]


def summarize(rows: list[dict]) -> dict:
    buckets = defaultdict(lambda: {"count": 0, "top1": 0, "top3": 0})
    for row in rows:
        for key in (
            "overall",
            row["target"],
            f"level_{row['level']}",
            f"difficulty_{row['difficulty']}",
        ):
            buckets[key]["count"] += 1
            buckets[key]["top1"] += 1 if row["top1_ok"] else 0
            buckets[key]["top3"] += 1 if row["top3_ok"] else 0
    summary = {}
    for key, value in sorted(buckets.items()):
        count = value["count"]
        summary[key] = {
            "count": count,
            "top1": value["top1"],
            "top3": value["top3"],
            "top1_rate": round(value["top1"] / count, 4) if count else 0,
            "top3_rate": round(value["top3"] / count, 4) if count else 0,
        }
    return summary


def summarize_resolution(rows: list[dict]) -> dict:
    buckets = defaultdict(lambda: {
        "count": 0,
        "top1_real_skill": 0,
        "top1_registry_gap": 0,
        "top3_real_skill": 0,
        "top3_registry_gap": 0,
    })
    for row in rows:
        for key in (
            "overall",
            row["target"],
            f"level_{row['level']}",
            f"difficulty_{row['difficulty']}",
        ):
            buckets[key]["count"] += 1
            if row["top1_match_type"] == "real_skill":
                buckets[key]["top1_real_skill"] += 1
            elif row["top1_match_type"] == "registry_gap":
                buckets[key]["top1_registry_gap"] += 1
            if row["top3_match_type"] == "real_skill":
                buckets[key]["top3_real_skill"] += 1
            elif row["top3_match_type"] == "registry_gap":
                buckets[key]["top3_registry_gap"] += 1
    return dict(sorted(buckets.items()))


def summarize_expected_resolution(rows: list[dict]) -> dict:
    buckets = defaultdict(lambda: {
        "count": 0,
        "expected_real_skill": 0,
        "expected_registry_gap": 0,
        "expected_none": 0,
    })
    for row in rows:
        for key in (
            "overall",
            row["target"],
            f"level_{row['level']}",
            f"difficulty_{row['difficulty']}",
        ):
            buckets[key]["count"] += 1
            if row["expected_match_type"] == "real_skill":
                buckets[key]["expected_real_skill"] += 1
            elif row["expected_match_type"] == "registry_gap":
                buckets[key]["expected_registry_gap"] += 1
            else:
                buckets[key]["expected_none"] += 1
    return dict(sorted(buckets.items()))


def threshold_failures(summary: dict, thresholds: dict) -> list[str]:
    failures = []
    for bucket, rules in thresholds.items():
        if bucket not in summary:
            continue
        top1_req = rules.get("top1")
        top3_req = rules.get("top3")
        if top1_req is not None and summary[bucket]["top1_rate"] < top1_req:
            failures.append(f"{bucket}.top1 {summary[bucket]['top1_rate']:.3f} < {top1_req:.3f}")
        if top3_req is not None and summary[bucket]["top3_rate"] < top3_req:
            failures.append(f"{bucket}.top3 {summary[bucket]['top3_rate']:.3f} < {top3_req:.3f}")
    return failures


def run_bench(bench: dict) -> dict:
    validate_bench(bench)
    find_nodes = find_idf = wiki_index = None
    rows = []
    for case in bench["cases"]:
        if case["target"] == "find":
            if find_nodes is None:
                find_nodes, find_idf = prepare_find()
            hits = run_find_case(case, find_nodes, find_idf)
        elif case["target"] == "wiki":
            if wiki_index is None:
                wiki_index = prepare_wiki()
            hits = run_wiki_case(case, wiki_index)
        else:
            raise ValueError(f"Unknown target: {case['target']}")
        top1_matches = matched_expected_ids(hits, case.get("expected_top1_any") or [], 1)
        top3_matches = matched_expected_ids(hits, case.get("expected_top3_any") or [], 3)
        top1_ok = bool(top1_matches)
        top3_ok = bool(top3_matches)
        rows.append({
            "id": case["id"],
            "target": case["target"],
            "level": case["level"],
            "difficulty": case.get("difficulty", "unspecified"),
            "query": case["query"],
            "top1_ok": top1_ok,
            "top3_ok": top3_ok,
            "top1_match_type": match_type(top1_matches),
            "top3_match_type": match_type(top3_matches),
            "expected_match_type": expected_match_type(case),
            "top5": [result_ids(hit)[0] for hit in hits],
            "expected_top1_any": case.get("expected_top1_any") or [],
            "expected_top3_any": case.get("expected_top3_any") or [],
        })
    summary = summarize(rows)
    failures = threshold_failures(summary, bench.get("thresholds") or {})
    return {
        "schema": "find_science_skills_retrieval_bench_report_v1",
        "bench_version": bench.get("version"),
        "thresholds": bench.get("thresholds") or {},
        "minimum_cases": bench.get("minimum_cases") or {
            "levels": DEFAULT_MIN_LEVEL_CASES,
            "difficulties": DEFAULT_MIN_DIFFICULTY_CASES,
        },
        "summary": summary,
        "resolution_summary": summarize_resolution(rows),
        "expected_resolution_summary": summarize_expected_resolution(rows),
        "threshold_failures": failures,
        "case_failures": [row for row in rows if not row["top1_ok"] or not row["top3_ok"]],
        "cases": rows,
    }


def run_holdout(holdout: dict) -> dict:
    validate_holdout(holdout)
    find_nodes = find_idf = wiki_index = None
    rows = []
    for case in holdout["cases"]:
        if case["target"] == "find":
            if find_nodes is None:
                find_nodes, find_idf = prepare_find()
            hits = run_find_case(case, find_nodes, find_idf)
        elif case["target"] == "wiki":
            if wiki_index is None:
                wiki_index = prepare_wiki()
            hits = run_wiki_case(case, wiki_index)
        else:
            raise ValueError(f"Unknown target: {case['target']}")

        expected_top1 = case.get("expected_top1_any") or case.get("expected_top3_any") or []
        expected_top3 = case.get("expected_top3_any") or []
        top1_matches = matched_expected_ids(hits, expected_top1, 1)
        top3_matches = matched_expected_ids(hits, expected_top3, 3)
        top1_ok = bool(top1_matches)
        top3_ok = bool(top3_matches)
        rows.append({
            "id": case["id"],
            "target": case["target"],
            "level": case["level"],
            "difficulty": case["difficulty"],
            "query": case["query"],
            "reason": case["reason"],
            "top1_ok": top1_ok,
            "top3_ok": top3_ok,
            "top1_match_type": match_type(top1_matches),
            "top3_match_type": match_type(top3_matches),
            "expected_match_type": expected_match_type(case),
            "top5": [result_ids(hit)[0] for hit in hits],
            "expected_top1_any": expected_top1,
            "expected_top3_any": expected_top3,
        })
    summary = summarize(rows)
    return {
        "schema": "find_science_skills_retrieval_holdout_report_v1",
        "holdout_version": holdout.get("version"),
        "summary": summary,
        "resolution_summary": summarize_resolution(rows),
        "expected_resolution_summary": summarize_expected_resolution(rows),
        "case_failures": [row for row in rows if not row["top3_ok"]],
        "cases": rows,
    }


def print_markdown(report: dict) -> None:
    print("# Retrieval Bench Report\n")
    print("| Bucket | Count | Top-1 | Top-3 |")
    print("| --- | ---: | ---: | ---: |")
    for name, item in report["summary"].items():
        print(f"| {name} | {item['count']} | {item['top1_rate']:.2%} | {item['top3_rate']:.2%} |")
    if report.get("resolution_summary"):
        if report.get("expected_resolution_summary"):
            print("\n## Expected Target Split\n")
            print("| Bucket | Count | Expected Real Skill | Expected Registry Gap | Expected None |")
            print("| --- | ---: | ---: | ---: | ---: |")
            for name, item in report["expected_resolution_summary"].items():
                print(
                    f"| {name} | {item['count']} | {item['expected_real_skill']} | "
                    f"{item['expected_registry_gap']} | {item['expected_none']} |"
                )
        print("\n## Resolution Summary\n")
        print("| Bucket | Count | Top-1 Real Skill | Top-1 Registry Gap | Top-3 Real Skill | Top-3 Registry Gap |")
        print("| --- | ---: | ---: | ---: | ---: | ---: |")
        for name, item in report["resolution_summary"].items():
            print(
                f"| {name} | {item['count']} | {item['top1_real_skill']} | "
                f"{item['top1_registry_gap']} | {item['top3_real_skill']} | {item['top3_registry_gap']} |"
            )
        gap_rows = [row for row in report["cases"] if row.get("top3_match_type") == "registry_gap"]
        if gap_rows:
            print("\n## Registry Gap Matches\n")
            for row in gap_rows:
                gap_ids = [value for value in row["top5"][:3] if is_registry_gap_id(value)]
                if not gap_ids:
                    gap_ids = [value for value in row["expected_top3_any"] if is_registry_gap_id(value)]
                print(f"- `{row['id']}` -> {', '.join(gap_ids)}")
                print(f"  - query: {row['query']}")
    if report.get("threshold_failures"):
        print("\n## Threshold Failures\n")
        for failure in report["threshold_failures"]:
            print(f"- {failure}")
    if report["case_failures"]:
        print("\n## Case Failures\n")
        for row in report["case_failures"]:
            print(f"- `{row['id']}` top1={row['top1_ok']} top3={row['top3_ok']} query={row['query']}")
            print(f"  - top5: {', '.join(row['top5'])}")
            print(f"  - expected top1: {', '.join(row['expected_top1_any'])}")
            print(f"  - expected top3: {', '.join(row['expected_top3_any'])}")
    else:
        print("\nNo case failures.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Run find-science-skills retrieval benchmark")
    ap.add_argument("--bench", default=str(DEFAULT_BENCH))
    ap.add_argument("--report", default=str(DEFAULT_REPORT))
    ap.add_argument("--holdout", action="store_true", help="Run non-gating holdout cases instead of release bench")
    ap.add_argument("--holdout-file", default=str(DEFAULT_HOLDOUT))
    ap.add_argument("--holdout-report", default=str(DEFAULT_HOLDOUT_REPORT))
    ap.add_argument("--json", action="store_true", help="Print full JSON report")
    ap.add_argument("--no-write", action="store_true", help="Do not write report file")
    ap.add_argument("--no-fail", action="store_true", help="Exit 0 even if thresholds fail")
    args = ap.parse_args()

    if args.holdout:
        holdout = load_json(pathlib.Path(args.holdout_file))
        report = run_holdout(holdout)
        report_path = pathlib.Path(args.holdout_report)
    else:
        bench = load_json(pathlib.Path(args.bench))
        validate_bench(bench)
        report = run_bench(bench)
        report_path = pathlib.Path(args.report)
    if not args.no_write:
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_markdown(report)
    if report.get("threshold_failures") and not args.no_fail:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
