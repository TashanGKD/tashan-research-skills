import hashlib
import importlib.util
import json
import pathlib

import pytest


SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_DIR / "scripts" / "build_science_mcp_catalog.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_science_mcp_catalog", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def fixture_skill_catalog():
    return {
        "dimensions": {
            "domains": ["生命科学"],
            "subdomains": ["生物信息学"],
            "stages": ["分析验证"],
            "functions": ["数据处理"],
        }
    }


def fixture_entry():
    return {
        "id": "sequence-mcp",
        "name": "Sequence MCP",
        "domain": "错误旧领域",
        "stage": "错误旧阶段",
        "function": "错误旧功能",
        "status": "verified_source",
        "taxonomy": {
            "domain": "生命科学",
            "subdomain": "生物信息学",
            "stage": "分析验证",
            "function": "数据处理",
            "review_status": "taxonomy_reviewed",
            "evidence_scope": "source_reviewed",
            "source_url": "https://example.org/sequence-mcp",
        },
        "skillhub": {
            "summary": "Process sequence data",
            "capabilities": ["search", "analyze"],
            "transport": ["stdio"],
            "license": "MIT",
        },
    }


def test_build_uses_reviewed_taxonomy_instead_of_legacy_top_level_fields():
    source = {"entries": [fixture_entry()]}
    source_bytes = json.dumps(source).encode("utf-8")
    catalog = load_module().build_catalog(source, fixture_skill_catalog(), source_bytes)
    item = catalog["mcps"][0]
    assert item["domain"] == "生命科学"
    assert item["stage"] == "分析验证"
    assert item["function"] == "数据处理"
    assert item["resource_type"] == "mcp"
    assert item["readiness"] == "trusted"
    assert item["source_url"] == "https://example.org/sequence-mcp"
    assert catalog["source_sha256"] == hashlib.sha256(source_bytes).hexdigest()


def test_builder_rejects_records_without_reviewed_taxonomy():
    entry = fixture_entry()
    entry["taxonomy"]["review_status"] = "needs_review"
    with pytest.raises(ValueError, match="not taxonomy_reviewed"):
        load_module().build_catalog(
            {"entries": [entry]},
            fixture_skill_catalog(),
            b"source",
        )


def test_builder_rejects_unknown_taxonomy_values():
    entry = fixture_entry()
    entry["taxonomy"]["domain"] = "不存在的领域"
    with pytest.raises(ValueError, match="unknown MCP domain"):
        load_module().build_catalog(
            {"entries": [entry]},
            fixture_skill_catalog(),
            b"source",
        )


def test_builder_drops_nonportable_local_install_commands():
    entry = fixture_entry()
    entry["skillhub"]["install_command"] = (
        "uv --directory /Users/example/project run sequence-mcp"
    )
    catalog = load_module().build_catalog(
        {"entries": [entry]},
        fixture_skill_catalog(),
        b"source",
    )
    assert catalog["mcps"][0]["install_command"] is None
