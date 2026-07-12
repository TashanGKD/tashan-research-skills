import hashlib
import json
import os
import pathlib
import subprocess
import sys


SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
VENDOR_ROOT = SKILL_DIR / "vendor" / "mcp_criticagent"


def test_vendored_kernel_matches_manifest():
    manifest = json.loads((VENDOR_ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "vendored_mcp_criticagent_kernel_v1"
    for relative, expected in manifest["files"].items():
        path = VENDOR_ROOT / relative
        assert path.is_file(), relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, relative


def test_grading_scripts_find_bundled_kernel_without_environment():
    environment = os.environ.copy()
    environment.pop("MCP_CRITICAGENT_ROOT", None)
    for script_name in ("grade_runs.py", "grade_triggers.py"):
        completed = subprocess.run(
            [sys.executable, str(SKILL_DIR / "scripts" / script_name), "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
            timeout=30,
        )
        assert completed.returncode == 0, completed.stderr
        assert "evaluation kernel not found" not in completed.stderr
