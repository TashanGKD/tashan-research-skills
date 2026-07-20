import importlib.util
import json
import pathlib

import pytest


SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_DIR / "scripts" / "review_critic_execution_mode.py"


def load_module():
    spec = importlib.util.spec_from_file_location("review_critic_execution_mode", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def source_package(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "SKILL.md").write_text(
        "# Demo\nUse the audit tool.\nReturn the findings in chat.\n",
        encoding="utf-8",
    )
    return root


def valid_payload(module, root, mode="tool"):
    manifest = module.tree_manifest(root)
    skill_sha = module.sha256(root / "SKILL.md")
    return {
        "schema": "critic_execution_mode_review_v1",
        "skill_id": "demo-skill",
        "source_tree_sha256": module.manifest_sha256(manifest),
        "review_status": "source_reviewed",
        "execution_mode": mode,
        "observed_modes": [mode],
        "confidence": "high",
        "primary_output": {
            "kind": "tool_result" if mode == "tool" else "conversation",
            "description": "An audit result returned to the user.",
        },
        "required_runtime": ["audit tool"] if mode == "tool" else [],
        "side_effects": [],
        "evidence": [
            {
                "path": "SKILL.md",
                "sha256": skill_sha,
                "excerpt": "Use the audit tool.",
                "supports": "runtime",
            },
            {
                "path": "SKILL.md",
                "sha256": skill_sha,
                "excerpt": "Return the findings in chat.",
                "supports": "primary_output",
            },
        ],
        "rationale": "The source requires a tool and returns its result without a file deliverable.",
    }


def test_prompt_defines_delivery_semantics_and_requires_exact_source_evidence(tmp_path):
    module = load_module()
    root = source_package(tmp_path)
    prompt = module.build_review_prompt("demo-skill", root)

    assert "guidance" in prompt
    assert "artifact" in prompt
    assert "tool" in prompt
    assert "hybrid" in prompt
    assert "exact excerpt" in prompt
    assert "not its name" in prompt
    assert "research taxonomy" in prompt
    assert "skill ID rule" not in prompt
    assert 'review_status must be exactly "source_reviewed"' in prompt
    assert 'execution_mode must be exactly one of "guidance", "artifact", "tool", "hybrid"' in prompt
    assert 'required_runtime and side_effects must always be JSON arrays' in prompt
    assert 'will use the key `excerpt`' in prompt
    assert "A stop/fallback message does not turn" in prompt
    assert 'hybrid must use primary_output.kind "mixed"' in prompt
    assert "artifact + tool => hybrid" in prompt
    assert "one contiguous source span" in prompt
    assert "no ellipsis, paraphrase, or merged lines" in prompt
    assert "line_start" in prompt
    assert "line_end" in prompt
    assert "Do not copy source prose into the JSON" in prompt


def test_prompt_requires_mounted_skill_as_the_first_action(tmp_path):
    module = load_module()
    root = source_package(tmp_path)
    prompt = module.build_review_prompt("demo-skill", root)
    normalized = " ".join(prompt.split())

    invocation = "Your first action must call the mounted Skill tool exactly once"
    snapshot = "Hash-backed source package:"
    assert invocation in normalized
    assert "Do not analyze the embedded source snapshot before that call returns" in normalized
    assert normalized.index(invocation) < normalized.index(snapshot)


def test_repair_prompt_requires_mounted_skill_as_the_first_action(tmp_path):
    module = load_module()
    root = source_package(tmp_path)
    prompt = module.build_repair_prompt(
        "demo-skill",
        root,
        {"schema": "wrong"},
        "execution-mode review identity or schema is invalid",
    )
    normalized = " ".join(prompt.split())

    invocation = "Your first action must call the mounted Skill tool exactly once"
    snapshot = "Hash-backed source package:"
    assert invocation in normalized
    assert normalized.index(invocation) < normalized.index(snapshot)


def test_validate_review_materializes_source_excerpt_from_line_anchors(tmp_path):
    module = load_module()
    root = source_package(tmp_path)
    payload = valid_payload(module, root)
    payload["evidence"][0].pop("excerpt")
    payload["evidence"][0]["line_start"] = 2
    payload["evidence"][0]["line_end"] = 2

    result = module.validate_review_payload(payload, "demo-skill", root)

    assert result["evidence"][0]["excerpt"] == "Use the audit tool."
    assert result["evidence"][0]["line_start"] == 2
    assert result["evidence"][0]["line_end"] == 2


def test_validate_review_rejects_out_of_range_line_anchors(tmp_path):
    module = load_module()
    root = source_package(tmp_path)
    payload = valid_payload(module, root)
    payload["evidence"][0].pop("excerpt")
    payload["evidence"][0]["line_start"] = 20
    payload["evidence"][0]["line_end"] = 20

    with pytest.raises(ValueError, match="line range is invalid"):
        module.validate_review_payload(payload, "demo-skill", root)


def test_validate_review_accepts_source_backed_tool_mode(tmp_path):
    module = load_module()
    root = source_package(tmp_path)
    payload = valid_payload(module, root)

    result = module.validate_review_payload(payload, "demo-skill", root)

    assert result["execution_mode"] == "tool"
    assert result["review_status"] == "source_reviewed"


def test_validate_review_rejects_evidence_not_present_in_source(tmp_path):
    module = load_module()
    root = source_package(tmp_path)
    payload = valid_payload(module, root)
    payload["evidence"][0]["excerpt"] = "Invented capability"

    with pytest.raises(ValueError, match="excerpt is not present"):
        module.validate_review_payload(payload, "demo-skill", root)


def test_validate_review_rejects_guidance_with_runtime_or_side_effects(tmp_path):
    module = load_module()
    root = source_package(tmp_path)
    payload = valid_payload(module, root, mode="guidance")
    payload["required_runtime"] = ["audit tool"]

    with pytest.raises(ValueError, match="guidance mode cannot require runtime"):
        module.validate_review_payload(payload, "demo-skill", root)


def test_validate_review_accepts_explicit_needs_review_without_guessing(tmp_path):
    module = load_module()
    root = source_package(tmp_path)
    payload = valid_payload(module, root)
    payload.update(
        {
            "review_status": "needs_mode_review",
            "execution_mode": None,
            "observed_modes": [],
            "confidence": "low",
            "primary_output": None,
            "required_runtime": [],
            "side_effects": [],
            "rationale": "The source describes incompatible primary deliverables.",
        }
    )

    result = module.validate_review_payload(payload, "demo-skill", root)

    assert result["execution_mode"] is None


def test_write_review_preserves_provider_and_source_hashes(tmp_path):
    module = load_module()
    root = source_package(tmp_path)
    payload = valid_payload(module, root)
    report = tmp_path / "provider-report.json"
    report.write_text(
        json.dumps(
            {
                "status": "pass",
                "source_unchanged": True,
                "final_text": json.dumps(payload),
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "execution-mode-review.json"

    result = module.write_validated_review(
        "demo-skill",
        root,
        report,
        output,
    )

    stored = json.loads(output.read_text(encoding="utf-8"))
    assert stored["provider_report_sha256"] == module.sha256(report)
    assert stored["source_tree_sha256"] == result["source_tree_sha256"]


def test_write_review_archives_strict_validation_failure(tmp_path):
    module = load_module()
    root = source_package(tmp_path)
    payload = valid_payload(module, root)
    payload["evidence"][0]["excerpt"] = "Invented source claim"
    report = tmp_path / "provider-report.json"
    report.write_text(
        json.dumps(
            {
                "status": "pass",
                "source_unchanged": True,
                "final_text": json.dumps(payload),
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="excerpt is not present"):
        module.write_validated_review(
            "demo-skill",
            root,
            report,
            tmp_path / "execution-mode-review.json",
        )

    error = json.loads(
        (tmp_path / "execution-mode-validation-error.json").read_text(
            encoding="utf-8"
        )
    )
    assert error["provider_report_sha256"] == module.sha256(report)
    assert error["error_type"] == "ValueError"
    repair_prompt = (tmp_path / "execution-mode-repair-prompt.txt").read_text(
        encoding="utf-8"
    )
    assert "Invented source claim" in repair_prompt
    assert "excerpt is not present" in repair_prompt
    assert "Hash-backed source package" in repair_prompt


def test_write_review_builds_repair_prompt_for_unparseable_response(tmp_path):
    module = load_module()
    root = source_package(tmp_path)
    report = tmp_path / "provider-report.json"
    report.write_text(
        json.dumps(
            {
                "status": "pass",
                "source_unchanged": True,
                "final_text": "I reviewed the source but did not return JSON.",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(json.JSONDecodeError):
        module.write_validated_review(
            "demo-skill",
            root,
            report,
            tmp_path / "execution-mode-review.json",
        )

    repair_prompt = (tmp_path / "execution-mode-repair-prompt.txt").read_text(
        encoding="utf-8"
    )
    assert "I reviewed the source but did not return JSON." in repair_prompt
    assert "strict JSON only" in repair_prompt
    assert "Hash-backed source package" in repair_prompt


def test_consume_single_repair_report_accepts_once_and_rejects_second(tmp_path):
    module = load_module()
    root = source_package(tmp_path)
    report = tmp_path / "repair-provider-report.json"
    report.write_text(
        json.dumps(
            {
                "status": "pass",
                "source_unchanged": True,
                "final_text": json.dumps(valid_payload(module, root)),
            }
        ),
        encoding="utf-8",
    )

    stored = module.consume_single_repair_report(
        "demo-skill", root, tmp_path, report
    )

    assert stored["repair_attempt_count"] == 1
    second = tmp_path / "second-provider-report.json"
    second.write_text(report.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="already consumed"):
        module.consume_single_repair_report("demo-skill", root, tmp_path, second)
