import asyncio
import importlib.util
import json
import pathlib

import pytest


SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_DIR / "scripts" / "run_agentscope_critic_provider.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "run_agentscope_critic_provider",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_load_claude_settings_keeps_credential_in_memory(tmp_path):
    module = load_module()
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {
                "env": {
                    "ANTHROPIC_AUTH_TOKEN": "secret-token",
                    "ANTHROPIC_BASE_URL": "https://provider.example/anthropic",
                    "ANTHROPIC_MODEL": "deepseek-v4-pro",
                }
            }
        ),
        encoding="utf-8",
    )

    loaded = module.load_claude_settings(settings)

    assert loaded == {
        "api_key": "secret-token",
        "base_url": "https://provider.example/anthropic",
        "model": "deepseek-v4-pro",
        "protocol": "anthropic",
        "auth_mode": "auth-token",
    }


def test_load_claude_settings_rejects_missing_required_values(tmp_path):
    module = load_module()
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"env": {}}), encoding="utf-8")

    with pytest.raises(ValueError, match="ANTHROPIC_AUTH_TOKEN"):
        module.load_claude_settings(settings)


def test_bash_constructor_compatibility_keeps_workspace_binding(tmp_path):
    module = load_module()

    class BashWithCwd:
        def __init__(self, cwd):
            self.cwd = cwd

    class BashWithoutCwd:
        def __init__(self):
            self.ready = True

    legacy = module.construct_bash_tool(BashWithCwd, tmp_path)
    current = module.construct_bash_tool(BashWithoutCwd, tmp_path)

    assert legacy.cwd == str(tmp_path.resolve())
    assert not hasattr(legacy, "_critic_workspace")
    assert current.ready
    assert current._critic_workspace == tmp_path.resolve()
    assert module.command_in_workspace(tmp_path, "python C:/grader.py") == (
        f'cd "{tmp_path.resolve()}" && python C:/grader.py'
    )


def test_exact_command_policy_rejects_appended_pipeline(tmp_path):
    module = load_module()
    command = "python scripts/filter_science_skills.py --json"
    allowed = module.allowed_command_forms(tmp_path, [command])

    assert module.command_is_allowed(command, allowed)
    assert module.command_is_allowed(
        f'cd "{tmp_path.resolve()}" && {command}',
        allowed,
    )
    assert not module.command_is_allowed(
        command + ' | python -c "print(1)"',
        allowed,
    )
    assert not module.command_is_allowed("python -c \"print(1)\"", allowed)


def test_classification_keeps_provider_and_skill_failures_separate():
    module = load_module()

    assert module.classify_run(timed_out=True) == "timeout"
    assert module.classify_run(error="401 Unauthorized") == "auth_error"
    assert (
        module.classify_run(tool_states=["success", "denied"])
        == "tool_permission_denied"
    )
    assert module.classify_run(tool_states=["success"]) == "pass"
    assert module.classify_run(tool_states=[]) == "no_tool_execution"
    assert (
        module.classify_run(
            tool_states=["success"],
            duplicate_write_attempts=1,
        )
        == "repeated_output_write"
    )


def test_missing_file_reads_are_recoverable_when_report_write_succeeds():
    module = load_module()
    results = [
        {
            "id": "read-missing",
            "name": "Read",
            "state": "error",
            "text": "Error: File does not exist: C:/case/summary.csv",
        },
        {
            "id": "write-report",
            "name": "Write",
            "state": "success",
            "text": "written successfully",
        },
    ]

    assert module.recoverable_read_errors(results)
    assert module.classify_run(tool_results=results) == "pass"
    assert not module.recoverable_read_errors(
        [{"name": "Write", "state": "error", "text": "disk full"}]
    )
    assert (
        module.classify_run(
            tool_results=[{"name": "Write", "state": "error", "text": "disk full"}]
        )
        == "tool_execution_error"
    )


def test_diagnostic_command_exit_defers_to_declared_artifact_assertions():
    module = load_module()
    result = [{"name": "Bash", "state": "error", "text": "Command failed: exit 2"}]

    assert (
        module.classify_run(
            tool_results=result,
            declared_artifacts_ready=True,
        )
        == "pass"
    )
    assert (
        module.classify_run(
            tool_results=result,
            declared_artifacts_ready=False,
        )
        == "tool_execution_error"
    )
    assert (
        module.classify_run(
            tool_results=[{"name": "Bash", "state": "denied", "text": "blocked"}],
            declared_artifacts_ready=True,
        )
        == "tool_permission_denied"
    )


def test_mounted_source_requires_exactly_one_skill_invocation():
    module = load_module()

    assert (
        module.classify_run(
            tool_states=["success"],
            skill_required=True,
            skill_invocation_count=0,
        )
        == "missing_skill_invocation"
    )
    assert (
        module.classify_run(
            tool_states=["success"],
            skill_required=True,
            skill_invocation_count=2,
        )
        == "repeated_skill_invocation"
    )
    assert (
        module.classify_run(
            tool_states=["success"],
            skill_required=True,
            skill_invocation_count=1,
        )
        == "pass"
    )


def test_forced_first_skill_middleware_only_changes_first_reasoning_call():
    module = load_module()

    class FakeMiddlewareBase:
        pass

    class FakeToolChoice:
        def __init__(self, mode):
            self.mode = mode

    middleware = module.construct_forced_first_skill_middleware(
        {
            "MiddlewareBase": FakeMiddlewareBase,
            "ToolChoice": FakeToolChoice,
        },
        enabled=True,
    )
    calls = []

    async def next_handler(**kwargs):
        calls.append(kwargs)
        yield kwargs

    async def exercise():
        first = [
            item
            async for item in middleware.on_reasoning(
                agent=None,
                input_kwargs={"tool_choice": None},
                next_handler=next_handler,
            )
        ]
        second = [
            item
            async for item in middleware.on_reasoning(
                agent=None,
                input_kwargs={"tool_choice": None},
                next_handler=next_handler,
            )
        ]
        return first, second

    first, second = asyncio.run(exercise())

    assert first[0]["tool_choice"].mode == "Skill"
    assert second[0]["tool_choice"].mode == "none"
    assert calls[0]["tool_choice"].mode == "Skill"
    assert calls[1]["tool_choice"].mode == "none"
    assert middleware.forced_selection_count == 1
    assert (
        module.construct_forced_first_skill_middleware(
            {
                "MiddlewareBase": FakeMiddlewareBase,
                "ToolChoice": FakeToolChoice,
            },
            enabled=False,
        )
        is None
    )


def test_directory_read_probe_is_recoverable_but_permission_error_is_not():
    module = load_module()
    report_write = {
        "id": "write-report",
        "name": "Write",
        "state": "success",
        "text": "written successfully",
    }
    directory_probe = {
        "id": "read-directory",
        "name": "Read",
        "state": "error",
        "text": "Error: Path is a directory, not a file: C:/case",
    }
    permission_error = {
        "id": "read-denied",
        "name": "Read",
        "state": "error",
        "text": "Error: Access denied: C:/outside/secret.txt",
    }

    assert module.recoverable_read_errors([directory_probe, report_write])
    assert module.classify_run(tool_results=[directory_probe, report_write]) == "pass"
    assert not module.recoverable_read_errors([permission_error, report_write])
    assert (
        module.classify_run(tool_results=[permission_error, report_write])
        == "tool_execution_error"
    )


def test_read_only_sandboxed_read_probes_do_not_hide_write_denials():
    module = load_module()
    denied_read = {
        "id": "read-outside",
        "name": "Read",
        "state": "denied",
        "text": "Read is outside the workspace and mounted source",
    }
    missing_read = {
        "id": "read-missing",
        "name": "Read",
        "state": "error",
        "text": "File does not exist",
    }
    denied_write = {
        "id": "write-outside",
        "name": "Write",
        "state": "denied",
        "text": "Write is outside the declared evaluation outputs",
    }

    assert (
        module.classify_run(
            tool_results=[denied_read, missing_read],
            allow_no_tool=True,
            read_only_probe_failures_are_nonfatal=True,
        )
        == "pass"
    )
    assert (
        module.classify_run(
            tool_results=[denied_write],
            allow_no_tool=True,
            read_only_probe_failures_are_nonfatal=True,
        )
        == "tool_permission_denied"
    )


def test_redaction_removes_environment_secret_without_hiding_other_text():
    module = load_module()
    secret = "secret-value-for-test"
    value = f"provider failed with token {secret} after timeout"

    assert module.redact_secret(value, secret) == (
        "provider failed with token [REDACTED] after timeout"
    )


def test_provider_transport_retries_have_a_small_nonzero_default():
    module = load_module()

    assert module.DEFAULT_PROVIDER_RETRIES == 2


def test_chat_model_factory_supports_openai_and_anthropic_protocols():
    module = load_module()
    calls = []

    class Credential:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class Model:
        class Parameters:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        def __init__(self, **kwargs):
            calls.append(kwargs)

    symbols = {
        "OpenAICredential": Credential,
        "OpenAIChatModel": Model,
        "AnthropicCredential": Credential,
        "AnthropicChatModel": Model,
    }

    _, openai_provider = module.construct_chat_model(
        symbols,
        protocol="openai",
        api_key="secret",
        base_url="https://openai.example/v1",
        model_name="flash-openai",
        timeout=30,
        provider_retries=1,
        max_output_tokens=4096,
    )
    _, anthropic_provider = module.construct_chat_model(
        symbols,
        protocol="anthropic",
        api_key="secret",
        base_url="https://anthropic.example",
        model_name="flash-anthropic",
        timeout=30,
        provider_retries=1,
        auth_mode="auth-token",
    )

    assert openai_provider == "agentscope-openai-compatible"
    assert anthropic_provider == "agentscope-anthropic-compatible"
    assert calls[0]["model"] == "flash-openai"
    assert calls[1]["model"] == "flash-anthropic"
    assert calls[0]["credential"].kwargs["base_url"] == "https://openai.example/v1"
    assert calls[0]["parameters"].kwargs["max_tokens"] == 4096
    assert calls[1]["credential"].kwargs["base_url"] == "https://anthropic.example"
    assert calls[1]["client_kwargs"]["api_key"] is None
    assert calls[1]["client_kwargs"]["auth_token"] == "secret"


def test_openai_chat_model_can_disable_thinking_for_every_call():
    module = load_module()
    api_calls = []

    class Credential:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class Model:
        class Parameters:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def __call__(
            self,
            messages,
            tools=None,
            tool_choice=None,
            **kwargs,
        ):
            api_calls.append(kwargs)
            return "ok"

    model, _ = module.construct_chat_model(
        {
            "OpenAICredential": Credential,
            "OpenAIChatModel": Model,
        },
        protocol="openai",
        api_key="secret",
        base_url="https://openai.example/v1",
        model_name="thinking-model",
        timeout=30,
        provider_retries=1,
        disable_thinking=True,
    )

    result = asyncio.run(model([{"role": "user", "content": "test"}]))

    assert result == "ok"
    assert api_calls == [{"extra_body": {"thinking": {"type": "disabled"}}}]


def test_tree_manifest_detects_source_mutation(tmp_path):
    module = load_module()
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("before\n", encoding="utf-8")

    before = module.tree_manifest(skill)
    (skill / "SKILL.md").write_text("after\n", encoding="utf-8")
    after = module.tree_manifest(skill)

    assert before["sha256"] != after["sha256"]
    assert before["files"][0]["path"] == "SKILL.md"


def test_workspace_and_mounted_skill_must_not_overlap(tmp_path):
    module = load_module()
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    workspace.mkdir()
    source.mkdir()

    module.validate_isolation(workspace, source)
    with pytest.raises(ValueError, match="must not overlap"):
        module.validate_isolation(workspace, workspace / "mounted-skill")
    with pytest.raises(ValueError, match="must not overlap"):
        module.validate_isolation(source / "case", source)


def test_read_boundary_allows_workspace_and_mounted_source_only(tmp_path):
    module = load_module()
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    outside = tmp_path / "outside"
    workspace.mkdir()
    source.mkdir()
    outside.mkdir()

    assert module.read_path_is_allowed(workspace, source, workspace / "input.md")
    assert module.read_path_is_allowed(source=source, workspace=workspace, raw_path=source / "references" / "guide.md")
    assert not module.read_path_is_allowed(workspace, source, outside / "secret.txt")


def test_relative_tool_paths_resolve_against_workspace_root(tmp_path):
    module = load_module()
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    outside = tmp_path / "outside"
    workspace.mkdir()
    source.mkdir()
    outside.mkdir()

    assert module.resolve_workspace_path(workspace, "evidence/manifest.json") == (
        workspace / "evidence" / "manifest.json"
    ).resolve()
    assert module.read_path_is_allowed(workspace, source, "evidence/manifest.json")
    assert not module.read_path_is_allowed(workspace, source, "../outside/secret.txt")

    allowed = module.normalize_allowed_outputs(workspace, ["outputs/report.md"])
    assert module.write_path_is_allowed(workspace, allowed, "outputs/report.md")
    assert not module.write_path_is_allowed(workspace, allowed, "../outside/report.md")


def test_output_allowlist_is_exact_and_workspace_scoped(tmp_path):
    module = load_module()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    allowed = module.normalize_allowed_outputs(
        workspace,
        ["outputs/report.md"],
    )

    assert allowed == {(workspace / "outputs" / "report.md").resolve()}
    assert module.write_path_is_allowed(
        workspace,
        allowed,
        workspace / "outputs" / "report.md",
    )
    assert not module.write_path_is_allowed(
        workspace,
        allowed,
        workspace / "test.txt",
    )
    with pytest.raises(ValueError, match="outside the workspace"):
        module.normalize_allowed_outputs(workspace, ["../outside.txt"])


def test_prepare_output_directories_creates_parents_without_faking_artifacts(tmp_path):
    module = load_module()
    output = (tmp_path / "outputs" / "nested" / "report.json").resolve()

    module.prepare_output_directories({output})

    assert output.parent.is_dir()
    assert not output.exists()


def test_empty_output_allowlist_keeps_workspace_compatibility(tmp_path):
    module = load_module()
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    assert module.write_path_is_allowed(
        workspace,
        set(),
        workspace / "legacy-output.md",
    )


def test_directory_inventory_is_deterministic_and_bounded(tmp_path):
    module = load_module()
    root = tmp_path / "workspace"
    (root / "nested").mkdir(parents=True)
    (root / "z.txt").write_text("z", encoding="utf-8")
    (root / "nested" / "a.txt").write_text("a", encoding="utf-8")

    assert module.directory_inventory(root) == ["nested/a.txt", "z.txt"]
    assert module.directory_inventory(root, max_entries=1) == ["nested/a.txt"]


def test_guidance_only_contract_allows_read_but_disables_write_and_shell():
    module = load_module()

    assert module.enabled_host_tool_names(
        guidance_only=True, has_commands=True, skill_only=False
    ) == (
        "Read",
    )
    assert module.enabled_host_tool_names(
        guidance_only=False, has_commands=False, skill_only=False
    ) == (
        "Read",
        "Write",
    )
    assert module.enabled_host_tool_names(
        guidance_only=False, has_commands=True, skill_only=False
    ) == (
        "Read",
        "Write",
        "Bash",
    )
    assert module.enabled_host_tool_names(
        guidance_only=True, has_commands=False, skill_only=True
    ) == ()
    assert module.enabled_host_tool_names(
        guidance_only=True,
        has_commands=False,
        skill_only=False,
        has_source=False,
    ) == ()


def test_guidance_prompt_forbids_evaluation_internals_and_parent_enumeration():
    module = load_module()

    prompt = module.base_system_prompt(guidance_only=True, skill_only=False)

    assert "Do not enumerate parent directories" in prompt
    assert "provider-prompt" in prompt
    assert "provider-report" in prompt


def test_runtime_guidance_prompt_declares_inventory_and_missing_dependencies(tmp_path):
    module = load_module()
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    workspace.mkdir()
    (source / "references").mkdir(parents=True)
    (workspace / "input.md").write_text("input", encoding="utf-8")
    (source / "SKILL.md").write_text("skill", encoding="utf-8")
    (source / "references" / "guide.md").write_text("guide", encoding="utf-8")

    prompt = module.build_runtime_system_prompt(
        guidance_only=True,
        skill_only=False,
        workspace=workspace,
        source=source,
        allowed_outputs=set(),
        allowed_commands=[],
    )

    assert "Workspace files at start: input.md" in prompt
    assert "Mounted source files: SKILL.md, references/guide.md" in prompt
    assert str(source.resolve()) in prompt
    assert "Treat every unlisted sibling skill, API, CLI, service, and hardware" in prompt
    assert "Call the mounted Skill tool exactly once" in prompt


def test_runtime_prompt_exposes_exact_command_without_relaxing_allowlist(tmp_path):
    module = load_module()
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    workspace.mkdir()
    source.mkdir()
    command = 'python "C:/mounted/scripts/run.py" --output "C:/work/report.json"'

    prompt = module.build_runtime_system_prompt(
        guidance_only=False,
        skill_only=False,
        workspace=workspace,
        source=source,
        allowed_outputs=set(),
        allowed_commands=[command],
    )

    assert "copy one command character-for-character" in prompt
    assert command in prompt
    assert "Do not create output directories" in prompt
    assert "Never synthesize a placeholder" in prompt


def test_runtime_behavior_prompt_forbids_unlisted_dependency_probes(tmp_path):
    module = load_module()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "input.tex").write_text("paper", encoding="utf-8")

    prompt = module.build_runtime_system_prompt(
        guidance_only=False,
        skill_only=False,
        workspace=workspace,
        source=None,
        allowed_outputs=set(),
        allowed_commands=[],
    )

    assert "Treat every unlisted input, script, API, CLI, service, and hardware" in prompt
    assert "Do not probe parent directories" in prompt
    assert "report the missing dependency" in prompt


def test_behavior_prompt_forbids_evaluation_internals_and_long_calculation_narration():
    module = load_module()

    prompt = module.base_system_prompt(guidance_only=False, skill_only=False)

    assert "provider-prompt" in prompt
    assert "provider-report" in prompt
    assert "Do not narrate calculations" in prompt


def test_skill_only_prompt_forbids_host_tools_and_requires_mounted_source():
    module = load_module()

    prompt = module.base_system_prompt(guidance_only=True, skill_only=True)

    assert "Skill tool" in prompt
    assert "Do not call Read, Write, or Bash" in prompt


def test_final_text_uses_only_last_assistant_message():
    module = load_module()
    context = [
        {"role": "user", "content": [{"type": "text", "text": "secret prompt marker"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "intermediate"}]},
        {"role": "tool", "content": [{"type": "tool_result", "text": "tool result"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "final answer"}]},
    ]

    assert module.final_assistant_text(context) == "final answer"
