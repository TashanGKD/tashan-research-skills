#!/usr/bin/env python
"""Check the local manim-agent runtime without printing secrets.

Cross-platform behavior:
- Resolve repo from --repo, then MANIM_AGENT_HOME, then common local clone paths.
- Report missing dependencies clearly; never print secret values.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

DASHSCOPE_API_KEY_HELP_URL = "https://help.aliyun.com/zh/model-studio/get-api-key"


def _candidate_default_repo() -> Path:
    cwd_repo = Path.cwd() / "manim-agent"
    if cwd_repo.exists():
        return cwd_repo

    home = Path.home()
    home_repo = home / "manim-agent"
    if home_repo.exists():
        return home_repo

    workspace_repo = home / "workspace" / "manim-agent"
    if workspace_repo.exists():
        return workspace_repo

    return home_repo


def _resolve_repo(cli_repo: str | None) -> Path:
    if cli_repo:
        repo = Path(cli_repo).expanduser()
    elif os.getenv("MANIM_AGENT_HOME"):
        repo = Path(os.environ["MANIM_AGENT_HOME"]).expanduser()
    else:
        repo = _candidate_default_repo()
    return repo.resolve() if repo.exists() else repo


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Check manim-agent local runtime.")
    parser.add_argument(
        "--repo",
        default=None,
        help=(
            "Path to the local gqy20/manim-agent repository. Defaults to "
            "$MANIM_AGENT_HOME, then ./manim-agent, then ~/manim-agent, then "
            "~/workspace/manim-agent."
        ),
    )
    args = parser.parse_args()

    repo = _resolve_repo(args.repo)
    checks: list[tuple[str, bool, str]] = []

    checks.append(("repo", repo.exists(), str(repo)))
    checks.append(("pyproject", (repo / "pyproject.toml").exists(), str(repo / "pyproject.toml")))
    checks.append(("cli_entry", (repo / "src" / "manim_agent" / "__main__.py").exists(), "src/manim_agent/__main__.py"))
    checks.append(("production_plugin", (repo / "plugins" / "manim-production").exists(), "plugins/manim-production"))

    py_ok = sys.version_info >= (3, 12)
    checks.append(("python>=3.12", py_ok, sys.version.split()[0]))

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
        "manim_agent",
    ]:
        ok, detail = check_python_package(package)
        checks.append((f"py:{package}", ok, detail))

    for env_name in [
        "DASHSCOPE_API_KEY",
        "DATABASE_URL",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
        "MANIM_AGENT_HOME",
    ]:
        checks.append((env_name, bool(os.getenv(env_name)), "set" if os.getenv(env_name) else "not set"))

    max_name = max(len(name) for name, _, _ in checks)
    failed_required = False
    required = {
        "python>=3.12",
        "uv",
        "ffmpeg",
        "py:claude_agent_sdk",
        "py:httpx",
        "py:manim_agent",
    }
    soft_required = {
        "repo",
        "pyproject",
        "cli_entry",
        "production_plugin",
        "manim",
        "py:manim",
    }

    for name, ok, detail in checks:
        marker = yes_no(ok)
        if name in soft_required and not ok:
            marker = "missing*"
        print(f"{name.ljust(max_name)}  {marker:8}  {detail}")
        if name in required and not ok:
            failed_required = True

    print()
    if not (repo / "pyproject.toml").exists():
        print(
            f"note: manim-agent repo not found at {repo}. "
            "Clone it with: git clone https://github.com/gqy20/manim-agent.git "
            f"\"{repo}\""
        )
        print("note: override the repo path with MANIM_AGENT_HOME=/path/to/manim-agent or --repo /path/to/manim-agent.")
    if not shutil.which("uv"):
        print("note: 'uv' is required. Install from https://docs.astral.sh/uv/.")
    if not shutil.which("manim") and importlib.util.find_spec("manim") is None:
        print("note: 'manim' CLI not found. Install system deps (cairo/pango/ffmpeg), then install manim.")
    if importlib.util.find_spec("claude_agent_sdk") is None:
        print("note: 'claude_agent_sdk' is not importable; install claude-agent-sdk in the repo environment.")
    if importlib.util.find_spec("manim_agent") is None:
        print("note: 'manim_agent' is not importable; run `uv pip install -e .` from the repo.")
    if os.getenv("DASHSCOPE_API_KEY"):
        print("note: DASHSCOPE_API_KEY can drive DashScope CosyVoice TTS when narration is enabled.")
    else:
        print(
            "note: DASHSCOPE_API_KEY is needed for Aliyun DashScope CosyVoice TTS. "
            f"Apply at {DASHSCOPE_API_KEY_HELP_URL}"
        )
    if not os.getenv("DATABASE_URL"):
        print("note: DATABASE_URL is needed for Web/backend persistence, not for direct CLI no-persistence runs.")
    if not (
        os.getenv("DASHSCOPE_API_KEY")
        or os.getenv("ANTHROPIC_AUTH_TOKEN")
        or os.getenv("ANTHROPIC_API_KEY")
    ):
        print("note: Manim Agent needs a DashScope/Bailian API key for normal model runs.")
    if not sys.platform.startswith("win"):
        print("note: PowerShell examples in this skill can be translated to bash; `uv run python -m manim_agent ...` is the same.")

    return 1 if failed_required else 0


if __name__ == "__main__":
    raise SystemExit(main())
