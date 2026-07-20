import importlib.util
import inspect
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_critic_hybrid_batch.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_critic_hybrid_batch", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_pack(root: Path):
    (root / "evals").mkdir(parents=True)
    (root / "SKILL.md").write_text(
        "---\nname: sample-skill\ndescription: Sample research planning skill.\n---\nBody\n",
        encoding="utf-8",
    )
    (root / "evals" / "evals.json").write_text(
        json.dumps(
            {
                "evals": [
                    {
                        "id": f"case-{index}",
                        "prompt": f"Prompt {index}",
                        "mode": "guidance",
                        "artifact_path": None,
                        "allowed_commands": [],
                        "file_assertions": [],
                        "tool_assertions": [],
                        "fixtures": [],
                        "assertions": [{"type": "contains", "value": f"item {index}"}],
                    }
                    for index in range(1, 4)
                ]
            }
        ),
        encoding="utf-8",
    )
    queries = [
        {"query": f"positive {index}", "should_trigger": True}
        for index in range(4)
    ] + [
        {"query": f"negative {index}", "should_trigger": False}
        for index in range(4)
    ]
    (root / "evals" / "trigger_queries.json").write_text(
        json.dumps({"trigger_queries": queries}), encoding="utf-8"
    )


def test_validate_eval_pack_requires_three_cases_and_balanced_triggers(tmp_path):
    module = load_module()
    make_pack(tmp_path)

    result = module.validate_eval_pack(tmp_path)

    assert result["skill_name"] == "sample-skill"
    assert result["case_count"] == 3
    assert result["trigger_count"] == 8


def test_validate_eval_pack_rejects_free_form_assertions(tmp_path):
    module = load_module()
    make_pack(tmp_path)
    path = tmp_path / "evals" / "evals.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["evals"][0]["assertions"] = ["looks good"]
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="deterministic"):
        module.validate_eval_pack(tmp_path)


def test_validate_eval_pack_accepts_file_only_artifact_evidence(tmp_path):
    module = load_module()
    make_pack(tmp_path)
    path = tmp_path / "evals" / "evals.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["evals"][0].update(
        {
            "mode": "artifact",
            "artifact_path": "outputs/report.json",
            "assertions": [],
            "file_assertions": [
                {"type": "file-exists", "path": "report.json"},
                {
                    "type": "file-contains",
                    "path": "report.json",
                    "value": "finding",
                },
            ],
        }
    )
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = module.validate_eval_pack(tmp_path)

    assert result["case_count"] == 3


def test_build_jobs_creates_six_behavior_runs_and_one_trigger_batch(tmp_path):
    module = load_module()
    pack = tmp_path / "eval_skill"
    make_pack(pack)

    jobs = module.build_jobs(
        skill_id="sample-skill",
        eval_skill=pack,
        run_root=tmp_path / "runs",
        model="deepseek-v4-flash-260425",
        agentscope_src=tmp_path / "agentscope",
        runner=tmp_path / "runner.py",
    )

    assert len(jobs) == 7
    assert sum(job["kind"] == "behavior" for job in jobs) == 6
    assert sum(job["kind"] == "trigger" for job in jobs) == 1
    assert sum("--skill-dir" in job["args"] for job in jobs) == 3
    assert all("--allow-no-tool" in job["args"] for job in jobs)


def test_build_jobs_forwards_anthropic_protocol(tmp_path):
    module = load_module()
    pack = tmp_path / "eval_skill"
    make_pack(pack)

    jobs = module.build_jobs(
        skill_id="sample-skill",
        eval_skill=pack,
        run_root=tmp_path / "runs",
        model="DeepSeek-V4-Flash",
        agentscope_src=tmp_path / "agentscope",
        runner=tmp_path / "runner.py",
        protocol="anthropic",
        auth_mode="auth-token",
    )

    assert all("--protocol" in job["args"] for job in jobs)
    assert all(job["args"][job["args"].index("--protocol") + 1] == "anthropic" for job in jobs)
    assert all(job["args"][job["args"].index("--auth-mode") + 1] == "auth-token" for job in jobs)


def test_build_jobs_applies_case_specific_artifact_permissions(tmp_path):
    module = load_module()
    pack = tmp_path / "eval_skill"
    make_pack(pack)
    evals_path = pack / "evals" / "evals.json"
    payload = json.loads(evals_path.read_text(encoding="utf-8"))
    payload["evals"][0].update(
        {
            "mode": "artifact",
            "artifact_path": "outputs/report.md",
            "file_assertions": [
                {"type": "file-exists", "path": "report.md"},
            ],
        }
    )
    evals_path.write_text(json.dumps(payload), encoding="utf-8")

    jobs = module.build_jobs(
        skill_id="sample-skill",
        eval_skill=pack,
        run_root=tmp_path / "runs",
        model="deepseek-v4-flash-260425",
        agentscope_src=tmp_path / "agentscope",
        runner=tmp_path / "runner.py",
    )

    artifact_jobs = [job for job in jobs if job.get("case_mode") == "artifact"]
    guidance_jobs = [job for job in jobs if job.get("case_mode") == "guidance"]
    trigger_job = next(job for job in jobs if job["kind"] == "trigger")
    assert len(artifact_jobs) == 2
    assert all("--guidance-only" not in job["args"] for job in artifact_jobs)
    assert all("--allow-output" in job["args"] for job in artifact_jobs)
    assert all("outputs/report.md" in job["args"] for job in artifact_jobs)
    assert all("--guidance-only" in job["args"] for job in guidance_jobs)
    assert "--guidance-only" in trigger_job["args"]


def test_build_jobs_allows_every_positive_declared_artifact_file(tmp_path):
    module = load_module()
    pack = tmp_path / "eval_skill"
    make_pack(pack)
    evals_path = pack / "evals" / "evals.json"
    payload = json.loads(evals_path.read_text(encoding="utf-8"))
    payload["evals"][0].update(
        {
            "mode": "artifact",
            "artifact_path": "outputs/.research/project_manifest.yml",
            "file_assertions": [
                {"type": "file-exists", "path": ".research/project_manifest.yml"},
                {"type": "file-contains", "path": ".research/run_log.md", "value": "run"},
                {"type": "file-not-exists", "path": ".paper/manifest.yml"},
            ],
        }
    )
    evals_path.write_text(json.dumps(payload), encoding="utf-8")

    jobs = module.build_jobs(
        skill_id="sample-skill",
        eval_skill=pack,
        run_root=tmp_path / "runs",
        model="glm5.2",
        agentscope_src=tmp_path / "agentscope",
        runner=tmp_path / "runner.py",
    )

    artifact_jobs = [job for job in jobs if job.get("case_mode") == "artifact"]
    for job in artifact_jobs:
        allowed = [
            job["args"][index + 1]
            for index, arg in enumerate(job["args"])
            if arg == "--allow-output"
        ]
        assert allowed == [
            "outputs/.research/project_manifest.yml",
            "outputs/.research/run_log.md",
        ]


def test_validate_eval_pack_rejects_file_assertion_path_escape(tmp_path):
    module = load_module()
    make_pack(tmp_path)
    evals_path = tmp_path / "evals" / "evals.json"
    payload = json.loads(evals_path.read_text(encoding="utf-8"))
    payload["evals"][0].update(
        {
            "mode": "artifact",
            "artifact_path": "outputs/report.md",
            "file_assertions": [
                {"type": "file-exists", "path": "../outside.txt"},
            ],
        }
    )
    evals_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="file assertion path"):
        module.validate_eval_pack(tmp_path)


def test_validate_eval_pack_rejects_directory_artifact_target(tmp_path):
    module = load_module()
    make_pack(tmp_path)
    evals_path = tmp_path / "evals" / "evals.json"
    payload = json.loads(evals_path.read_text(encoding="utf-8"))
    payload["evals"][0].update(
        {
            "mode": "artifact",
            "artifact_path": "outputs/.research/",
            "file_assertions": [
                {"type": "file-exists", "path": ".research/project_manifest.yml"},
            ],
        }
    )
    evals_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="artifact_path must name a file"):
        module.validate_eval_pack(tmp_path)


def test_build_jobs_stages_identical_declared_fixtures_for_both_modes(tmp_path):
    module = load_module()
    pack = tmp_path / "eval_skill"
    make_pack(pack)
    (pack / "fixtures").mkdir()
    (pack / "fixtures" / "sample.csv").write_text("x\n1\n", encoding="utf-8")
    evals_path = pack / "evals" / "evals.json"
    payload = json.loads(evals_path.read_text(encoding="utf-8"))
    payload["evals"][0].update(
        {
            "mode": "artifact",
            "artifact_path": "outputs/report.md",
            "file_assertions": [{"type": "file-exists", "path": "report.md"}],
            "fixtures": [
                {
                    "source_path": "fixtures/sample.csv",
                    "target_path": "inputs/sample.csv",
                }
            ],
        }
    )
    evals_path.write_text(json.dumps(payload), encoding="utf-8")
    run_root = tmp_path / "runs"

    jobs = module.build_jobs(
        skill_id="sample-skill",
        eval_skill=pack,
        run_root=run_root,
        model="deepseek-v4-flash-260425",
        agentscope_src=tmp_path / "agentscope",
        runner=tmp_path / "runner.py",
    )

    staged = [
        run_root / mode / "case-1" / "inputs" / "sample.csv"
        for mode in ("with_skill", "without_skill")
    ]
    assert [path.read_text(encoding="utf-8") for path in staged] == ["x\n1\n", "x\n1\n"]
    artifact_jobs = [job for job in jobs if job.get("case_mode") == "artifact"]
    assert all(job["fixture_count"] == 1 for job in artifact_jobs)


def test_build_jobs_expands_skill_commands_only_for_with_skill(tmp_path):
    module = load_module()
    pack = tmp_path / "eval_skill"
    make_pack(pack)
    (pack / "scripts").mkdir()
    (pack / "scripts" / "run.py").write_text("print('ok')\n", encoding="utf-8")
    evals_path = pack / "evals" / "evals.json"
    payload = json.loads(evals_path.read_text(encoding="utf-8"))
    payload["evals"][0].update(
        {
            "mode": "artifact",
            "artifact_path": "outputs/report.md",
            "file_assertions": [{"type": "file-exists", "path": "report.md"}],
            "allowed_commands": [
                'python "{skill_dir}/scripts/run.py" --output "{workspace}/outputs/report.md"'
            ],
        }
    )
    evals_path.write_text(json.dumps(payload), encoding="utf-8")
    run_root = tmp_path / "runs"

    jobs = module.build_jobs(
        skill_id="sample-skill",
        eval_skill=pack,
        run_root=run_root,
        model="deepseek-v4-flash-260425",
        agentscope_src=tmp_path / "agentscope",
        runner=tmp_path / "runner.py",
    )

    with_job = next(job for job in jobs if job["name"].endswith("with_skill-case-1"))
    without_job = next(job for job in jobs if job["name"].endswith("without_skill-case-1"))
    expanded = (
        f'python "{pack.resolve().as_posix()}/scripts/run.py" '
        f'--output "{(run_root / "with_skill" / "case-1").resolve().as_posix()}/outputs/report.md"'
    )
    assert expanded in with_job["args"]
    assert "--allow-command" in with_job["args"]
    assert "--allow-command" not in without_job["args"]


def test_build_jobs_propagates_provider_connection_without_changing_eval_contract(tmp_path):
    module = load_module()
    eval_skill = tmp_path / "eval_skill"
    make_pack(eval_skill)
    jobs = module.build_jobs(
        skill_id="demo-skill",
        eval_skill=eval_skill,
        run_root=tmp_path / "runs",
        model="glm5.2",
        agentscope_src=tmp_path / "agentscope",
        runner=tmp_path / "runner.py",
        base_url="https://newapi.example/v1",
        api_key_env="TASHAN_API_KEY",
        disable_thinking=True,
    )

    assert len(jobs) == 7
    for job in jobs:
        args = job["args"]
        assert args[args.index("--base-url") + 1] == "https://newapi.example/v1"
        assert args[args.index("--api-key-env") + 1] == "TASHAN_API_KEY"
        assert "--disable-thinking" in args


def test_gate_routes_non_discriminating_or_failed_runs_to_codex():
    module = load_module()
    green = module.classify_evidence_gate(
        provider_failures=[],
        invalid_attempt_count=0,
        with_passed=3,
        without_passed=1,
        trigger_accuracy=1.0,
        always_failing=0,
        risk_class="low_risk_guidance",
    )
    red = module.classify_evidence_gate(
        provider_failures=[],
        invalid_attempt_count=0,
        with_passed=3,
        without_passed=1,
        trigger_accuracy=1.0,
        always_failing=1,
        risk_class="low_risk_guidance",
    )

    assert green == "ready_for_scorecard"
    assert red == "codex_adjudication"

    invalid_history = module.classify_evidence_gate(
        provider_failures=[],
        invalid_attempt_count=1,
        with_passed=3,
        without_passed=0,
        trigger_accuracy=1.0,
        always_failing=0,
        risk_class="low_risk_guidance",
    )
    assert invalid_history == "codex_adjudication"


def test_grade_skill_requires_actual_execution_model():
    module = load_module()

    assert "execution_model" in inspect.signature(module.grade_skill).parameters


def test_gate_terminalizes_valid_negative_skill_result_as_fix_first():
    module = load_module()

    gate = module.classify_evidence_gate(
        provider_failures=[],
        invalid_attempt_count=0,
        with_passed=1,
        without_passed=1,
        trigger_accuracy=0.75,
        always_failing=0,
        risk_class="low_risk_guidance",
    )

    assert gate == "ready_for_fix_first"


def test_archive_failed_report_preserves_each_invalid_attempt(tmp_path):
    module = load_module()
    report = tmp_path / "provider-report.json"
    report.write_text('{"status":"tool_permission_denied"}', encoding="utf-8")

    first = module.archive_failed_report(report)
    report.write_text('{"status":"timeout"}', encoding="utf-8")
    second = module.archive_failed_report(report)

    assert first.name == "provider-report.invalid-attempt-1.json"
    assert second.name == "provider-report.invalid-attempt-2.json"
    assert first.is_file() and second.is_file()


def test_normalize_existing_report_archives_prompt_contaminated_text(tmp_path):
    module = load_module()
    report = tmp_path / "provider-report.json"
    report.write_text(
        json.dumps(
            {
                "status": "pass",
                "final_text": "prompt marker\nfinal answer",
                "context": [
                    {"role": "user", "content": [{"type": "text", "text": "prompt marker"}]},
                    {"role": "assistant", "content": [{"type": "text", "text": "final answer"}]},
                ],
            }
        ),
        encoding="utf-8",
    )

    changed = module.normalize_existing_report(report)

    assert changed is True
    assert json.loads(report.read_text(encoding="utf-8"))["final_text"] == "final answer"
    assert (tmp_path / "provider-report.pre-assistant-only.json").is_file()


def test_normalize_existing_report_reclassifies_sandboxed_read_only_probes(tmp_path):
    module = load_module()
    report = tmp_path / "provider-report.json"
    report.write_text(
        json.dumps(
            {
                "status": "tool_permission_denied",
                "source_unchanged": True,
                "workspace_changes": [],
                "allowed_commands": [],
                "allowed_outputs": [],
                "final_text": "complete answer",
                "tool_results": [
                    {
                        "id": "read-outside",
                        "name": "Read",
                        "state": "denied",
                        "text": "outside sandbox",
                    }
                ],
                "context": [
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "complete answer"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    changed = module.normalize_existing_report(report)
    normalized = json.loads(report.read_text(encoding="utf-8"))

    assert changed is True
    assert normalized["status"] == "pass"
    assert normalized["original_status"] == "tool_permission_denied"
    assert normalized["read_only_probe_policy_applied"] is True


def test_normalize_existing_report_never_reclassifies_incomplete_run(tmp_path):
    module = load_module()
    report = tmp_path / "provider-report.json"
    report.write_text(
        json.dumps(
            {
                "status": "incomplete_agent_run",
                "source_unchanged": True,
                "workspace_changes": [],
                "allowed_commands": [],
                "allowed_outputs": [],
                "final_text": "Let me inspect the workspace first.",
                "tool_results": [
                    {
                        "id": "read-outside",
                        "name": "Read",
                        "state": "denied",
                        "text": "outside sandbox",
                    }
                ],
                "context": [
                    {
                        "role": "assistant",
                        "content": [
                            {"type": "text", "text": "Let me inspect the workspace first."}
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    changed = module.normalize_existing_report(report)
    normalized = json.loads(report.read_text(encoding="utf-8"))

    assert changed is False
    assert normalized["status"] == "incomplete_agent_run"
    assert "read_only_probe_policy_applied" not in normalized


def _sample_jobs(skill_id="sample-skill"):
    jobs = []
    for case_index in range(1, 4):
        for mode in ("with_skill", "without_skill"):
            jobs.append(
                {
                    "skill_id": skill_id,
                    "name": f"{skill_id}-{mode}-case-{case_index}",
                    "kind": "behavior",
                    "attempt": f"case-{case_index}",
                }
            )
    jobs.append(
        {
            "skill_id": skill_id,
            "name": f"{skill_id}-triggers",
            "kind": "trigger",
        }
    )
    return jobs


def test_staged_runner_stops_after_first_pair_when_canary_is_invalid(monkeypatch, tmp_path):
    module = load_module()
    jobs = _sample_jobs()
    calls = []

    def fake_run_group(group, *, concurrency, resume):
        calls.append([job["name"] for job in group])
        return [
            {
                "name": job["name"],
                "kind": job["kind"],
                "status": "pass",
                "exit": 0,
                "seconds": 1.0,
                "resumed": False,
            }
            for job in group
        ]

    monkeypatch.setattr(module, "run_job_group", fake_run_group)
    monkeypatch.setattr(
        module,
        "run_first_pair_canary",
        lambda *args, **kwargs: {
            "status": "invalid",
            "always_failing_assertions": 1,
        },
    )

    results, canaries = module.run_staged_jobs(
        jobs,
        {"sample-skill": (tmp_path / "eval_skill", tmp_path / "run")},
        concurrency=8,
        resume=False,
    )

    assert len(calls) == 1
    assert len(calls[0]) == 2
    assert canaries["sample-skill"]["status"] == "invalid"
    assert sum(result["status"] == "skipped_canary_invalid" for result in results) == 5


def test_staged_runner_releases_remaining_jobs_only_after_canary_passes(monkeypatch, tmp_path):
    module = load_module()
    jobs = _sample_jobs()
    calls = []

    def fake_run_group(group, *, concurrency, resume):
        calls.append([job["name"] for job in group])
        return [
            {
                "name": job["name"],
                "kind": job["kind"],
                "status": "pass",
                "exit": 0,
                "seconds": 1.0,
                "resumed": False,
            }
            for job in group
        ]

    monkeypatch.setattr(module, "run_job_group", fake_run_group)
    monkeypatch.setattr(
        module,
        "run_first_pair_canary",
        lambda *args, **kwargs: {
            "status": "pass",
            "always_failing_assertions": 0,
        },
    )

    results, canaries = module.run_staged_jobs(
        jobs,
        {"sample-skill": (tmp_path / "eval_skill", tmp_path / "run")},
        concurrency=8,
        resume=False,
    )

    assert [len(call) for call in calls] == [2, 5]
    assert canaries["sample-skill"]["status"] == "pass"
    assert len(results) == 7
    assert all(result["status"] == "pass" for result in results)


def test_first_pair_canary_uses_vendored_grader_and_flags_always_failing(tmp_path):
    module = load_module()
    eval_skill = tmp_path / "eval_skill"
    make_pack(eval_skill)
    evals_path = eval_skill / "evals" / "evals.json"
    payload = json.loads(evals_path.read_text(encoding="utf-8"))
    payload["evals"][0]["assertions"] = [
        {"type": "contains", "value": "never produced"}
    ]
    evals_path.write_text(json.dumps(payload), encoding="utf-8")
    run_root = tmp_path / "run"
    for mode in ("with_skill", "without_skill"):
        workspace = run_root / mode / "case-1"
        workspace.mkdir(parents=True)
        (workspace / "provider-report.json").write_text(
            json.dumps(
                {
                    "status": "pass",
                    "source_unchanged": True,
                    "workspace": str(workspace.resolve()),
                    "workspace_changes": [],
                    "final_text": "A valid response without the required anchor.",
                    "context": [],
                }
            ),
            encoding="utf-8",
        )

    evidence = module.run_first_pair_canary(
        "sample-skill", eval_skill, run_root
    )

    assert evidence["status"] == "invalid"
    assert evidence["always_failing_assertions"] == 1
    assert evidence["remaining_jobs_released"] is False
    assert (run_root / "assertion-canary-grader.json").is_file()


def test_external_single_skill_layout_stays_inside_worker_run_root(tmp_path):
    module = load_module()
    eval_skill = tmp_path / "worker" / "eval_skill"
    run_root = tmp_path / "worker" / "complete"

    roots, artifact_root = module.resolve_run_layout(
        ["fresh-github-skill"],
        run_label="unused-catalog-label",
        eval_skill=eval_skill,
        run_root=run_root,
    )

    assert roots == {"fresh-github-skill": (eval_skill.resolve(), run_root.resolve())}
    assert artifact_root == run_root.resolve()


def test_external_single_skill_layout_requires_both_paths_and_one_id(tmp_path):
    module = load_module()

    with pytest.raises(ValueError, match="together"):
        module.resolve_run_layout(
            ["fresh-github-skill"],
            run_label="run",
            eval_skill=tmp_path / "eval_skill",
            run_root=None,
        )
    with pytest.raises(ValueError, match="exactly one"):
        module.resolve_run_layout(
            ["first", "second"],
            run_label="run",
            eval_skill=tmp_path / "eval_skill",
            run_root=tmp_path / "run",
        )
