#!/usr/bin/env python3
"""Filter static science Skill and MCP catalogs by the shared taxonomy."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Iterable


SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_SKILL_CATALOG = SKILL_DIR / "data" / "science_skill_catalog.json"
DEFAULT_MCP_CATALOG = SKILL_DIR / "data" / "science_mcp_catalog.json"
READINESS_ORDER = {"trusted": 0, "provisional": 1, "restricted": 2}
COMPACT_FIELDS = (
    "resource_type",
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
    "source_repository",
    "source_path",
    "source_url",
    "license",
    "license_status",
    "transport",
    "install_command",
    "capabilities",
    "docs",
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


def _read_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_catalogs(
    skill_path: pathlib.Path = DEFAULT_SKILL_CATALOG,
    mcp_path: pathlib.Path = DEFAULT_MCP_CATALOG,
) -> dict:
    skill_catalog = _read_json(skill_path)
    mcp_catalog = _read_json(mcp_path)
    if skill_catalog["dimensions"] != mcp_catalog["dimensions"]:
        raise ValueError("Skill and MCP catalogs use different taxonomy dimensions")

    skills = [
        {"resource_type": "skill", **item}
        for item in skill_catalog.get("skills", [])
    ]
    return {
        "dimensions": skill_catalog["dimensions"],
        "resources": skills + mcp_catalog.get("mcps", []),
        "counts": {
            "skill": len(skills),
            "mcp": len(mcp_catalog.get("mcps", [])),
        },
    }


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


def _sort_key(resource: dict) -> tuple:
    return (
        0 if resource.get("function_match", True) else 1,
        READINESS_ORDER.get(resource.get("readiness"), 3),
        -(resource.get("quality_score") or 0),
        resource["id"],
    )


def _resource_types(resource: str) -> set[str]:
    if resource == "all":
        return {"skill", "mcp"}
    if resource not in {"skill", "mcp"}:
        raise ValueError(f"unknown resource type: {resource}")
    return {resource}


def function_options(
    catalog: dict,
    *,
    domains: Iterable[str],
    stages: Iterable[str],
    subdomains: Iterable[str] = (),
    resource: str = "skill",
) -> list[dict]:
    dimensions = catalog["dimensions"]
    selected_domains = _values(domains)
    selected_subdomains = _values(subdomains)
    selected_stages = _values(stages)
    selected_types = _resource_types(resource)
    if not selected_domains or not selected_stages:
        raise ValueError("domain and stage are required")
    _validate(selected_domains, dimensions["domains"], "domain")
    _validate(selected_subdomains, dimensions["subdomains"], "subdomain")
    _validate(selected_stages, dimensions["stages"], "stage")

    matches = [
        item
        for item in catalog["resources"]
        if item["resource_type"] in selected_types
        and item["domain"] in selected_domains
        and item["stage"] in selected_stages
        and (not selected_subdomains or item["subdomain"] in selected_subdomains)
    ]
    options = []
    for function in dimensions["functions"]:
        members = sorted(
            (item for item in matches if item["function"] == function),
            key=_sort_key,
        )
        if members:
            options.append(
                {
                    "function": function,
                    "count": len(members),
                    "skill_count": sum(item["resource_type"] == "skill" for item in members),
                    "mcp_count": sum(item["resource_type"] == "mcp" for item in members),
                    "examples": [item["id"] for item in members[:3]],
                }
            )
    return options


def filter_resources(
    catalog: dict,
    *,
    domains: Iterable[str],
    stages: Iterable[str],
    functions: Iterable[str],
    subdomains: Iterable[str] = (),
    resource: str = "skill",
    function_mode: str = "strict",
) -> list[dict]:
    dimensions = catalog["dimensions"]
    selected_domains = _values(domains)
    selected_subdomains = _values(subdomains)
    selected_stages = _values(stages)
    selected_functions = _values(functions)
    selected_types = _resource_types(resource)

    if not selected_domains or not selected_stages or not selected_functions:
        raise ValueError("domain, stage, and function are required")
    _validate(selected_domains, dimensions["domains"], "domain")
    _validate(selected_subdomains, dimensions["subdomains"], "subdomain")
    _validate(selected_stages, dimensions["stages"], "stage")
    _validate(selected_functions, dimensions["functions"], "function")
    if function_mode not in {"strict", "prefer"}:
        raise ValueError(f"unknown function mode: {function_mode}")

    matches = [
        item
        for item in catalog["resources"]
        if item["resource_type"] in selected_types
        and item["domain"] in selected_domains
        and item["stage"] in selected_stages
        and (not selected_subdomains or item["subdomain"] in selected_subdomains)
    ]
    if function_mode == "strict":
        results = [item for item in matches if item["function"] in selected_functions]
    else:
        results = [
            {**item, "function_match": item["function"] in selected_functions}
            for item in matches
        ]
    return sorted(results, key=_sort_key)


def result_payload(selection: dict, results: list[dict], *, function_mode: str, full: bool = False) -> dict:
    resources = results
    if not full:
        resources = [
            {field: item[field] for field in COMPACT_FIELDS if field in item}
            for item in results
        ]
    return {
        "selection": selection,
        "function_mode": function_mode,
        "decision_contract": DECISION_CONTRACT,
        "count": len(results),
        "counts": {
            "skill": sum(item["resource_type"] == "skill" for item in results),
            "mcp": sum(item["resource_type"] == "mcp" for item in results),
        },
        "resources": resources,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="按统一科研分类筛选 Skill 和 MCP。")
    parser.add_argument("--skill-catalog", type=pathlib.Path, default=DEFAULT_SKILL_CATALOG)
    parser.add_argument("--mcp-catalog", type=pathlib.Path, default=DEFAULT_MCP_CATALOG)
    parser.add_argument("--resource", choices=("all", "skill", "mcp"), default="skill")
    parser.add_argument("--domain", action="append", help="一级领域，可重复或用逗号分隔")
    parser.add_argument("--subdomain", action="append", help="可选二级领域，可重复或用逗号分隔")
    parser.add_argument("--stage", action="append", help="研究阶段，可重复或用逗号分隔")
    parser.add_argument("--function", action="append", help="功能分工，可重复或用逗号分隔")
    parser.add_argument("--strict-function", action="store_true", help="把功能作为硬过滤")
    parser.add_argument("--list-dimensions", action="store_true", help="列出分类和资源数量")
    parser.add_argument("--list-functions", action="store_true", help="列出当前领域和阶段的功能")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    parser.add_argument("--full", action="store_true", help="保留完整目录字段")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        catalog = load_catalogs(args.skill_catalog, args.mcp_catalog)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    if args.list_dimensions:
        print(json.dumps({"dimensions": catalog["dimensions"], "counts": catalog["counts"]}, ensure_ascii=False, indent=2))
        return 0

    selection = {
        "resource": args.resource,
        "domains": _values(args.domain),
        "subdomains": _values(args.subdomain),
        "stages": _values(args.stage),
        "functions": _values(args.function),
    }
    if args.list_functions:
        try:
            options = function_options(
                catalog,
                domains=selection["domains"],
                subdomains=selection["subdomains"],
                stages=selection["stages"],
                resource=args.resource,
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps({"selection": selection, "function_options": options}, ensure_ascii=False, indent=2))
        return 0

    try:
        results = filter_resources(
            catalog,
            domains=selection["domains"],
            subdomains=selection["subdomains"],
            stages=selection["stages"],
            functions=selection["functions"],
            resource=args.resource,
            function_mode="strict" if args.strict_function else "prefer",
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

    print(f"匹配到 {len(results)} 项科研资源（Skill {payload['counts']['skill']} / MCP {payload['counts']['mcp']}）。")
    for item in results:
        label = "Skill" if item["resource_type"] == "skill" else "MCP"
        print(f"- [{label}] {item['id']} | {item['name']} | {item['readiness']}")
        print(f"  {item['summary']}")
        print(f"  来源：{item.get('source_url') or item.get('source_repository')}")
    if not results:
        print("当前分类组合暂无资源；请调整一个分类维度或询问用户。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
