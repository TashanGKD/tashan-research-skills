import importlib.util
import json
import pathlib

import pytest


SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_DIR / "scripts" / "filter_science_skills.py"
CATALOG_PATH = SKILL_DIR / "data" / "science_skill_catalog.json"


def load_module():
    spec = importlib.util.spec_from_file_location("filter_science_skills", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def fixture_catalog():
    return {
        "dimensions": {
            "domains": ["生命科学", "物质科学"],
            "subdomains": ["生物信息学", "药物发现"],
            "stages": ["执行采集", "分析验证"],
            "functions": ["数据处理", "模拟建模"],
        },
        "skills": [
            {
                "id": "restricted-skill",
                "domain": "生命科学",
                "subdomain": "生物信息学",
                "stage": "分析验证",
                "function": "数据处理",
                "readiness": "restricted",
                "quality_score": 99,
            },
            {
                "id": "trusted-low",
                "domain": "生命科学",
                "subdomain": "生物信息学",
                "stage": "分析验证",
                "function": "数据处理",
                "readiness": "trusted",
                "quality_score": 60,
            },
            {
                "id": "trusted-high",
                "domain": "生命科学",
                "subdomain": "生物信息学",
                "stage": "分析验证",
                "function": "数据处理",
                "readiness": "trusted",
                "quality_score": 80,
            },
            {
                "id": "docking",
                "domain": "物质科学",
                "subdomain": "药物发现",
                "stage": "执行采集",
                "function": "模拟建模",
                "readiness": "provisional",
                "quality_score": 90,
            },
        ],
    }


def test_filter_uses_exact_three_dimension_intersection_and_stable_order():
    module = load_module()
    results = module.filter_skills(
        fixture_catalog(),
        domains=["生命科学"],
        stages=["分析验证"],
        functions=["数据处理"],
    )
    assert [item["id"] for item in results] == [
        "trusted-high",
        "trusted-low",
        "restricted-skill",
    ]


def test_filter_allows_multiple_values_with_or_inside_each_dimension():
    module = load_module()
    results = module.filter_skills(
        fixture_catalog(),
        domains=["生命科学", "物质科学"],
        stages=["执行采集", "分析验证"],
        functions=["数据处理", "模拟建模"],
    )
    assert {item["id"] for item in results} == {
        "trusted-high",
        "trusted-low",
        "restricted-skill",
        "docking",
    }


def test_preferred_function_mode_keeps_domain_stage_fallbacks_after_exact_matches():
    module = load_module()
    results = module.filter_skills(
        fixture_catalog(),
        domains=["生命科学"],
        stages=["分析验证"],
        functions=["模拟建模"],
        function_mode="prefer",
    )
    assert [item["id"] for item in results] == [
        "trusted-high",
        "trusted-low",
        "restricted-skill",
    ]
    assert all(item["function_match"] is False for item in results)


def test_preferred_function_mode_ranks_exact_function_before_fallbacks():
    catalog = fixture_catalog()
    catalog["skills"].append(
        {
            "id": "preferred-function",
            "domain": "生命科学",
            "subdomain": "生物信息学",
            "stage": "分析验证",
            "function": "模拟建模",
            "readiness": "provisional",
            "quality_score": 50,
        }
    )
    results = load_module().filter_skills(
        catalog,
        domains=["生命科学"],
        stages=["分析验证"],
        functions=["模拟建模"],
        function_mode="prefer",
    )
    assert results[0]["id"] == "preferred-function"
    assert results[0]["function_match"] is True


def test_function_options_summarize_domain_stage_before_strict_filtering():
    module = load_module()
    options = module.function_options(
        fixture_catalog(),
        domains=["生命科学"],
        stages=["分析验证"],
    )
    assert options == [
        {
            "function": "数据处理",
            "count": 3,
            "trusted_count": 2,
            "examples": ["trusted-high", "trusted-low", "restricted-skill"],
        }
    ]


def test_result_payload_exposes_host_decision_contract_and_compact_evidence():
    module = load_module()
    results = module.filter_skills(
        fixture_catalog(),
        domains=["生命科学"],
        stages=["分析验证"],
        functions=["数据处理"],
        function_mode="prefer",
    )
    results[0]["classification_rationale"] = "review process detail"
    results[0]["review_status"] = "metadata_reviewed"
    payload = module.result_payload(
        {
            "domains": ["生命科学"],
            "subdomains": [],
            "stages": ["分析验证"],
            "functions": ["数据处理"],
        },
        results,
        function_mode="prefer",
    )
    assert payload["decision_contract"] == {
        "quality_order_is_semantic_relevance": False,
        "direct_match_requires": [
            "research_object_or_data",
            "requested_action_or_output",
        ],
        "maximum_recommendations": 5,
        "no_direct_match": "return_gap_or_ask_clarification",
    }
    assert "classification_rationale" not in payload["skills"][0]
    assert "review_status" not in payload["skills"][0]
    assert payload["skills"][0]["function_match"] is True


def test_result_payload_can_preserve_full_catalog_records_for_audit():
    module = load_module()
    results = module.filter_skills(
        fixture_catalog(),
        domains=["生命科学"],
        stages=["分析验证"],
        functions=["数据处理"],
    )
    results[0]["classification_rationale"] = "source-backed rationale"
    payload = module.result_payload({}, results, function_mode="strict", full=True)
    assert payload["skills"][0]["classification_rationale"] == "source-backed rationale"


def test_subdomain_is_an_optional_exact_filter():
    module = load_module()
    results = module.filter_skills(
        fixture_catalog(),
        domains=["物质科学"],
        subdomains=["药物发现"],
        stages=["执行采集"],
        functions=["模拟建模"],
    )
    assert [item["id"] for item in results] == ["docking"]


def test_unknown_dimension_value_is_rejected_instead_of_silently_relaxed():
    module = load_module()
    with pytest.raises(ValueError, match="unknown domain"):
        module.filter_skills(
            fixture_catalog(),
            domains=["不存在的领域"],
            stages=["分析验证"],
            functions=["数据处理"],
        )


def test_generated_catalog_is_complete_and_uses_normalized_names():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    assert catalog["schema"] == "science_skill_catalog_v1"
    assert catalog["source_skill_count"] == 1398
    assert catalog["excluded_non_scientific_count"] == 7
    assert len(catalog["skills"]) == 1391
    assert len(catalog["dimensions"]["domains"]) == 9
    assert len(catalog["dimensions"]["stages"]) == 5
    assert len(catalog["dimensions"]["functions"]) == 17
    required = {
        "id",
        "name",
        "summary",
        "domain",
        "subdomain",
        "stage",
        "function",
        "quality_score",
        "readiness",
        "source_repository",
        "source_path",
    }
    assert all(required <= set(skill) for skill in catalog["skills"])
    assert all("group" not in skill and "family" not in skill for skill in catalog["skills"])


def test_openfoam_simulators_are_classified_as_simulation_not_experiment_execution():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    by_id = {skill["id"]: skill for skill in catalog["skills"]}
    for skill_id in ("hpc-openfoam", "openfoam-agent", "openfoam-sim"):
        assert by_id[skill_id]["function"] == "模拟建模"
