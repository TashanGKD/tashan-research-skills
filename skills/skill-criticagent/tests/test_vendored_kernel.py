import hashlib
import json
import os
import pathlib
import subprocess
import sys
import textwrap


SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
VENDOR_ROOT = SKILL_DIR / "vendor" / "mcp_criticagent"


def _utf8_subprocess_environment():
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    return environment


def test_vendored_kernel_matches_manifest():
    manifest = json.loads((VENDOR_ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "vendored_mcp_criticagent_kernel_v1"
    for relative, expected in manifest["files"].items():
        path = VENDOR_ROOT / relative
        assert path.is_file(), relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, relative


def test_vendored_validator_rejects_embedded_secret(tmp_path):
    sys.path.insert(0, str(VENDOR_ROOT))
    try:
        from src.core.skill_validator import validate_skill_dir

        skill = tmp_path / "unsafe-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            "---\nname: unsafe-skill\ndescription: Unsafe test skill.\n---\n",
            encoding="utf-8",
        )
        secret = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
        (skill / "config.py").write_text(
            f'api_key = "{secret}"\n',
            encoding="utf-8",
        )
        result = validate_skill_dir(skill, strict=True).to_dict()
    finally:
        sys.path.remove(str(VENDOR_ROOT))

    assert result["valid"] is False
    assert any(item["severity"] == "high" for item in result["summary"]["security_findings"])


def test_vendored_validator_accepts_multiline_frontmatter(tmp_path):
    sys.path.insert(0, str(VENDOR_ROOT))
    try:
        from src.core.skill_trigger import load_catalog_entry
        from src.core.skill_validator import validate_skill_dir

        skill = tmp_path / "multiline-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            "---\n"
            "name: multiline-skill\n"
            "description: |\n"
            "  First line.\n"
            "  Second line.\n"
            "---\n",
            encoding="utf-8",
        )
        result = validate_skill_dir(skill, strict=True).to_dict()
        catalog_entry = load_catalog_entry(skill)
    finally:
        sys.path.remove(str(VENDOR_ROOT))

    assert result["valid"] is True
    assert catalog_entry.description == "First line.\nSecond line."


def test_grading_scripts_find_bundled_kernel_without_environment():
    environment = _utf8_subprocess_environment()
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


def test_graders_can_print_compact_summary_and_archive_full_result(tmp_path):
    skill_dir = tmp_path / "compact-skill"
    evals_dir = skill_dir / "evals"
    evals_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: compact-skill\ndescription: Compact grader output test.\n---\n",
        encoding="utf-8",
    )
    prompt = "Return compact evidence."
    (evals_dir / "evals.json").write_text(
        json.dumps(
            {
                "evals": [
                    {
                        "id": "compact",
                        "prompt": prompt,
                        "assertions": [{"type": "contains", "value": "verified"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (evals_dir / "trigger_queries.json").write_text(
        json.dumps(
            {
                "queries": [
                    {"query": "Use compact skill.", "should_trigger": True},
                    {"query": "Do something else.", "should_trigger": False},
                ]
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "runs.json"
    manifest.write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "prompt": prompt,
                        "with_skill": {"output": "verified"},
                        "without_skill": {"output": "baseline"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    decisions = tmp_path / "decisions.json"
    decisions.write_text(
        json.dumps(
            [
                {
                    "query": "Use compact skill.",
                    "should_trigger": True,
                    "decisions": ["compact-skill"],
                },
                {
                    "query": "Do something else.",
                    "should_trigger": False,
                    "decisions": ["none"],
                },
            ]
        ),
        encoding="utf-8",
    )

    behavior_archive = tmp_path / "behavior-full.json"
    behavior = subprocess.run(
        [
            sys.executable,
            str(SKILL_DIR / "scripts" / "grade_runs.py"),
            str(skill_dir),
            str(manifest),
            "--output",
            str(behavior_archive),
            "--summary-only",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_utf8_subprocess_environment(),
        timeout=30,
    )
    assert behavior.returncode == 0, behavior.stderr
    behavior_payload = json.loads(behavior.stdout)
    assert "runs" not in behavior_payload
    assert behavior_payload["with_skill"] == {"passed": 1, "total": 1}
    assert behavior_payload["without_skill"] == {"passed": 0, "total": 1}
    assert behavior_payload["assertion_audit"] == {
        "non_discriminating_count": 0,
        "always_failing_count": 0,
    }
    assert "runs" in json.loads(behavior_archive.read_text(encoding="utf-8"))

    trigger_archive = tmp_path / "trigger-full.json"
    trigger = subprocess.run(
        [
            sys.executable,
            str(SKILL_DIR / "scripts" / "grade_triggers.py"),
            str(skill_dir),
            str(decisions),
            "--output",
            str(trigger_archive),
            "--summary-only",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_utf8_subprocess_environment(),
        timeout=30,
    )
    assert trigger.returncode == 0, trigger.stderr
    trigger_payload = json.loads(trigger.stdout)
    assert trigger_payload == {"passed": 2, "total": 2, "accuracy": 1.0}
    assert "results" in json.loads(trigger_archive.read_text(encoding="utf-8"))


def test_trigger_grader_report_only_preserves_quality_red_without_host_failure(tmp_path):
    skill_dir = tmp_path / "weak-trigger"
    evals_dir = skill_dir / "evals"
    evals_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: weak-trigger\ndescription: Trigger report-only test.\n---\n",
        encoding="utf-8",
    )
    (evals_dir / "trigger_queries.json").write_text(
        json.dumps(
            {"queries": [{"query": "Use it.", "should_trigger": True}]}
        ),
        encoding="utf-8",
    )
    decisions = tmp_path / "decisions.json"
    decisions.write_text(
        json.dumps(
            [
                {
                    "query": "Use it.",
                    "should_trigger": True,
                    "decisions": ["none"],
                }
            ]
        ),
        encoding="utf-8",
    )

    strict = subprocess.run(
        [
            sys.executable,
            str(SKILL_DIR / "scripts" / "grade_triggers.py"),
            str(skill_dir),
            str(decisions),
            "--summary-only",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_utf8_subprocess_environment(),
        timeout=30,
    )
    report_only = subprocess.run(
        [
            sys.executable,
            str(SKILL_DIR / "scripts" / "grade_triggers.py"),
            str(skill_dir),
            str(decisions),
            "--summary-only",
            "--report-only",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_utf8_subprocess_environment(),
        timeout=30,
    )

    assert strict.returncode == 1
    assert report_only.returncode == 0, report_only.stderr
    assert json.loads(report_only.stdout) == {
        "passed": 0,
        "total": 1,
        "accuracy": 0.0,
    }
    assert "VERDICT HINT" in report_only.stderr


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
        env=_utf8_subprocess_environment(),
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    runs = {(run["case_id"], run["mode"]): run for run in result["runs"]}
    assert runs[("real_execution", "with_skill")]["passed"] is True
    assert runs[("real_execution", "without_skill")]["passed"] is False
