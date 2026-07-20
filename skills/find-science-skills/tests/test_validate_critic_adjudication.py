import importlib.util
import json
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "validate_critic_adjudication.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("validate_critic_adjudication", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def stage(tmp_path, *, gate="ready_for_scorecard", final_overrides=None, prose="结论：建议安装"):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    evidence = {
        "skill_id": "demo-skill",
        "execution_model": "deepseek-v4-flash-aistar",
        "provider_failures": [],
        "behavior": {"with_passed": 3, "without_passed": 0},
        "trigger_accuracy": 1.0,
        "always_failing_assertions": (
            0 if gate in {"ready_for_scorecard", "ready_for_fix_first"} else 2
        ),
        "gate": gate,
    }
    write_json(workspace / "evidence-gate.json", evidence)
    write_json(workspace / "source-invariants.json", {"all_unchanged": True})
    write_json(workspace / "static_validation.json", {"valid": True})
    decision = {
        "schema": "critic_final_adjudication_v1",
        "skill_id": "demo-skill",
        "verdict": "recommend_install" if gate == "ready_for_scorecard" else "fix_first",
        "execution_model": "deepseek-v4-flash-aistar",
        "provider_status": "pass",
        "provider_failure_count": 0,
        "with_skill_passed": 3,
        "without_skill_passed": 0,
        "trigger_accuracy": 1.0,
        "always_failing_assertions": evidence["always_failing_assertions"],
        "source_unchanged": True,
        "static_valid": True,
        "primary_failure_class": (
            "none"
            if gate == "ready_for_scorecard"
            else "skill_quality"
            if gate == "ready_for_fix_first"
            else "eval_invalid"
        ),
        "scorecard_write_recommendation": gate
        in {"ready_for_scorecard", "ready_for_fix_first"},
    }
    decision.update(final_overrides or {})
    report = {
        "status": "pass",
        "skill_invocation_count": 1,
        "source_unchanged": True,
        "workspace_changes": [],
        "final_text": prose + "\n```json\n" + json.dumps(decision) + "\n```",
    }
    write_json(workspace / "provider-report.json", report)
    return workspace


def test_accepts_exact_evidence_backed_adjudication(tmp_path):
    module = load_module()
    result = module.validate_adjudication(stage(tmp_path))
    assert result["status"] == "pass"
    assert result["scorecard_write_allowed"] is True


def test_accepts_evidence_backed_fix_first_adjudication(tmp_path):
    module = load_module()
    workspace = stage(
        tmp_path,
        gate="ready_for_fix_first",
        prose="结论：先修复。问题属于技能触发边界，而非 provider 故障。",
    )
    result = module.validate_adjudication(workspace)
    assert result["status"] == "pass"
    assert result["scorecard_write_allowed"] is True


def test_rejects_missing_structured_decision(tmp_path):
    module = load_module()
    workspace = stage(tmp_path)
    report = json.loads((workspace / "provider-report.json").read_text())
    report["final_text"] = "结论：建议安装"
    write_json(workspace / "provider-report.json", report)
    result = module.validate_adjudication(workspace)
    assert result["status"] == "fail"
    assert "structured_decision_missing" in result["errors"]


def test_rejects_execution_model_drift(tmp_path):
    module = load_module()
    workspace = stage(tmp_path, final_overrides={"execution_model": "local-static-grader"})
    result = module.validate_adjudication(workspace)
    assert "execution_model_mismatch" in result["errors"]


def test_rejects_false_provider_failure_attribution(tmp_path):
    module = load_module()
    workspace = stage(
        tmp_path,
        prose="结论：先修复。失败来自 provider、权限、超时或传输失败。",
        final_overrides={"verdict": "fix_first", "primary_failure_class": "provider_failure"},
    )
    result = module.validate_adjudication(workspace)
    assert "primary_failure_class_mismatch" in result["errors"]
    assert "prose_provider_failure_contradiction" in result["errors"]


def test_codex_adjudication_gate_cannot_recommend_scorecard_write(tmp_path):
    module = load_module()
    workspace = stage(
        tmp_path,
        gate="codex_adjudication",
        final_overrides={"scorecard_write_recommendation": True},
        prose="结论：先修复",
    )
    result = module.validate_adjudication(workspace)
    assert "scorecard_write_recommendation_mismatch" in result["errors"]
    assert result["scorecard_write_allowed"] is False


def test_accepts_explicit_statement_that_provider_had_no_failures(tmp_path):
    module = load_module()
    workspace = stage(
        tmp_path,
        prose="Provider failures list is empty; provider 无故障，7/7 均通过。",
    )
    result = module.validate_adjudication(workspace)
    assert result["status"] == "pass"


def test_can_validate_a_separate_repair_report(tmp_path):
    module = load_module()
    workspace = stage(tmp_path)
    original = workspace / "provider-report.json"
    repair = workspace / "repair-report.json"
    repair.write_bytes(original.read_bytes())
    result = module.validate_adjudication(workspace, repair)
    assert result["status"] == "pass"
