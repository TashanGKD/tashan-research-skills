#!/usr/bin/env python
"""Check the local manim-agent runtime without printing secrets."""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_version(command: list[str], timeout: int = 12) -> tuple[bool, str]:
    exe = shutil.which(command[0])
    if not exe:
        return False, "not found in PATH"
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - defensive environment helper
        return False, f"error: {exc}"
    output = (result.stdout or result.stderr or "").strip().splitlines()
    first_line = output[0] if output else f"exit {result.returncode}"
    return result.returncode == 0, first_line


def yes_no(value: bool) -> str:
    return "ok" if value else "missing"


def check_python_package(import_name: str) -> tuple[bool, str]:
    found = importlib.util.find_spec(import_name) is not None
    return found, "importable" if found else "not importable"


def repo_venv_python(repo: Path) -> Path:
    return repo / ".venv" / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")


def run_python_probe(python_exe: Path, code: str, timeout: int = 20) -> tuple[bool, str]:
    if not python_exe.exists():
        return False, f"not found: {python_exe}"
    try:
        result = subprocess.run(
            [str(python_exe), "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - defensive environment helper
        return False, f"error: {exc}"
    output = (result.stdout or result.stderr or "").strip().splitlines()
    first_line = output[0] if output else f"exit {result.returncode}"
    return result.returncode == 0, first_line


def check_repo_venv_package(repo: Path, import_name: str) -> tuple[bool, str]:
    return run_python_probe(
        repo_venv_python(repo),
        f"import {import_name}; print('importable')",
    )


def infer_llm_provider() -> str:
    explicit = os.getenv("MANIM_AGENT_LLM_PROVIDER")
    if explicit:
        return explicit

    base_url = (os.getenv("ANTHROPIC_BASE_URL") or "").lower()
    if "dashscope" in base_url or "aliyuncs" in base_url:
        return "aliyun"
    if "volces" in base_url or "volcengine" in base_url or "byteplus" in base_url:
        return "volcengine"
    if base_url:
        return "custom"
    return "unknown"


def infer_tts_provider() -> str:
    explicit = os.getenv("MANIM_AGENT_TTS_PROVIDER")
    if explicit:
        return explicit
    if os.getenv("DASHSCOPE_API_KEY") or os.getenv("ALIYUN_DASHSCOPE_API_KEY"):
        return "aliyun"
    if (
        os.getenv("VOLCENGINE_TTS_API_KEY")
        or os.getenv("VOLCENGINE_TTS_ACCESS_TOKEN")
        or os.getenv("VOLCENGINE_TTS_APP_ID")
    ):
        return "volcengine"
    return "unknown"


def has_llm_key() -> bool:
    return any(
        os.getenv(name)
        for name in [
            "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_API_KEY",
            "ARK_API_KEY",
            "VOLCENGINE_API_KEY",
            "ALIYUN_DASHSCOPE_API_KEY",
            "ALIYUN_TOKEN_PLAN_API_KEY",
            "ALIYUN_CODING_PLAN_API_KEY",
        ]
    )


def has_tts_key() -> bool:
    return any(
        os.getenv(name)
        for name in [
            "DASHSCOPE_API_KEY",
            "ALIYUN_DASHSCOPE_API_KEY",
            "VOLCENGINE_TTS_API_KEY",
            "VOLCENGINE_TTS_ACCESS_TOKEN",
            "VOLCENGINE_TTS_APP_ID",
            "MANIM_AGENT_TTS_AUTH_TOKEN",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Check manim-agent local runtime.")
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to the local gqy20/manim-agent repository.",
    )
    args = parser.parse_args()

    repo = Path(args.repo)
    checks: list[tuple[str, bool, str]] = []

    checks.append(("repo", repo.exists(), str(repo)))
    checks.append(("pyproject", (repo / "pyproject.toml").exists(), str(repo / "pyproject.toml")))
    checks.append(("cli_entry", (repo / "src" / "manim_agent" / "__main__.py").exists(), "src/manim_agent/__main__.py"))
    checks.append(("production_plugin", (repo / "plugins" / "manim-production").exists(), "plugins/manim-production"))

    py_ok = sys.version_info >= (3, 12)
    checks.append(("python>=3.12", py_ok, sys.version.split()[0]))
    venv_python = repo_venv_python(repo)
    venv_py_ok, venv_py_detail = run_python_probe(
        venv_python,
        "import sys; print('.'.join(map(str, sys.version_info[:3])))",
    )
    venv_version_ok = False
    if venv_py_ok:
        try:
            parts = [int(part) for part in venv_py_detail.split(".")[:2]]
            venv_version_ok = tuple(parts) >= (3, 12)
        except ValueError:
            venv_version_ok = False
    checks.append(("repo_venv_python>=3.12", venv_py_ok and venv_version_ok, venv_py_detail))

    for name, cmd in [
        ("uv", ["uv", "--version"]),
        ("git", ["git", "--version"]),
        ("manim", ["manim", "--version"]),
        ("ffmpeg", ["ffmpeg", "-version"]),
    ]:
        ok, detail = run_version(cmd)
        checks.append((name, ok, detail))

    for package in [
        "claude_agent_sdk",
        "manim",
        "httpx",
    ]:
        ok, detail = check_python_package(package)
        checks.append((f"py:{package}", ok, detail))
        venv_ok, venv_detail = check_repo_venv_package(repo, package)
        checks.append((f"repo_venv:{package}", venv_ok, venv_detail))

    for env_name in [
        "MANIM_AGENT_LLM_PROVIDER",
        "MANIM_AGENT_LLM_ROUTE",
        "DASHSCOPE_API_KEY",
        "ALIYUN_DASHSCOPE_API_KEY",
        "ALIYUN_TOKEN_PLAN_API_KEY",
        "ALIYUN_CODING_PLAN_API_KEY",
        "ARK_API_KEY",
        "VOLCENGINE_API_KEY",
        "DATABASE_URL",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
        "MANIM_AGENT_TTS_PROVIDER",
        "MANIM_AGENT_TTS_ROUTE",
        "MANIM_AGENT_TTS_MODEL",
        "MANIM_AGENT_TTS_VOICE",
        "MANIM_AGENT_TTS_AUTH_TOKEN",
        "VOLCENGINE_TTS_API_KEY",
        "VOLCENGINE_TTS_ACCESS_TOKEN",
        "VOLCENGINE_TTS_APP_ID",
        "VOLCENGINE_TTS_CLUSTER",
    ]:
        checks.append((env_name, bool(os.getenv(env_name)), "set" if os.getenv(env_name) else "not set"))

    max_name = max(len(name) for name, _, _ in checks)
    required_status: dict[str, bool] = {}
    for name, ok, detail in checks:
        print(f"{name.ljust(max_name)}  {yes_no(ok):8}  {detail}")
        if name in {
            "repo",
            "pyproject",
            "cli_entry",
            "production_plugin",
            "ffmpeg",
        }:
            required_status[name] = ok

    python_runtime_ok = dict((name, ok) for name, ok, _ in checks).get("python>=3.12", False) or dict(
        (name, ok) for name, ok, _ in checks
    ).get("repo_venv_python>=3.12", False)
    manim_runtime_ok = dict((name, ok) for name, ok, _ in checks).get("manim", False) or dict(
        (name, ok) for name, ok, _ in checks
    ).get("repo_venv:manim", False)
    package_runtime_ok = all(
        dict((name, ok) for name, ok, _ in checks).get(f"py:{package}", False)
        or dict((name, ok) for name, ok, _ in checks).get(f"repo_venv:{package}", False)
        for package in ["claude_agent_sdk", "manim", "httpx"]
    )
    failed_required = not (
        all(required_status.values())
        and python_runtime_ok
        and manim_runtime_ok
        and package_runtime_ok
    )

    if os.getenv("DASHSCOPE_API_KEY"):
        print("note: DASHSCOPE_API_KEY can drive DashScope LLM and DashScope CosyVoice TTS when the matching env vars are set.")
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("note: DASHSCOPE_API_KEY is needed for Aliyun DashScope CosyVoice TTS and DashScope direct checks.")
    print(f"note: inferred LLM provider profile: {infer_llm_provider()}")
    print(f"note: inferred TTS provider profile: {infer_tts_provider()}")
    if os.getenv("ALIYUN_DASHSCOPE_API_KEY") or os.getenv("ALIYUN_TOKEN_PLAN_API_KEY") or os.getenv("ALIYUN_CODING_PLAN_API_KEY"):
        print("note: Aliyun key env is available; map it with configure_manim_provider.py --provider aliyun --route regular|token-plan|coding-plan.")
    if os.getenv("ARK_API_KEY") or os.getenv("VOLCENGINE_API_KEY"):
        print("note: Volcengine Ark key env is available; map it with configure_manim_provider.py --provider volcengine --route regular|coding-plan.")
    if os.getenv("VOLCENGINE_TTS_API_KEY") or os.getenv("VOLCENGINE_TTS_ACCESS_TOKEN") or os.getenv("VOLCENGINE_TTS_APP_ID"):
        print("note: Volcengine TTS env is available; map it with configure_manim_provider.py --provider volcengine --purpose tts.")
    if not os.getenv("DATABASE_URL"):
        print("note: DATABASE_URL is needed for Web/backend persistence, not for direct CLI no-persistence runs.")
    if repo_venv_python(repo).exists():
        print("note: repo .venv is available; direct CLI runs can use .venv\\Scripts\\python.exe -m manim_agent on Windows.")
    if not (os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY")):
        print("note: Claude Agent SDK needs local Claude auth or ANTHROPIC_AUTH_TOKEN/ANTHROPIC_API_KEY for normal pipeline runs.")
    if not has_llm_key():
        print("action: For Manim LLM access, apply for or refresh a key in the Volcengine Ark console or Aliyun DashScope/Bailian console, then run configure_manim_provider.py.")
    if not has_tts_key():
        print("action: For narrated Manim videos, apply for or refresh Aliyun DashScope CosyVoice access or Volcengine speech synthesis access, then run configure_manim_provider.py --purpose tts; otherwise run with --no-tts.")

    return 1 if failed_required else 0


if __name__ == "__main__":
    raise SystemExit(main())
