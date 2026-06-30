import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIGURE = ROOT / "scripts" / "configure_manim_provider.py"
CHECK_ENV = ROOT / "scripts" / "check_manim_agent_env.py"


def run_configure(*args, env=None):
    completed = subprocess.run(
        [sys.executable, str(CONFIGURE), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, **(env or {})},
    )
    return completed.stdout


def run_configure_json(*args, env=None):
    return json.loads(run_configure(*args, "--format", "json", env=env))


def test_aliyun_regular_profile_outputs_anthropic_env_without_secret_value():
    stdout = run_configure(
        "--provider",
        "aliyun",
        "--route",
        "regular",
        "--format",
        "powershell",
        env={"ALIYUN_DASHSCOPE_API_KEY": "test-secret-value"},
    )

    assert '$env:ANTHROPIC_AUTH_TOKEN = $env:ALIYUN_DASHSCOPE_API_KEY' in stdout
    assert '$env:ANTHROPIC_BASE_URL = "https://dashscope.aliyuncs.com/apps/anthropic"' in stdout
    assert '$env:ANTHROPIC_MODEL = "qwen3.7-plus"' in stdout
    assert "test-secret-value" not in stdout


def test_aliyun_plan_routes_have_distinct_anthropic_endpoints():
    token_plan = run_configure_json("--provider", "aliyun", "--route", "token-plan")
    coding_plan = run_configure_json("--provider", "aliyun", "--route", "coding-plan")

    assert token_plan["base_url"] == "https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic"
    assert coding_plan["base_url"] == "https://coding.dashscope.aliyuncs.com/apps/anthropic"
    assert token_plan["base_url"] != coding_plan["base_url"]


def test_volcengine_regular_and_coding_plan_profiles_are_supported_and_distinct():
    regular = run_configure_json(
        "--provider",
        "volcengine",
        "--route",
        "regular",
        env={"ARK_API_KEY": "test-secret-value"},
    )
    coding_plan = run_configure_json(
        "--provider",
        "volcengine",
        "--route",
        "coding-plan",
        env={"ARK_API_KEY": "test-secret-value"},
    )

    assert regular["base_url"] == "https://ark.cn-beijing.volces.com/api/compatible"
    assert coding_plan["base_url"] == "https://ark.cn-beijing.volces.com/api/coding"
    assert regular["auth_token_env"] == "ARK_API_KEY"
    assert coding_plan["auth_token_env"] == "ARK_API_KEY"
    assert regular["base_url"] != coding_plan["base_url"]
    assert "test-secret-value" not in json.dumps(regular)
    assert "test-secret-value" not in json.dumps(coding_plan)


def test_profiles_prefer_provider_source_env_over_existing_global_anthropic_env():
    profile = run_configure_json(
        "--provider",
        "volcengine",
        "--route",
        "regular",
        env={
            "ARK_API_KEY": "",
            "VOLCENGINE_API_KEY": "",
            "ANTHROPIC_AUTH_TOKEN": "already-mapped-global-token",
        },
    )

    assert profile["auth_token_env"] == "ARK_API_KEY"
    assert "already-mapped-global-token" not in json.dumps(profile)


def test_volcengine_regular_profile_accepts_current_console_overrides():
    profile = run_configure_json(
        "--provider",
        "volcengine",
        "--route",
        "regular",
        "--base-url",
        "https://example.test/anthropic-compatible",
        "--model",
        "custom-console-model",
        "--auth-env",
        "VOLCENGINE_API_KEY",
    )

    assert profile["base_url"] == "https://example.test/anthropic-compatible"
    assert profile["model"] == "custom-console-model"
    assert profile["auth_token_env"] == "VOLCENGINE_API_KEY"


def test_check_env_reports_provider_key_candidates_without_printing_values(tmp_path):
    fake_repo = tmp_path / "manim-agent"
    (fake_repo / "src" / "manim_agent").mkdir(parents=True)
    (fake_repo / "plugins" / "manim-production").mkdir(parents=True)
    (fake_repo / "pyproject.toml").write_text("[project]\nname = 'manim-agent'\n", encoding="utf-8")
    (fake_repo / "src" / "manim_agent" / "__main__.py").write_text("", encoding="utf-8")

    env = {
        **os.environ,
        "MANIM_AGENT_LLM_PROVIDER": "volcengine",
        "ARK_API_KEY": "test-secret-value",
        "ANTHROPIC_BASE_URL": "https://ark.cn-beijing.volces.com/api/compatible",
        "ANTHROPIC_MODEL": "doubao-seed-code-preview-latest",
    }
    completed = subprocess.run(
        [sys.executable, str(CHECK_ENV), "--repo", str(fake_repo)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )

    assert "MANIM_AGENT_LLM_PROVIDER" in completed.stdout
    assert "ARK_API_KEY" in completed.stdout
    assert "volcengine" in completed.stdout.lower()
    assert "test-secret-value" not in completed.stdout
    assert "test-secret-value" not in completed.stderr
