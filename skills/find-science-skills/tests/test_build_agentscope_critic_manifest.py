import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "build_agentscope_critic_manifest.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("build_agentscope_manifest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def provider_report(workspace: Path, status="pass"):
    return {
        "status": status,
        "workspace": str(workspace.resolve()),
        "source_unchanged": True,
        "workspace_changes": ["outputs/verification-report.md"],
        "final_text": "final host answer",
        "context": [
            {"role": "user", "content": [{"type": "text", "text": "actual prompt"}]},
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "Write",
                        "input": '{"file_path":"report.md","content":"ok"}',
                    }
                ],
            },
        ],
    }


def test_build_manifest_uses_real_context_tool_calls(tmp_path):
    module = load_module()
    skill = tmp_path / "skill"
    (skill / "evals").mkdir(parents=True)
    (skill / "evals" / "evals.json").write_text(
        json.dumps({"evals": [{"id": "case-a", "prompt": "fixed prompt"}]}),
        encoding="utf-8",
    )
    root = tmp_path / "runs"
    for mode in ("with_skill", "without_skill"):
        workspace = root / mode / "case-1"
        (workspace / "outputs").mkdir(parents=True)
        (workspace / "outputs" / "verification-report.md").write_text(
            "report", encoding="utf-8"
        )
        (workspace / "provider-report.json").write_text(
            json.dumps(provider_report(workspace)), encoding="utf-8"
        )

    manifest = module.build_manifest(
        skill, root, ["case-1"], grade_artifact_output=True
    )

    run = manifest["runs"][0]
    assert run["prompt"] == "fixed prompt"
    assert run["with_skill"]["output_file"] == str(
        (root / "with_skill" / "case-1" / "outputs" / "verification-report.md").resolve()
    )
    assert run["with_skill"]["provider_final_text"] == "final host answer"
    assert run["with_skill"]["provider_prompt"] == "actual prompt"
    assert run["with_skill"]["tool_calls"] == [
        {
            "id": "write-1",
            "type": "function",
            "function": {
                "name": "Write",
                "arguments": '{"file_path":"report.md","content":"ok"}',
            },
        }
    ]


def test_build_manifest_defaults_to_host_final_text(tmp_path):
    module = load_module()
    skill = tmp_path / "skill"
    (skill / "evals").mkdir(parents=True)
    (skill / "evals" / "evals.json").write_text(
        json.dumps({"evals": [{"id": "case-a", "prompt": "fixed prompt"}]}),
        encoding="utf-8",
    )
    root = tmp_path / "runs"
    for mode in ("with_skill", "without_skill"):
        workspace = root / mode / "case-1"
        (workspace / "outputs").mkdir(parents=True)
        (workspace / "outputs" / "verification-report.md").write_text(
            "report", encoding="utf-8"
        )
        (workspace / "provider-report.json").write_text(
            json.dumps(provider_report(workspace)), encoding="utf-8"
        )

    manifest = module.build_manifest(skill, root, ["case-1"])

    assert manifest["runs"][0]["with_skill"]["output"] == "final host answer"
    assert "output_file" not in manifest["runs"][0]["with_skill"]


def test_build_manifest_rejects_nonpassing_provider_run(tmp_path):
    module = load_module()
    workspace = tmp_path / "case"
    workspace.mkdir()
    report = provider_report(workspace, status="provider_error")

    with pytest.raises(ValueError, match="not gradeable"):
        module.validate_report(report, workspace)


def test_validate_report_accepts_declared_artifact_path(tmp_path):
    module = load_module()
    workspace = tmp_path / "case"
    (workspace / "outputs").mkdir(parents=True)
    artifact = "outputs/methods.md"
    (workspace / artifact).write_text("methods", encoding="utf-8")
    report = provider_report(workspace)
    report["workspace_changes"] = [artifact]

    module.validate_report(report, workspace, artifact)


def test_manifest_grades_missing_baseline_artifact_as_failed_output(tmp_path):
    module = load_module()
    skill = tmp_path / "skill"
    (skill / "evals").mkdir(parents=True)
    (skill / "evals" / "evals.json").write_text(
        json.dumps(
            {
                "evals": [
                    {
                        "id": "artifact",
                        "prompt": "write report",
                        "mode": "artifact",
                        "artifact_path": "outputs/report.md",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    root = tmp_path / "runs"
    with_workspace = root / "with_skill" / "case-1"
    (with_workspace / "outputs").mkdir(parents=True)
    (with_workspace / "outputs" / "report.md").write_text("report", encoding="utf-8")
    with_report = provider_report(with_workspace)
    with_report["workspace_changes"] = ["outputs/report.md"]
    (with_workspace / "provider-report.json").write_text(json.dumps(with_report), encoding="utf-8")
    without_workspace = root / "without_skill" / "case-1"
    without_workspace.mkdir(parents=True)
    without_report = provider_report(without_workspace)
    without_report["workspace_changes"] = []
    (without_workspace / "provider-report.json").write_text(
        json.dumps(without_report), encoding="utf-8"
    )

    manifest = module.build_manifest(
        skill, root, ["case-1"], derive_case_contracts=True
    )

    with_spec = manifest["runs"][0]["with_skill"]
    without_spec = manifest["runs"][0]["without_skill"]
    assert with_spec["artifact_requirement"] == "pass"
    assert "output_file" in with_spec
    assert without_spec["artifact_requirement"] == "missing"
    assert "output_file" not in without_spec
    assert without_spec["outputs_dir"].endswith("without_skill\\case-1\\outputs")


def test_build_manifest_accepts_guidance_run_without_artifact(tmp_path):
    module = load_module()
    skill = tmp_path / "skill"
    (skill / "evals").mkdir(parents=True)
    (skill / "evals" / "evals.json").write_text(
        json.dumps({"evals": [{"id": "case-a", "prompt": "fixed prompt"}]}),
        encoding="utf-8",
    )
    root = tmp_path / "runs"
    for mode in ("with_skill", "without_skill"):
        workspace = root / mode / "case-1"
        workspace.mkdir(parents=True)
        report = provider_report(workspace)
        report["workspace_changes"] = []
        report["context"] = [
            {"role": "user", "content": [{"type": "text", "text": "actual prompt"}]}
        ]
        (workspace / "provider-report.json").write_text(
            json.dumps(report), encoding="utf-8"
        )

    manifest = module.build_manifest(
        skill, root, ["case-1"], artifact_required=False
    )

    run = manifest["runs"][0]
    assert run["with_skill"]["output"] == "final host answer"
    assert run["with_skill"]["tool_calls"] == []
    assert run["with_skill"]["artifact_requirement"] == "not_applicable"


def test_build_manifest_derives_mixed_case_contracts_from_evals(tmp_path):
    module = load_module()
    skill = tmp_path / "skill"
    (skill / "evals").mkdir(parents=True)
    (skill / "evals" / "evals.json").write_text(
        json.dumps(
            {
                "evals": [
                    {"id": "guide", "prompt": "guide", "mode": "guidance"},
                    {
                        "id": "artifact",
                        "prompt": "write",
                        "mode": "artifact",
                        "artifact_path": "outputs/methods.md",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    root = tmp_path / "runs"
    for mode in ("with_skill", "without_skill"):
        guide = root / mode / "case-1"
        guide.mkdir(parents=True)
        guide_report = provider_report(guide)
        guide_report["workspace_changes"] = []
        (guide / "provider-report.json").write_text(
            json.dumps(guide_report), encoding="utf-8"
        )
        artifact = root / mode / "case-2"
        (artifact / "outputs").mkdir(parents=True)
        (artifact / "outputs" / "methods.md").write_text("methods", encoding="utf-8")
        artifact_report = provider_report(artifact)
        artifact_report["workspace_changes"] = ["outputs/methods.md"]
        (artifact / "provider-report.json").write_text(
            json.dumps(artifact_report), encoding="utf-8"
        )

    manifest = module.build_manifest(
        skill,
        root,
        ["case-1", "case-2"],
        derive_case_contracts=True,
    )

    assert manifest["runs"][0]["with_skill"]["artifact_requirement"] == "not_applicable"
    assert "output_file" not in manifest["runs"][0]["with_skill"]
    assert manifest["runs"][1]["with_skill"]["output_file"].endswith(
        "outputs\\methods.md"
    )
