#!/usr/bin/env python3
"""Filter the static science skill catalog by three taxonomy dimensions."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Iterable


SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = SKILL_DIR / "data" / "science_skill_catalog.json"
READINESS_ORDER = {"trusted": 0, "provisional": 1, "restricted": 2}
COMPACT_FIELDS = (
    "id",
    "name",
    "summary",
    "task",
    "domain",
    "subdomain",
    "stage",
    "function",
    "function_match",
    "readiness",
    "quality_score",
    "model_source_review_score",
    "critic_evidence_level",
    "model_source_review_verdict",
    "static_validation_status",
    "evaluation_status",
    "install_recommendation",
    "source_repository",
    "source_path",
)
DECISION_CONTRACT = {
    "quality_order_is_semantic_relevance": False,
    "direct_match_requires": [
        "research_object_or_data",
        "requested_action_or_output",
    ],
    "maximum_recommendations": 5,
    "no_direct_match": "return_gap_or_ask_clarification",
}


def load_catalog(path: pathlib.Path = DEFAULT_CATALOG) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def attach_critic_scores(catalog: dict, scorecard: dict) -> dict:
    """Return a catalog copy enriched with optional critic evidence."""

    records = scorecard.get("scores")
    if not isinstance(records, list):
        raise ValueError("critic scorecard must contain a scores array")
    by_id: dict[str, dict] = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("id"), str):
            raise ValueError("critic scorecard records require string ids")
        if record["id"] in by_id:
            raise ValueError(f"duplicate critic score id: {record['id']}")
        by_id[record["id"]] = record

    critic_fields = {
        "model_source_review_score",
        "critic_evidence_level",
        "model_source_review_verdict",
        "static_validation_status",
        "evaluation_status",
        "install_recommendation",
        "critic_model",
        "critic_source_sha256",
    }
    skills = []
    for skill in catalog["skills"]:
        evidence = by_id.get(skill["id"], {})
        skills.append(
            {
                **skill,
                **{key: evidence[key] for key in critic_fields if key in evidence},
            }
        )
    return {**catalog, "skills": skills, "critic_scorecard_attached": True}


def _values(items: Iterable[str] | None) -> list[str]:
    values: list[str] = []
    for item in items or ():
        for value in item.split(","):
            value = value.strip()
            if value and value not in values:
                values.append(value)
    return values


def _validate(selected: list[str], allowed: list[str], label: str) -> None:
    unknown = sorted(set(selected) - set(allowed))
    if unknown:
        raise ValueError(f"unknown {label}: {', '.join(unknown)}")


def _sort_key(skill: dict) -> tuple:
    return (
        0 if skill.get("function_match", True) else 1,
        READINESS_ORDER.get(skill.get("readiness"), 3),
        -(skill.get("quality_score") or 0),
        skill["id"],
    )


def function_options(
    catalog: dict,
    *,
    domains: Iterable[str],
    stages: Iterable[str],
    subdomains: Iterable[str] = (),
) -> list[dict]:
    dimensions = catalog["dimensions"]
    selected_domains = _values(domains)
    selected_subdomains = _values(subdomains)
    selected_stages = _values(stages)
    if not selected_domains or not selected_stages:
        raise ValueError("domain and stage are required")
    _validate(selected_domains, dimensions["domains"], "domain")
    _validate(selected_subdomains, dimensions["subdomains"], "subdomain")
    _validate(selected_stages, dimensions["stages"], "stage")

    matches = [
        skill
        for skill in catalog["skills"]
        if skill["domain"] in selected_domains
        and skill["stage"] in selected_stages
        and (not selected_subdomains or skill["subdomain"] in selected_subdomains)
    ]
    options = []
    for function in dimensions["functions"]:
        members = sorted(
            (skill for skill in matches if skill["function"] == function),
            key=_sort_key,
        )
        if members:
            options.append(
                {
                    "function": function,
                    "count": len(members),
                    "trusted_count": sum(
                        skill.get("readiness") == "trusted" for skill in members
                    ),
                    "examples": [skill["id"] for skill in members[:3]],
                }
            )
    return options


def result_payload(
    selection: dict,
    results: list[dict],
    *,
    function_mode: str,
    full: bool = False,
) -> dict:
    skills = results
    if not full:
        skills = [
            {field: skill[field] for field in COMPACT_FIELDS if field in skill}
            for skill in results
        ]
    return {
        "selection": selection,
        "function_mode": function_mode,
        "decision_contract": DECISION_CONTRACT,
        "count": len(results),
        "skills": skills,
    }


def filter_skills(
    catalog: dict,
    *,
    domains: Iterable[str],
    stages: Iterable[str],
    functions: Iterable[str],
    subdomains: Iterable[str] = (),
    function_mode: str = "strict",
    min_source_review_score: int | None = None,
    critic_require_full_source: bool = False,
    critic_require_package_pass: bool = False,
) -> list[dict]:
    dimensions = catalog["dimensions"]
    selected_domains = _values(domains)
    selected_subdomains = _values(subdomains)
    selected_stages = _values(stages)
    selected_functions = _values(functions)

    if not selected_domains or not selected_stages or not selected_functions:
        raise ValueError("domain, stage, and function are required")
    _validate(selected_domains, dimensions["domains"], "domain")
    _validate(selected_subdomains, dimensions["subdomains"], "subdomain")
    _validate(selected_stages, dimensions["stages"], "stage")
    _validate(selected_functions, dimensions["functions"], "function")
    if function_mode not in {"strict", "prefer"}:
        raise ValueError(f"unknown function mode: {function_mode}")
    if min_source_review_score is not None:
        if not catalog.get("critic_scorecard_attached"):
            raise ValueError("source review score requires an attached critic scorecard")
        if not 0 <= min_source_review_score <= 100:
            raise ValueError("source review score must be between 0 and 100")
    if critic_require_full_source and not catalog.get("critic_scorecard_attached"):
        raise ValueError("full-source critic filtering requires an attached critic scorecard")
    if critic_require_package_pass and not catalog.get("critic_scorecard_attached"):
        raise ValueError("package-pass critic filtering requires an attached critic scorecard")

    domain_stage_matches = [
        skill
        for skill in catalog["skills"]
        if skill["domain"] in selected_domains
        and skill["stage"] in selected_stages
        and (not selected_subdomains or skill["subdomain"] in selected_subdomains)
    ]
    if function_mode == "strict":
        results = [
            skill for skill in domain_stage_matches if skill["function"] in selected_functions
        ]
    else:
        results = [
            {**skill, "function_match": skill["function"] in selected_functions}
            for skill in domain_stage_matches
        ]
    if min_source_review_score is not None:
        results = [
            skill
            for skill in results
            if isinstance(skill.get("model_source_review_score"), (int, float))
            and skill["model_source_review_score"] >= min_source_review_score
        ]
    if critic_require_full_source:
        results = [
            skill
            for skill in results
            if skill.get("critic_evidence_level") == "full_source"
        ]
    if critic_require_package_pass:
        results = [
            skill
            for skill in results
            if skill.get("static_validation_status") == "pass"
        ]
    return sorted(results, key=_sort_key)


def selection_payload(args: argparse.Namespace) -> dict:
    return {
        "domains": _values(args.domain),
        "subdomains": _values(args.subdomain),
        "stages": _values(args.stage),
        "functions": _values(args.function),
        "min_source_review_score": args.min_source_review_score,
        "critic_require_full_source": args.critic_require_full_source,
        "critic_require_package_pass": args.critic_require_package_pass,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="按领域、研究阶段和功能分工筛选科研 skill。"
    )
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    parser.add_argument(
        "--critic-scorecard",
        help="可选 CriticAgent 评分旁车；仅显式提供时参与输出或过滤",
    )
    parser.add_argument(
        "--min-source-review-score",
        type=int,
        help="仅保留达到该模型源码评审分的技能；元数据记录无可比较分数",
    )
    parser.add_argument(
        "--critic-require-full-source",
        action="store_true",
        help="排除仅按 registry 元数据评分的技能",
    )
    parser.add_argument(
        "--critic-require-package-pass",
        action="store_true",
        help="仅保留通过 CriticAgent 严格安装检查的技能",
    )
    parser.add_argument("--domain", action="append", help="一级领域，可重复或用逗号分隔")
    parser.add_argument("--subdomain", action="append", help="可选二级领域，可重复或用逗号分隔")
    parser.add_argument("--stage", action="append", help="研究阶段，可重复或用逗号分隔")
    parser.add_argument("--function", action="append", help="功能分工，可重复或用逗号分隔")
    parser.add_argument(
        "--strict-function",
        action="store_true",
        help="把功能作为硬过滤；默认仅按功能优先排序，避免复合任务漏召回",
    )
    parser.add_argument("--list-dimensions", action="store_true", help="列出合法分类及技能数量")
    parser.add_argument(
        "--list-functions",
        action="store_true",
        help="按已选领域和阶段列出可用功能及代表技能",
    )
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    parser.add_argument(
        "--full",
        action="store_true",
        help="保留审查状态和分类理由等完整目录字段",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    catalog = load_catalog(pathlib.Path(args.catalog))
    if args.critic_scorecard:
        scorecard = json.loads(
            pathlib.Path(args.critic_scorecard).read_text(encoding="utf-8")
        )
        try:
            catalog = attach_critic_scores(catalog, scorecard)
        except ValueError as exc:
            parser.error(str(exc))
    if args.list_dimensions:
        print(json.dumps(catalog["dimensions"], ensure_ascii=False, indent=2))
        return 0

    selection = selection_payload(args)
    if args.list_functions:
        try:
            options = function_options(
                catalog,
                domains=selection["domains"],
                subdomains=selection["subdomains"],
                stages=selection["stages"],
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(
            json.dumps(
                {"selection": selection, "function_options": options},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    try:
        results = filter_skills(
            catalog,
            domains=selection["domains"],
            subdomains=selection["subdomains"],
            stages=selection["stages"],
            functions=selection["functions"],
            function_mode="strict" if args.strict_function else "prefer",
            min_source_review_score=args.min_source_review_score,
            critic_require_full_source=args.critic_require_full_source,
            critic_require_package_pass=args.critic_require_package_pass,
        )
    except ValueError as exc:
        parser.error(str(exc))

    payload = result_payload(
        selection,
        results,
        function_mode="strict" if args.strict_function else "prefer",
        full=args.full,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"匹配到 {len(results)} 个科研 skill。")
    for skill in results:
        critic = ""
        if isinstance(skill.get("model_source_review_score"), (int, float)):
            critic = (
                f" | Source review {skill['model_source_review_score']}"
                f"/{skill.get('critic_evidence_level', 'unknown')}"
            )
        print(
            f"- {skill['id']} | {skill['name']} | {skill['readiness']} | "
            f"质量 {skill.get('quality_score') if skill.get('quality_score') is not None else '未评'}"
            f"{critic}"
        )
        print(f"  {skill['summary']}")
        print(f"  来源：{skill['source_repository']}/{skill['source_path']}")
    if not results:
        print("该三维组合暂无技能；请调整一个分类维度或向用户确认需求。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
