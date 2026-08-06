#!/usr/bin/env python3
"""Build the compact MCP catalog used by find-science-skills."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re


SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_SKILL_CATALOG = SKILL_DIR / "data" / "science_skill_catalog.json"
DEFAULT_OUTPUT = SKILL_DIR / "data" / "science_mcp_catalog.json"
LOCAL_PATH_PATTERN = re.compile(r"(?:[A-Za-z]:\\Users\\|/Users/|/home/)[^\s\"']+")


def _read_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _readiness(entry: dict) -> str:
    taxonomy = entry.get("taxonomy") or {}
    if taxonomy.get("evidence_scope") == "source_reviewed":
        return "trusted"
    return "provisional"


def _portable_install_command(value: object) -> object:
    if isinstance(value, str) and LOCAL_PATH_PATTERN.search(value):
        return None
    return value


def compact_entry(entry: dict, allowed: dict[str, set[str]]) -> dict:
    taxonomy = entry.get("taxonomy") or {}
    if taxonomy.get("review_status") != "taxonomy_reviewed":
        raise ValueError(f"MCP is not taxonomy_reviewed: {entry.get('id')}")

    for key in ("domain", "subdomain", "stage", "function"):
        value = taxonomy.get(key)
        if value not in allowed[key]:
            raise ValueError(f"unknown MCP {key}: {value!r} ({entry.get('id')})")

    skillhub = entry.get("skillhub") or {}
    info_page = skillhub.get("info_page") or {}
    summary = (
        skillhub.get("summary")
        or skillhub.get("description")
        or entry.get("overlap")
        or entry.get("name")
        or entry["id"]
    )
    capabilities = skillhub.get("capabilities") or info_page.get("tool_names") or []
    source_url = taxonomy.get("source_url") or skillhub.get("source") or entry.get("url")

    return {
        "resource_type": "mcp",
        "id": entry["id"],
        "name": entry.get("name") or entry["id"],
        "summary": summary,
        "task": summary,
        "domain": taxonomy["domain"],
        "subdomain": taxonomy["subdomain"],
        "stage": taxonomy["stage"],
        "function": taxonomy["function"],
        "readiness": _readiness(entry),
        "quality_score": 90 if _readiness(entry) == "trusted" else 70,
        "source_url": source_url,
        "source_repository": source_url,
        "source_path": "",
        "status": entry.get("status"),
        "evidence_scope": taxonomy.get("evidence_scope"),
        "license": entry.get("license") or skillhub.get("license"),
        "license_status": entry.get("license_status"),
        "transport": skillhub.get("transport") or info_page.get("transport") or [],
        "install_command": _portable_install_command(
            skillhub.get("install_command") or info_page.get("install_command")
        ),
        "capabilities": capabilities,
        "docs": skillhub.get("docs") or source_url,
    }


def build_catalog(source: dict, skill_catalog: dict, source_bytes: bytes) -> dict:
    dimensions = skill_catalog["dimensions"]
    allowed = {
        "domain": set(dimensions["domains"]),
        "subdomain": set(dimensions["subdomains"]),
        "stage": set(dimensions["stages"]),
        "function": set(dimensions["functions"]),
    }
    mcps = [compact_entry(entry, allowed) for entry in source.get("entries", [])]
    mcps.sort(
        key=lambda item: (
            dimensions["domains"].index(item["domain"]),
            dimensions["subdomains"].index(item["subdomain"]),
            dimensions["stages"].index(item["stage"]),
            dimensions["functions"].index(item["function"]),
            item["id"],
        )
    )
    return {
        "schema": "science_mcp_catalog_v1",
        "generated_at": source.get("generated_at"),
        "source_schema": source.get("schema_version"),
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_mcp_count": len(source.get("entries", [])),
        "active_mcp_count": len(mcps),
        "dimensions": dimensions,
        "mcps": mcps,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="从活动科研 MCP Hub 快照生成紧凑静态目录。")
    parser.add_argument("source", type=pathlib.Path, help="science-mcp-catalog.json 路径")
    parser.add_argument("--skill-catalog", type=pathlib.Path, default=DEFAULT_SKILL_CATALOG)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source_bytes = args.source.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    skill_catalog = _read_json(args.skill_catalog)
    catalog = build_catalog(source, skill_catalog, source_bytes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {catalog['active_mcp_count']} MCP records to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
