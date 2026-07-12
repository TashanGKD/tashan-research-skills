import importlib.util
import pathlib


SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_DIR / "scripts" / "finalize_critic_scores.py"


def load_module():
    spec = importlib.util.spec_from_file_location("finalize_critic_scores", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def base_record(**overrides):
    record = {
        "id": "demo",
        "critic_content_score": 92,
        "critic_evidence_level": "full_source",
        "critic_model": "deepseek-v4-flash-260425",
        "critic_source_sha256": "abc",
        "critic_package_status": "pass",
        "critic_verdict": "recommend",
        "errors": [],
        "warnings": [],
    }
    record.update(overrides)
    return record


def test_static_failure_overrides_high_model_score():
    module = load_module()
    result = module.finalize_record(
        base_record(
            critic_package_status="fail",
            errors=["Referenced file does not exist: references/missing.md"],
        )
    )
    assert result["model_source_review_score"] == 92
    assert result["static_validation_status"] == "fail"
    assert result["evaluation_status"] == "static_failed"
    assert result["install_recommendation"] == "fix_first"


def test_metadata_only_is_unverified_and_has_no_comparable_score():
    module = load_module()
    result = module.finalize_record(
        base_record(
            critic_content_score=61,
            critic_evidence_level="metadata_only",
            critic_package_status="source_unavailable",
        )
    )
    assert result["model_source_review_score"] is None
    assert result["legacy_metadata_score"] == 61
    assert result["evaluation_status"] == "unverified"
    assert result["install_recommendation"] == "unverified"


def test_checkout_directory_mismatch_alone_is_normalized():
    module = load_module()
    result = module.finalize_record(
        base_record(
            critic_package_status="fail",
            errors=[
                "Directory name 'owner__repo' must match skill name 'demo'",
            ],
        )
    )
    assert result["static_validation_status"] == "pass"
    assert result["static_validation_mode"] == "normalized_install_directory"
    assert result["static_validation_errors"] == []
    assert result["evaluation_status"] == "needs_behavior_and_trigger"


def test_checkout_normalization_does_not_hide_substantive_errors():
    module = load_module()
    result = module.finalize_record(
        base_record(
            critic_package_status="fail",
            errors=[
                "Directory name 'owner__repo' must match skill name 'demo'",
                "Referenced file does not exist: scripts/run.py",
            ],
        )
    )
    assert result["static_validation_status"] == "fail"
    assert result["static_validation_errors"] == [
        "Referenced file does not exist: scripts/run.py"
    ]
    assert result["install_recommendation"] == "fix_first"


def test_recommend_install_requires_all_three_evaluation_layers():
    module = load_module()
    incomplete = module.finalize_record(base_record())
    assert incomplete["install_recommendation"] == "not_yet_evaluated"

    complete = module.finalize_record(
        base_record(
            behavior_evaluation={"status": "pass", "pass_rate_delta": 0.5},
            trigger_evaluation={"status": "pass", "trigger_rate": 0.9},
        )
    )
    assert complete["evaluation_status"] == "complete"
    assert complete["install_recommendation"] == "recommend_install"


def test_security_failure_is_rejected():
    module = load_module()
    result = module.finalize_record(
        base_record(
            critic_package_status="fail",
            errors=["Security (hardcoded-credential) at scripts/run.py:1"],
        )
    )
    assert result["evaluation_status"] == "security_failed"
    assert result["install_recommendation"] == "reject"
