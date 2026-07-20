import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = (
    Path(__file__).parents[1] / "scripts" / "stage_direct_critic_replay.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("direct_replay", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def make_evidence(root: Path) -> None:
    skill = root / "eval_skill"
    (skill / "evals").mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: sample\ndescription: Sample research helper.\n---\n# Sample\n",
        encoding="utf-8",
    )
    write_json(skill / "evals" / "evals.json", {"skill_name": "sample", "evals": []})
    write_json(skill / "evals" / "trigger_queries.json", [])
    for name in (
        "runs-manifest.json",
        "trigger-decisions.json",
        "behavior-grader.json",
        "trigger-grader.json",
    ):
        write_json(root / name, {})
    write_json(root / "evidence-gate.json", {"gate": "ready_for_scorecard"})
    for mode in ("with_skill", "without_skill"):
        for index in range(1, 4):
            write_json(
                root / mode / f"case-{index}" / "provider-report.json",
                {
                    "status": "pass",
                    "source_unchanged": mode == "with_skill",
                    "source_before": {"sha256": "same"} if mode == "with_skill" else None,
                    "source_after": {"sha256": "same"} if mode == "with_skill" else None,
                    "workspace_changes": [],
                },
            )
    write_json(root / "triggers" / "batch-1" / "provider-report.json", {"status": "pass"})


def test_stage_replay_copies_minimal_evidence_and_checks_invariants(tmp_path):
    module = load_module()
    evidence = tmp_path / "evidence"
    output = tmp_path / "replay"
    make_evidence(evidence)

    result = module.stage_replay(evidence, output, "sample")

    assert result["source_invariants"]["all_unchanged"] is True
    assert result["source_invariants"]["provider_pass_count"] == 7
    assert (output / "sample" / "SKILL.md").is_file()
    assert (output / "provider-workspace" / "evidence" / "sample" / "SKILL.md").is_file()
    assert (output / "evidence-manifest.json").is_file()
    assert (output / "provider-prompt.txt").is_file()
    assert len(result["allowed_commands"]) == 2
    assert "fresh isolated execution evidence" in result["prompt"]
    assert '"schema": "critic_final_adjudication_v1"' in result["prompt"]
    assert "do not infer a provider failure" in result["prompt"]
    assert "do not call any other tool" in result["prompt"]
    assert "ready_for_scorecard or ready_for_fix_first" in result["prompt"]
    assert "evidence/sample/SKILL.md" in result["prompt"]
    assert "Do not use absolute paths" in result["prompt"]
    assert all(not command.startswith("cd ") for command in result["allowed_commands"])


@pytest.mark.parametrize("gate", [None, "codex_adjudication", "unknown"])
def test_stage_replay_rejects_non_writable_evidence_before_provider(tmp_path, gate):
    module = load_module()
    evidence = tmp_path / "evidence"
    make_evidence(evidence)
    write_json(evidence / "evidence-gate.json", {"gate": gate})

    with pytest.raises(ValueError, match="evidence gate is not scorecard-writable"):
        module.stage_replay(evidence, tmp_path / "replay", "sample")

    assert not (tmp_path / "replay").exists()
