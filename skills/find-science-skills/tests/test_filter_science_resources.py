import importlib.util
import json
import pathlib


SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_DIR / "scripts" / "filter_science_resources.py"
SKILL_CATALOG_PATH = SKILL_DIR / "data" / "science_skill_catalog.json"
MCP_CATALOG_PATH = SKILL_DIR / "data" / "science_mcp_catalog.json"


def load_module():
    spec = importlib.util.spec_from_file_location("filter_science_resources", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def fixture_catalog():
    dimensions = {
        "domains": ["生命科学"],
        "subdomains": ["生物信息学"],
        "stages": ["分析验证"],
        "functions": ["数据处理", "验证评测"],
    }
    return {
        "dimensions": dimensions,
        "resources": [
            {
                "resource_type": "skill",
                "id": "sequence-skill",
                "name": "Sequence Skill",
                "summary": "Process sequence data",
                "domain": "生命科学",
                "subdomain": "生物信息学",
                "stage": "分析验证",
                "function": "数据处理",
                "readiness": "trusted",
                "quality_score": 80,
            },
            {
                "resource_type": "mcp",
                "id": "sequence-mcp",
                "name": "Sequence MCP",
                "summary": "Evaluate sequence models",
                "domain": "生命科学",
                "subdomain": "生物信息学",
                "stage": "分析验证",
                "function": "验证评测",
                "readiness": "trusted",
                "quality_score": 90,
            },
        ],
        "counts": {"skill": 1, "mcp": 1},
    }


def test_default_resource_mode_returns_only_skills():
    results = load_module().filter_resources(
        fixture_catalog(),
        domains=["生命科学"],
        stages=["分析验证"],
        functions=["数据处理"],
        function_mode="prefer",
    )
    assert [item["id"] for item in results] == ["sequence-skill"]


def test_all_resource_mode_returns_skill_and_mcp():
    results = load_module().filter_resources(
        fixture_catalog(),
        resource="all",
        domains=["生命科学"],
        stages=["分析验证"],
        functions=["数据处理"],
        function_mode="prefer",
    )
    assert [item["id"] for item in results] == ["sequence-skill", "sequence-mcp"]


def test_resource_filter_can_select_only_mcp():
    results = load_module().filter_resources(
        fixture_catalog(),
        resource="mcp",
        domains=["生命科学"],
        stages=["分析验证"],
        functions=["验证评测"],
    )
    assert [item["id"] for item in results] == ["sequence-mcp"]


def test_function_options_report_counts_by_resource_type():
    options = load_module().function_options(
        fixture_catalog(),
        resource="all",
        domains=["生命科学"],
        stages=["分析验证"],
    )
    assert options == [
        {
            "function": "数据处理",
            "count": 1,
            "skill_count": 1,
            "mcp_count": 0,
            "examples": ["sequence-skill"],
        },
        {
            "function": "验证评测",
            "count": 1,
            "skill_count": 0,
            "mcp_count": 1,
            "examples": ["sequence-mcp"],
        },
    ]


def test_payload_preserves_resource_type_and_type_counts():
    results = load_module().filter_resources(
        fixture_catalog(),
        resource="all",
        domains=["生命科学"],
        stages=["分析验证"],
        functions=["数据处理"],
        function_mode="prefer",
    )
    payload = load_module().result_payload({}, results, function_mode="prefer")
    assert payload["counts"] == {"skill": 1, "mcp": 1}
    assert {item["resource_type"] for item in payload["resources"]} == {"skill", "mcp"}


def test_cli_parser_defaults_to_skill_and_accepts_explicit_all():
    parser = load_module().build_parser()
    assert parser.parse_args([]).resource == "skill"
    assert parser.parse_args(["--resource", "all"]).resource == "all"


def test_static_catalogs_share_dimensions_and_expected_counts():
    skill_catalog = json.loads(SKILL_CATALOG_PATH.read_text(encoding="utf-8"))
    mcp_catalog = json.loads(MCP_CATALOG_PATH.read_text(encoding="utf-8"))
    assert skill_catalog["dimensions"] == mcp_catalog["dimensions"]
    assert len(skill_catalog["skills"]) == 1391
    assert len(mcp_catalog["mcps"]) == 5643
    assert len(mcp_catalog["dimensions"]["domains"]) == 9
    assert len(mcp_catalog["dimensions"]["subdomains"]) == 42
    assert len(mcp_catalog["dimensions"]["stages"]) == 5
    assert len(mcp_catalog["dimensions"]["functions"]) == 17
    assert all(item["resource_type"] == "mcp" for item in mcp_catalog["mcps"])
    assert all(item["source_url"] for item in mcp_catalog["mcps"])
