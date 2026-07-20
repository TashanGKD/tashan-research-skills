import importlib.util
import json
import pathlib

import pytest


SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_DIR / "scripts" / "author_critic_eval_pack.py"


def load_module():
    spec = importlib.util.spec_from_file_location("author_critic_eval_pack", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def valid_payload(skill_type="guidance"):
    cases = []
    for index in range(3):
        case = {
            "id": f"case-{index + 1}",
            "prompt": f"Analyze research scenario {index + 1} and give a concise decision.",
            "mode": "guidance",
            "assertions": [
                {"type": "contains", "value": f"Decision {index + 1}"},
                {"type": "regex", "value": r"(?i)limitation|boundary"},
            ],
            "file_assertions": [],
            "tool_assertions": [],
            "artifact_path": None,
            "allowed_commands": [],
            "fixtures": [],
        }
        cases.append(case)
    if skill_type != "guidance":
        cases[0].update(
            {
                "mode": "artifact",
                "artifact_path": "outputs/report.md",
                "file_assertions": [
                    {"type": "file-exists", "path": "report.md"},
                    {
                        "type": "file-contains",
                        "path": "report.md",
                        "value": "Decision 1",
                    },
                ],
            }
        )
    return {
        "schema": "critic_eval_author_v1",
        "skill_id": "demo-skill",
        "skill_type": skill_type,
        "cases": cases,
        "triggers": [
            {"query": f"use demo skill for task {index}", "should_trigger": True}
            for index in range(4)
        ]
        + [
            {"query": f"near miss request {index}", "should_trigger": False}
            for index in range(4)
        ],
        "author_rationale": "Three distinct source-backed tasks.",
        "self_review": {
            "source_fidelity": True,
            "offline_feasibility": True,
            "prompt_trigger_separation": True,
            "assertion_robustness": True,
            "artifact_evidence": True,
            "notes": "Checked against the mounted source before returning JSON.",
        },
    }


def test_validate_author_payload_rejects_fabricated_numeric_regex_identifier():
    module = load_module()
    payload = valid_payload()
    payload["cases"][1]["prompt"] = (
        "An output file is empty and the log contains errors. Report the verification result."
    )
    payload["cases"][1]["assertions"] = [
        {"type": "regex", "value": r"Verification FAILED for stage-\d+"}
    ]

    with pytest.raises(ValueError, match="numeric identifier absent from its prompt"):
        module.validate_author_payload(payload, "demo-skill", "guidance")


def execution_mode_review(module, source, mode="guidance", status="source_reviewed"):
    mode_to_output = {
        "guidance": "conversation",
        "artifact": "file",
        "tool": "tool_result",
        "hybrid": "mixed",
    }
    payload = {
        "schema": "critic_execution_mode_review_v1",
        "skill_id": "demo-skill",
        "source_tree_sha256": module.manifest_sha256(module.tree_manifest(source)),
        "review_status": status,
        "execution_mode": mode,
        "observed_modes": [mode] if mode != "hybrid" else ["artifact", "tool"],
        "confidence": "high",
        "primary_output": {
            "kind": mode_to_output[mode],
            "description": "Source-backed primary delivery.",
        },
        "required_runtime": [],
        "side_effects": [],
        "evidence": [],
        "rationale": "Reviewed against the complete source package.",
        "provider_report_sha256": "a" * 64,
    }
    if status == "needs_mode_review":
        payload.update(
            {
                "execution_mode": None,
                "observed_modes": [],
                "confidence": "low",
                "primary_output": None,
            }
        )
    return payload


def test_execution_mode_review_maps_source_backed_delivery_to_eval_type(tmp_path):
    module = load_module()
    source = tmp_path / "source"
    source.mkdir()
    (source / "SKILL.md").write_text("# Demo\nWrite a report.\n", encoding="utf-8")
    review_path = tmp_path / "execution-mode-review.json"
    review_path.write_text(
        json.dumps(execution_mode_review(module, source, mode="artifact")),
        encoding="utf-8",
    )

    resolved = module.load_execution_mode_review(review_path, "demo-skill", source)

    assert resolved["execution_mode"] == "artifact"
    assert resolved["skill_type"] == "executable"
    assert resolved["review_sha256"] == module.sha256(review_path)


def test_author_prompt_requires_compact_json_without_dropping_contract_fields():
    module = load_module()

    prompt = module.build_author_prompt(
        "demo-skill",
        "guidance",
        source_snapshot="# Demo\nGive source-backed guidance.\n",
    )

    assert "Return one compact JSON object only" in prompt
    assert "Do not emit analysis, reasoning, commentary, or Markdown fences" in prompt
    assert "Do not repeat or summarize the embedded source" in prompt
    assert "one concise sentence each" in prompt
    assert "exactly three" in prompt
    assert "exactly eight" in prompt
    assert "author_rationale" in prompt
    assert "self_review" in prompt
    assert "file_assertions" in prompt
    assert "tool_assertions" in prompt


def test_author_prompt_treats_source_mode_and_primary_output_as_hard_contract():
    module = load_module()

    prompt = module.build_author_prompt(
        "demo-skill",
        "executable",
        source_snapshot="# Demo\nWrite writing_blueprint.md.\n",
        mode_contract={
            "execution_mode": "artifact",
            "observed_modes": ["artifact"],
            "primary_output": {"path": "writing_blueprint.md"},
        },
    )

    assert "Every case must preserve the source-backed execution mode" in prompt
    assert "Do not relabel a primary artifact path as guidance" in prompt
    assert "Use the exact source-documented primary output path" in prompt


def test_review_prompt_explains_harness_output_path_mapping():
    module = load_module()

    prompt = module.build_review_prompt(
        "demo-skill",
        "executable",
        valid_payload("executable"),
        source_snapshot="# Demo\nSave writing_blueprint.md.\n",
        mode_contract={
            "execution_mode": "artifact",
            "observed_modes": ["artifact"],
            "primary_output": {"path": "writing_blueprint.md"},
        },
    )

    assert "The harness stores artifacts under `outputs/`" in prompt
    assert "file_assertions paths are relative to that directory" in prompt
    assert "preserve the source-relative filename" in prompt


def test_repair_prompt_preserves_case_discrimination_when_replacing_generic_labels():
    module = load_module()

    prompt = module.build_repair_prompt(
        "demo-skill",
        "guidance",
        valid_payload(),
        "cases[2].assertions[1] uses a generic status label as a positive assertion",
    )

    assert "source-specific, non-prompt-echo positive assertion" in prompt
    assert "every case retains at least one discriminating positive assertion" in prompt


def test_author_prompt_routes_code_identifiers_to_regex_assertions():
    module = load_module()

    prompt = module.build_author_prompt(
        "demo-skill",
        "guidance",
        source_snapshot="# Demo\nCall luminosity_distance.\n",
    )

    assert "Code identifiers must use regex, not contains" in prompt


def test_author_prompt_rejects_bare_task_verbs_as_positive_assertions():
    module = load_module()

    prompt = module.build_author_prompt(
        "demo-skill",
        "guidance",
        source_snapshot="# Demo\nShorten a title while preserving its meaning.\n",
    )

    assert "bare task verbs or generic nouns" in prompt
    assert "combine them with a source-specific outcome" in prompt
    assert "observable source-specific outcome" in prompt


def test_author_prompt_requires_existing_commands_and_compatible_fixtures():
    module = load_module()

    prompt = module.build_author_prompt(
        "demo-skill",
        "executable",
        source_snapshot="# Demo\nOnly SKILL.md exists.\n",
    )

    assert "Every command path must exist in the source snapshot" in prompt
    assert "Fixture target format must match its source file content" in prompt


def test_author_prompt_binds_assertions_to_exact_script_output_shapes():
    module = load_module()

    prompt = module.build_author_prompt(
        "demo-skill",
        "executable",
        source_snapshot="# Demo\nA script writes unit,arm CSV rows.\n",
    )

    assert "exact executed code path" in prompt
    assert "complete record shape" in prompt
    assert "documentation prose" in prompt


def test_execution_mode_review_rejects_source_drift_and_unresolved_mode(tmp_path):
    module = load_module()
    source = tmp_path / "source"
    source.mkdir()
    skill = source / "SKILL.md"
    skill.write_text("# Demo\nOriginal.\n", encoding="utf-8")
    review_path = tmp_path / "execution-mode-review.json"
    review_path.write_text(
        json.dumps(execution_mode_review(module, source)), encoding="utf-8"
    )
    skill.write_text("# Demo\nChanged.\n", encoding="utf-8")

    with pytest.raises(ValueError, match="source tree hash"):
        module.load_execution_mode_review(review_path, "demo-skill", source)

    unresolved = execution_mode_review(
        module, source, status="needs_mode_review"
    )
    review_path.write_text(json.dumps(unresolved), encoding="utf-8")
    with pytest.raises(ValueError, match="needs independent mode review"):
        module.load_execution_mode_review(review_path, "demo-skill", source)


def test_execution_mode_conflict_is_archived_and_blocks_authoring(tmp_path):
    module = load_module()
    source = tmp_path / "source"
    source.mkdir()
    (source / "SKILL.md").write_text("# Demo\nWrite a report.\n", encoding="utf-8")
    review_path = tmp_path / "execution-mode-review.json"
    review_path.write_text(
        json.dumps(execution_mode_review(module, source, mode="artifact")),
        encoding="utf-8",
    )
    run_root = tmp_path / "run"

    with pytest.raises(ValueError, match="conflicts with source-backed"):
        module.resolve_execution_mode_review(
            review_path,
            "demo-skill",
            source,
            "guidance",
            run_root,
        )

    conflict = json.loads(
        (run_root / "execution-mode-conflict.json").read_text(encoding="utf-8")
    )
    assert conflict["requested_skill_type"] == "guidance"
    assert conflict["source_backed_skill_type"] == "executable"
    assert not (run_root / "author-prompt.txt").exists()


def test_parse_author_response_accepts_fenced_json():
    module = load_module()
    payload = valid_payload()
    text = "Here is the pack:\n```json\n" + json.dumps(payload) + "\n```"
    assert module.parse_author_response(text) == payload


def test_parse_author_response_prefers_complete_schema_payload_over_example():
    module = load_module()
    example = {"type": "not_contains", "path": "report.html"}
    payload = valid_payload()
    text = (
        "The invalid assertion was:\n```json\n"
        + json.dumps(example)
        + "\n```\nHere is the complete repaired payload:\n```json\n"
        + json.dumps(payload)
        + "\n```"
    )

    assert module.parse_author_response(text) == payload


def test_normalize_author_payload_maps_unambiguous_trigger_schema_alias():
    module = load_module()
    payload = valid_payload()
    for trigger in payload["triggers"]:
        trigger["expected_match"] = trigger.pop("should_trigger")

    normalized = module.normalize_author_payload(payload)

    assert all("expected_match" not in trigger for trigger in normalized["triggers"])
    assert [trigger["should_trigger"] for trigger in normalized["triggers"]] == [
        True,
        True,
        True,
        True,
        False,
        False,
        False,
        False,
    ]


def test_normalize_author_payload_rejects_conflicting_trigger_aliases():
    module = load_module()
    payload = valid_payload()
    payload["triggers"][0]["expected_match"] = False

    with pytest.raises(ValueError, match="conflicting"):
        module.normalize_author_payload(payload)


def test_normalize_author_payload_maps_empty_guidance_artifact_to_null():
    module = load_module()
    payload = valid_payload()
    for case in payload["cases"]:
        case["artifact_path"] = ""

    normalized = module.normalize_author_payload(payload)

    assert [case["artifact_path"] for case in normalized["cases"]] == [
        None,
        None,
        None,
    ]


def test_normalize_author_payload_preserves_empty_artifact_for_strict_validation():
    module = load_module()
    payload = valid_payload("hybrid")
    payload["cases"][0]["artifact_path"] = ""

    normalized = module.normalize_author_payload(payload)

    assert normalized["cases"][0]["artifact_path"] == ""
    with pytest.raises(ValueError, match="relative path or null"):
        module.validate_author_payload(normalized, "demo-skill", "hybrid")


def test_normalize_author_payload_maps_unambiguous_assertion_value_alias():
    module = load_module()
    payload = valid_payload()
    for case in payload["cases"]:
        for assertion in case["assertions"]:
            assertion["expected"] = assertion.pop("value")

    normalized = module.normalize_author_payload(payload)

    assert all(
        "expected" not in assertion and assertion["value"]
        for case in normalized["cases"]
        for assertion in case["assertions"]
    )


def test_normalize_author_payload_moves_flat_file_assertions_and_artifact_mode():
    module = load_module()
    payload = valid_payload("hybrid")
    case = payload["cases"][0]
    case["mode"] = "tool"
    case["assertions"] = [
        {"type": "file-exists", "path": "report.md"},
        {"type": "file-contains", "path": "report.md", "value": "Decision 1"},
    ]
    case["file_assertions"] = []
    case["tool_assertions"] = []
    case["allowed_commands"] = [
        'python "{skill_dir}/scripts/run.py" --output "{workspace}/outputs/report.md"'
    ]

    normalized = module.normalize_author_payload(payload)

    assert normalized["cases"][0]["assertions"] == []
    assert normalized["cases"][0]["file_assertions"] == [
        {"type": "file-exists", "path": "report.md"},
        {"type": "file-contains", "path": "report.md", "value": "Decision 1"},
    ]
    assert normalized["cases"][0]["mode"] == "artifact"
    module.validate_author_payload(normalized, "demo-skill", "hybrid")


def test_normalize_author_payload_rejects_conflicting_assertion_value_alias():
    module = load_module()
    payload = valid_payload()
    payload["cases"][0]["assertions"][0]["expected"] = "conflict"

    with pytest.raises(ValueError, match="conflicting assertion values"):
        module.normalize_author_payload(payload)


def test_validate_author_payload_accepts_guidance_contract():
    module = load_module()
    result = module.validate_author_payload(valid_payload(), "demo-skill", "guidance")
    assert result["case_count"] == 3
    assert result["trigger_count"] == 8
    assert result["prompt_echo_risks"] == []


def test_validate_author_payload_requires_completed_self_review():
    module = load_module()
    payload = valid_payload()
    payload["self_review"]["offline_feasibility"] = False

    with pytest.raises(ValueError, match="self_review"):
        module.validate_author_payload(payload, "demo-skill", "guidance")


def test_validate_author_payload_flags_prompt_echo_and_requires_discrimination():
    module = load_module()
    payload = valid_payload()
    payload["cases"][0]["prompt"] += " The answer must say Decision 1 and limitation."
    with pytest.raises(ValueError, match="prompt-echo"):
        module.validate_author_payload(payload, "demo-skill", "guidance")


def test_hybrid_payload_requires_non_guidance_case():
    module = load_module()
    guidance_only = valid_payload("hybrid")
    for case in guidance_only["cases"]:
        case.update(
            {
                "mode": "guidance",
                "artifact_path": None,
                "file_assertions": [],
            }
        )
    with pytest.raises(ValueError, match="artifact or tool"):
        module.validate_author_payload(guidance_only, "demo-skill", "hybrid")
    result = module.validate_author_payload(valid_payload("hybrid"), "demo-skill", "hybrid")
    assert result["execution_modes"]["artifact"] == 1


def test_materialize_pack_copies_source_and_writes_canonical_evals(tmp_path):
    module = load_module()
    source = tmp_path / "source"
    source.mkdir()
    (source / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: demo\n---\nInstructions\n",
        encoding="utf-8",
    )
    (source / "reference.txt").write_text("source evidence", encoding="utf-8")
    output = tmp_path / "eval_skill"

    manifest = module.materialize_pack(
        source,
        output,
        valid_payload(),
        author_report_sha256="author-sha",
        native_eval_sha256=None,
    )

    assert (output / "SKILL.md").is_file()
    assert (output / "reference.txt").read_text(encoding="utf-8") == "source evidence"
    evals = json.loads((output / "evals" / "evals.json").read_text(encoding="utf-8"))
    triggers = json.loads(
        (output / "evals" / "trigger_queries.json").read_text(encoding="utf-8")
    )
    assert len(evals["evals"]) == 3
    assert len(triggers["queries"]) == 8
    assert manifest["author_report_sha256"] == "author-sha"
    assert manifest["source_file_count"] == 2


def test_materialize_pack_preserves_safe_fixture_contract(tmp_path):
    module = load_module()
    source = tmp_path / "source"
    (source / "fixtures").mkdir(parents=True)
    (source / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: demo\n---\nInstructions\n",
        encoding="utf-8",
    )
    (source / "fixtures" / "sample.csv").write_text("x\n1\n", encoding="utf-8")
    payload = valid_payload("hybrid")
    payload["cases"][0]["fixtures"] = [
        {"source_path": "fixtures/sample.csv", "target_path": "inputs/sample.csv"}
    ]

    output = tmp_path / "eval_skill"
    module.materialize_pack(
        source,
        output,
        payload,
        author_report_sha256="author-sha",
        native_eval_sha256=None,
    )

    evals = json.loads((output / "evals" / "evals.json").read_text(encoding="utf-8"))
    assert evals["evals"][0]["fixtures"] == [
        {"source_path": "fixtures/sample.csv", "target_path": "inputs/sample.csv"}
    ]


def test_validate_author_payload_rejects_fixture_path_escape():
    module = load_module()
    payload = valid_payload("hybrid")
    payload["cases"][0]["fixtures"] = [
        {"source_path": "fixtures/sample.csv", "target_path": "../sample.csv"}
    ]

    with pytest.raises(ValueError, match="fixtures must target inputs"):
        module.validate_author_payload(payload, "demo-skill", "hybrid")


def test_validate_author_payload_rejects_artifact_directory_path():
    module = load_module()
    payload = valid_payload("executable")
    payload["cases"][0]["artifact_path"] = "outputs/reports/"

    with pytest.raises(ValueError, match="must name a file"):
        module.validate_author_payload(payload, "demo-skill", "executable")


def test_author_prompt_preserves_native_eval_as_reference_not_gold_answer():
    module = load_module()
    prompt = module.build_author_prompt(
        "demo-skill",
        "guidance",
        native_eval={"evals": [{"prompt": "legacy task", "expected_output": "legacy"}]},
    )
    assert "reference material, not an answer table" in prompt
    assert "legacy task" in prompt
    assert "Return strict JSON only" in prompt
    assert "offline and isolated" in prompt
    assert "unavailable dependency" in prompt
    assert "Never assert a successful analysis, scan, clean result, or report" in prompt
    assert "enumerate the offline path for every case" in prompt
    assert "For fallback or refusal cases, prefer positive prerequisite" in prompt
    assert "Every output assertion must contain a non-empty string `value`" in prompt
    assert "short semantic anchor" in prompt
    assert "at most five whitespace" in prompt
    assert "generic headings or status labels" in prompt
    assert "主要问题" in prompt
    assert "a `not_contains` value must not occur in its case prompt" in prompt
    assert "guidance cases must use exactly" in prompt
    assert '"target_path":"inputs/<filename>"' in prompt
    assert "Run this schema preflight before returning" in prompt
    assert "do not use not_contains on requested task terms" in prompt
    assert "self_review" in prompt


def test_author_prompt_defines_fair_command_and_fixture_placeholders():
    module = load_module()
    prompt = module.build_author_prompt("demo-skill", "executable")

    assert "{skill_dir}" in prompt
    assert "{workspace}" in prompt
    assert "inputs are staged identically for with-skill and without-skill" in prompt
    assert "implementation commands are available only to the with-skill run" in prompt
    assert '`file_assertions` is a flat array' in prompt
    assert '`{"type":"file-contains","path":"report.json","value":"finding"}`' in prompt


def test_author_prompt_defines_flat_tool_assertion_contract():
    module = load_module()
    prompt = module.build_author_prompt("demo-skill", "executable")

    assert "`tool_assertions` is a flat array" in prompt
    assert "tool-called" in prompt
    assert "tool-arg-equals" in prompt
    assert "never a command object wrapping a" in prompt


def test_source_snapshot_is_hash_backed_and_embedded_without_tool_calls(tmp_path):
    module = load_module()
    source = tmp_path / "source"
    (source / "references").mkdir(parents=True)
    (source / "SKILL.md").write_text("# Demo\nUse the fallback.\n", encoding="utf-8")
    (source / "references" / "guide.md").write_text("# Guide\nEvidence\n", encoding="utf-8")

    snapshot = module.build_source_snapshot(source)
    prompt = module.build_author_prompt(
        "demo-skill",
        "guidance",
        source_snapshot=snapshot,
    )

    assert "FILE: SKILL.md" in snapshot
    assert "FILE: references/guide.md" in snapshot
    assert module.sha256(source / "SKILL.md") in snapshot
    assert "complete hash-backed source package is embedded below" in prompt
    assert "Do not call tools" in prompt
    assert "Use the fallback." in prompt


def test_validate_author_payload_rejects_broad_negative_side_effect_words():
    module = load_module()
    payload = valid_payload()
    payload["cases"][0]["assertions"].append(
        {"type": "not_contains", "value": "delete"}
    )

    with pytest.raises(ValueError, match="broad negative"):
        module.validate_author_payload(payload, "demo-skill", "guidance")


@pytest.mark.parametrize("value", ["提示", "相关", "主要问题", "仍需确认"])
def test_validate_author_payload_rejects_generic_status_labels_as_positive_assertions(value):
    module = load_module()
    payload = valid_payload()
    payload["cases"][0]["assertions"][0] = {"type": "contains", "value": value}

    with pytest.raises(ValueError, match="generic status label"):
        module.validate_author_payload(payload, "demo-skill", "guidance")


def test_validate_author_payload_rejects_negative_assertion_present_in_prompt():
    module = load_module()
    payload = valid_payload()
    payload["cases"][0]["assertions"].append(
        {"type": "not_contains", "value": "research scenario"}
    )

    with pytest.raises(ValueError, match="conflicts with its prompt"):
        module.validate_author_payload(payload, "demo-skill", "guidance")


@pytest.mark.parametrize(
    "value",
    [
        "local linear regression with a triangular kernel",
        "McCrary (2008)",
    ],
)
def test_validate_author_payload_rejects_brittle_contains_anchors(value):
    module = load_module()
    payload = valid_payload()
    payload["cases"][0]["assertions"][0] = {"type": "contains", "value": value}

    with pytest.raises(ValueError, match="brittle contains anchor"):
        module.validate_author_payload(payload, "demo-skill", "guidance")


def test_validate_author_payload_reports_all_brittle_assertions_for_single_repair():
    module = load_module()
    payload = valid_payload()
    payload["cases"][0]["assertions"] = [
        {"type": "contains", "value": "local linear regression with a triangular kernel"},
        {"type": "contains", "value": "McCrary (2008)"},
    ]

    with pytest.raises(ValueError) as error:
        module.validate_author_payload(payload, "demo-skill", "guidance")

    message = str(error.value)
    assert "cases[0].assertions[0]" in message
    assert "cases[0].assertions[1]" in message


def test_validate_author_payload_accepts_short_semantic_contains_anchors():
    module = load_module()
    payload = valid_payload()
    payload["cases"][0]["assertions"] = [
        {"type": "contains", "value": "triangular kernel"},
        {"type": "contains", "value": "McCrary"},
    ]

    validated = module.validate_author_payload(payload, "demo-skill", "guidance")

    assert validated["case_count"] == 3
    assert payload["cases"][0]["assertions"] == [
        {"type": "contains", "value": "triangular kernel"},
        {"type": "contains", "value": "McCrary"},
    ]


def test_validate_author_payload_separates_behavior_prompts_from_trigger_queries():
    module = load_module()
    payload = valid_payload()
    payload["triggers"][0]["query"] = payload["cases"][0]["prompt"]

    with pytest.raises(ValueError, match="must differ from trigger queries"):
        module.validate_author_payload(payload, "demo-skill", "guidance")


def test_review_prompt_is_source_only_and_checks_offline_feasibility():
    module = load_module()
    source_snapshot = "FILE: SKILL.md\nSHA256: abc123\nCONTENT:\n# Demo"
    mode_contract = execution_mode_review(
        module, pathlib.Path(__file__).parent, mode="guidance"
    )
    prompt = module.build_review_prompt(
        "demo-skill",
        "guidance",
        valid_payload(),
        source_snapshot=source_snapshot,
        mode_contract=mode_contract,
    )

    assert "Do not use or request behavior-run outputs" in prompt
    assert "offline feasibility" in prompt
    assert "broad not_contains" in prompt
    assert "Markdown-sensitive" in prompt
    assert "short semantic anchors" in prompt
    assert "Do not call tools" in prompt
    assert "Hash-backed source package" in prompt
    assert source_snapshot in prompt
    assert "Source-backed execution-mode contract" in prompt


def test_author_prompt_receives_exact_execution_mode_contract():
    module = load_module()
    mode_contract = {
        "execution_mode": "artifact",
        "primary_output": {"kind": "file", "description": "Write .research/a.yml"},
        "required_runtime": [],
        "side_effects": ["append run log"],
    }

    prompt = module.build_author_prompt(
        "demo-skill",
        "executable",
        source_snapshot="FILE: SKILL.md\nCONTENT:\nWrite files.",
        mode_contract=mode_contract,
    )

    assert '"execution_mode": "artifact"' in prompt
    assert "fallback file merely to satisfy the executable schema" in prompt
    assert "Write .research/a.yml" in prompt


def test_validate_review_payload_rejects_source_reviewed_revision():
    module = load_module()
    revised = valid_payload()
    review = {
        "schema": "critic_eval_review_v1",
        "skill_id": "demo-skill",
        "verdict": "revised",
        "issues": [
            {
                "case_id": "case-1",
                "code": "offline_infeasible",
                "detail": "Test the documented fallback instead.",
            }
        ],
        "reviewed_payload": revised,
        "review_rationale": "Checked against mounted source only.",
    }

    with pytest.raises(ValueError, match="approved or rejected"):
        module.validate_review_payload(
            review, "demo-skill", "guidance", valid_payload()
        )


def test_validate_review_payload_rejects_changed_approved_payload():
    module = load_module()
    authored = valid_payload()
    changed = json.loads(json.dumps(authored))
    changed["cases"][0]["prompt"] = "Changed by reviewer"
    review = {
        "schema": "critic_eval_review_v1",
        "skill_id": "demo-skill",
        "verdict": "approved",
        "issues": [],
        "reviewed_payload": changed,
        "review_rationale": "Checked against mounted source only.",
    }

    with pytest.raises(ValueError, match="must preserve authored_payload"):
        module.validate_review_payload(review, "demo-skill", "guidance", authored)


def test_validate_review_payload_unwraps_unambiguous_schema_envelope():
    module = load_module()
    reviewed = valid_payload()
    inner = {
        "skill_id": "demo-skill",
        "verdict": "approved",
        "issues": [],
        "reviewed_payload": reviewed,
        "review_rationale": "Checked against the mounted source only.",
    }
    wrapped = {"critic_eval_review_v1": inner}
    original = json.loads(json.dumps(wrapped))

    result = module.validate_review_payload(
        wrapped, "demo-skill", "guidance", reviewed
    )

    assert result["schema"] == "critic_eval_review_v1"
    assert result["verdict"] == inner["verdict"]
    assert result["reviewed_payload"] == inner["reviewed_payload"]
    assert result["review_rationale"] == inner["review_rationale"]
    assert wrapped == original


@pytest.mark.parametrize(
    "wrapped",
    [
        {
            "critic_eval_review_v1": {
                "skill_id": "demo-skill",
                "verdict": "rejected",
                "issues": [],
                "reviewed_payload": None,
                "review_rationale": "Rejected against source.",
            },
            "extra": "ambiguous",
        },
        {
            "critic_eval_review_v1": {
                "schema": "different_review_schema",
                "skill_id": "demo-skill",
                "verdict": "rejected",
                "issues": [],
                "reviewed_payload": None,
                "review_rationale": "Rejected against source.",
            }
        },
    ],
)
def test_validate_review_payload_rejects_ambiguous_or_conflicting_envelopes(wrapped):
    module = load_module()

    with pytest.raises(ValueError, match="identity or schema"):
        module.validate_review_payload(
            wrapped, "demo-skill", "guidance", valid_payload()
        )


def test_repair_prompt_contains_only_payload_error_and_generic_contract():
    module = load_module()
    payload = valid_payload()
    payload["cases"][0]["assertions"][0]["value"] = ""

    prompt = module.build_repair_prompt(
        "demo-skill",
        "guidance",
        payload,
        "cases[0].assertions[0].value must be a non-empty string",
    )

    assert "cases[0].assertions[0].value must be a non-empty string" in prompt
    assert '"skill_id": "demo-skill"' in prompt
    assert "Return one complete corrected `critic_eval_author_v1` payload" in prompt
    assert "Set the top-level schema field exactly to `critic_eval_author_v1`" in prompt
    assert "file-exists, file-not-exists, file-contains, or file-matches" in prompt
    assert "Every artifact case" in prompt
    assert "non-empty artifact_path" in prompt
    assert "file_assertions must be a flat array" in prompt
    assert "Fixtures may not contain inline content" in prompt
    assert "existing source-relative file" in prompt
    assert "unique target_path beginning with `inputs/`" in prompt
    assert "Do not add source facts" in prompt
    assert "guidance cases MUST use exactly" in prompt
    assert "`artifact_path: null`" in prompt
    assert "`allowed_commands: []`" in prompt
    assert "`file_assertions: []`" in prompt
    assert "`tool_assertions: []`" in prompt
    assert "`fixtures: []`" in prompt
    assert "Do not add artifact paths, commands" in prompt
    assert "file assertions, tool assertions, or fixtures" in prompt
    assert "Hash-backed source package" not in prompt
    assert "Native eval reference" not in prompt


def test_review_repair_prompt_preserves_review_semantics():
    module = load_module()
    review = {
        "schema": "critic_eval_review_v1",
        "skill_id": "demo-skill",
        "verdict": "approved",
        "issues": ["Use an object for this issue."],
        "reviewed_payload": valid_payload(),
        "review_rationale": "Source-backed review.",
    }

    prompt = module.build_review_repair_prompt(
        "demo-skill",
        "guidance",
        review,
        "review issues must be an array of objects",
    )

    assert "only the review envelope schema" in prompt
    assert "must remain exactly unchanged" in prompt
    assert "review issues must be an array of objects" in prompt
    assert "Hash-backed source package" not in prompt


def test_consume_single_review_repair_rejects_semantic_changes(tmp_path):
    module = load_module()
    original = {
        "schema": "critic_eval_review_v1",
        "skill_id": "demo-skill",
        "verdict": "approved",
        "issues": ["Use an object for this issue."],
        "reviewed_payload": valid_payload(),
        "review_rationale": "Source-backed review.",
    }
    repaired = dict(original)
    repaired["issues"] = [
        {"case_id": "case-1", "code": "schema", "detail": original["issues"][0]}
    ]
    report_path = tmp_path / "review-repair.json"
    report_path.write_text(
        json.dumps(
            {"status": "pass", "source_unchanged": True, "final_text": json.dumps(repaired)}
        ),
        encoding="utf-8",
    )

    result, _ = module.consume_single_review_repair_report(
        tmp_path,
        report_path,
        original,
        "demo-skill",
        "guidance",
        valid_payload(),
    )
    assert result["reviewed_payload"] == original["reviewed_payload"]

    changed = json.loads(json.dumps(repaired))
    changed["reviewed_payload"]["cases"][0]["prompt"] = "Changed semantics"
    changed_path = tmp_path / "review-repair-changed.json"
    changed_path.write_text(
        json.dumps(
            {"status": "pass", "source_unchanged": True, "final_text": json.dumps(changed)}
        ),
        encoding="utf-8",
    )
    other_root = tmp_path / "other"
    with pytest.raises(ValueError, match="must preserve authored_payload"):
        module.consume_single_review_repair_report(
            other_root,
            changed_path,
            original,
            "demo-skill",
            "guidance",
            valid_payload(),
        )
    failure = json.loads(
        (other_root / "review-repair-validation-error.json").read_text(
            encoding="utf-8"
        )
    )
    assert failure["stage"] == "review_repair"
    assert failure["error"] == "approved review must preserve authored_payload"


def test_consume_single_repair_report_rejects_a_different_second_attempt(tmp_path):
    module = load_module()
    first = tmp_path / "repair-1.json"
    second = tmp_path / "repair-2.json"
    report = {
        "status": "pass",
        "source_unchanged": True,
        "final_text": json.dumps(valid_payload()),
    }
    first.write_text(json.dumps(report), encoding="utf-8")
    report["final_text"] += "\n"
    second.write_text(json.dumps(report), encoding="utf-8")

    payload, report_sha = module.consume_single_repair_report(
        tmp_path,
        first,
        "demo-skill",
        "guidance",
    )

    assert payload["skill_id"] == "demo-skill"
    assert report_sha == module.sha256(first)
    marker = json.loads((tmp_path / "repair-attempt.json").read_text(encoding="utf-8"))
    assert marker["attempt_count"] == 1
    with pytest.raises(ValueError, match="already consumed"):
        module.consume_single_repair_report(
            tmp_path,
            second,
            "demo-skill",
            "guidance",
        )


def test_consume_single_repair_report_archives_strict_validation_failure(tmp_path):
    module = load_module()
    invalid = valid_payload()
    invalid["cases"][0]["assertions"][0]["value"] = ""
    report_path = tmp_path / "repair.json"
    report_path.write_text(
        json.dumps(
            {
                "status": "pass",
                "source_unchanged": True,
                "final_text": json.dumps(invalid),
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="non-empty string"):
        module.consume_single_repair_report(
            tmp_path,
            report_path,
            "demo-skill",
            "guidance",
        )

    archived = json.loads(
        (tmp_path / "repair-validation-error.json").read_text(encoding="utf-8")
    )
    assert archived["stage"] == "repair"
    assert archived["repair_report_sha256"] == module.sha256(report_path)


def test_main_waits_for_independent_review_before_materializing(tmp_path):
    module = load_module()
    source = tmp_path / "source"
    source.mkdir()
    source_skill = source / "SKILL.md"
    source_skill.write_text(
        "---\nname: demo-skill\ndescription: Demo guidance skill.\n---\n\n"
        "Return a structured conversational analysis.\n",
        encoding="utf-8",
    )
    run_root = tmp_path / "run"
    run_root.mkdir()
    mode_review = run_root / "execution-mode-review.json"
    mode_review.write_text(
        json.dumps(
            {
                "schema": "critic_execution_mode_review_v1",
                "skill_id": "demo-skill",
                "source_tree_sha256": module.manifest_sha256(
                    module.tree_manifest(source)
                ),
                "review_status": "source_reviewed",
                "execution_mode": "guidance",
                "provider_report_sha256": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    author_report = run_root / "author-provider-report.json"
    author_report.write_text(
        json.dumps(
            {
                "status": "pass",
                "source_unchanged": True,
                "final_text": json.dumps(valid_payload()),
            }
        ),
        encoding="utf-8",
    )

    result = module.main(
        [
            "--id",
            "demo-skill",
            "--skill-type",
            "guidance",
            "--source-skill",
            str(source_skill),
            "--run-root",
            str(run_root),
            "--execution-mode-review",
            str(mode_review),
            "--provider-report",
            str(author_report),
        ]
    )

    assert result == 0
    assert (run_root / "author-payload.json").is_file()
    assert (run_root / "review-prompt.txt").is_file()
    assert not (run_root / "eval_skill").exists()


def test_main_stages_one_repair_for_unparseable_author_response(tmp_path):
    module = load_module()
    source = tmp_path / "source"
    source.mkdir()
    source_skill = source / "SKILL.md"
    source_skill.write_text(
        "---\nname: demo-skill\ndescription: Demo guidance skill.\n---\n\n"
        "Return a structured conversational analysis.\n",
        encoding="utf-8",
    )
    run_root = tmp_path / "run"
    run_root.mkdir()
    mode_review = run_root / "execution-mode-review.json"
    mode_review.write_text(
        json.dumps(
            {
                "schema": "critic_execution_mode_review_v1",
                "skill_id": "demo-skill",
                "source_tree_sha256": module.manifest_sha256(
                    module.tree_manifest(source)
                ),
                "review_status": "source_reviewed",
                "execution_mode": "guidance",
                "provider_report_sha256": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    author_report = run_root / "author-provider-report.json"
    author_report.write_text(
        json.dumps(
            {
                "status": "pass",
                "source_unchanged": True,
                "final_text": '```json\n{"schema":"critic_eval_author_v1",',
            }
        ),
        encoding="utf-8",
    )

    result = module.main(
        [
            "--id",
            "demo-skill",
            "--skill-type",
            "guidance",
            "--source-skill",
            str(source_skill),
            "--run-root",
            str(run_root),
            "--execution-mode-review",
            str(mode_review),
            "--provider-report",
            str(author_report),
        ]
    )

    assert result == 2
    error = json.loads(
        (run_root / "author-validation-error.json").read_text(encoding="utf-8")
    )
    assert error["stage"] == "author"
    assert error["error_type"] == "JSONDecodeError"
    prompt = (run_root / "repair-prompt.txt").read_text(encoding="utf-8")
    assert "Original invalid response" in prompt
    assert "critic_eval_author_v1" in prompt
    assert not (run_root / "author-payload.json").exists()
