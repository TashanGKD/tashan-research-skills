import importlib.util
import pathlib

import pytest


SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_DIR / "scripts" / "apply_critic_evaluation.py"


def load_module():
    spec = importlib.util.spec_from_file_location("apply_critic_evaluation", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def fixture_scorecard(static_status="pass"):
    return {
        "schema": "science_skill_critic_scores_v2",
        "scores": [
            {
                "id": "demo",
                "critic_source_sha256": "abc",
                "model_source_review_verdict": "recommend",
                "static_validation_status": static_status,
                "static_validation_errors": [],
            }
        ],
    }


def fixture_report(source_hash="abc"):
    return {
        "schema": "science_skill_critic_evaluation_v1",
        "id": "demo",
        "critic_source_sha256": source_hash,
        "formal_kernel_run": True,
        "behavior_evaluation": {"status": "pass", "pass_rate_delta": 1.0},
        "trigger_evaluation": {"status": "pass", "accuracy": 1.0},
    }


def test_apply_complete_report_enables_install_recommendation():
    module = load_module()
    result = module.apply_report(fixture_scorecard(), fixture_report())
    record = result["scores"][0]
    assert record["evaluation_status"] == "complete"
    assert record["install_recommendation"] == "recommend_install"


def test_apply_rejects_stale_source_hash():
    module = load_module()
    with pytest.raises(ValueError, match="source hash"):
        module.apply_report(fixture_scorecard(), fixture_report("stale"))


def test_apply_cannot_override_static_failure():
    module = load_module()
    with pytest.raises(ValueError, match="static validation failure"):
        module.apply_report(fixture_scorecard("fail"), fixture_report())


def test_non_kernel_review_is_preserved_but_not_an_install_recommendation():
    module = load_module()
    report = fixture_report()
    report["formal_kernel_run"] = False
    result = module.apply_report(fixture_scorecard(), report)
    record = result["scores"][0]
    assert record["behavior_tested"] is True
    assert record["trigger_tested"] is True
    assert record["evaluation_status"] == "provisional_behavior_and_trigger"
    assert record["install_recommendation"] == "not_yet_evaluated"
