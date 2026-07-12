import hashlib
import json
import os
import pathlib
import subprocess
import sys
import textwrap


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


def test_grade_runs_passes_manifest_tool_calls_and_real_files(tmp_path):
    skill_dir = tmp_path / "demo-skill"
    evals_dir = skill_dir / "evals"
    outputs_dir = tmp_path / "outputs"
    evals_dir.mkdir(parents=True)
    outputs_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        textwrap.dedent(
            """\
            ---
            name: demo-skill
            description: Writes a real report for deterministic evaluation.
            ---
            Read the input and write report.md.
            """
        ),
        encoding="utf-8",
    )
    prompt = "Read input.txt and write report.md."
    (evals_dir / "evals.json").write_text(
        json.dumps(
            {
                "evals": [
                    {
                        "id": "real_execution",
                        "prompt": prompt,
                        "assertions": [{"type": "contains", "value": "done"}],
                        "tool_assertions": [
                            {"type": "tool-called", "name": "read_file"},
                            {"type": "tool-called", "name": "write_file"},
                            {
                                "type": "tool-arg-equals",
                                "name": "write_file",
                                "path": "path",
                                "value": "report.md",
                            },
                        ],
                        "file_assertions": [
                            {"type": "file-exists", "path": "report.md"},
                            {
                                "type": "file-contains",
                                "path": "report.md",
                                "value": "verified evidence",
                            },
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (outputs_dir / "report.md").write_text("verified evidence", encoding="utf-8")
    tool_calls = [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "arguments": json.dumps({"path": "input.txt"}),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "arguments": json.dumps({"path": "report.md"}),
            },
        },
    ]
    manifest = tmp_path / "runs.json"
    manifest.write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "prompt": prompt,
                        "with_skill": {
                            "output": "done",
                            "outputs_dir": str(outputs_dir),
                            "tool_calls": tool_calls,
                        },
                        "without_skill": {"output": "baseline"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(SKILL_DIR / "scripts" / "grade_runs.py"),
            str(skill_dir),
            str(manifest),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    runs = {(run["case_id"], run["mode"]): run for run in result["runs"]}
    assert runs[("real_execution", "with_skill")]["passed"] is True
    assert runs[("real_execution", "without_skill")]["passed"] is False
