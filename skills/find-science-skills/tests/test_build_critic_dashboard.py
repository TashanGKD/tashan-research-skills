import json
import pathlib
import re
import subprocess
import sys


SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "build_critic_dashboard.py"


def write_inputs(tmp_path, *, missing_score=False):
    catalog = {
        "schema": "science_skill_catalog_v1",
        "skills": [
            {
                "id": "alpha",
                "name": "Alpha",
                "summary": "Alpha summary",
                "domain": "生命科学",
                "subdomain": "组学",
                "stage": "分析验证",
                "function": "分析推断",
                "task": "差异分析",
                "quality_score": 88,
                "readiness": "trusted",
                "source_repository": "org/repo",
                "source_path": "skills/alpha/SKILL.md",
                "review_status": "manual_confirmed",
            },
            {
                "id": "beta",
                "name": "Beta",
                "summary": "Beta summary",
                "domain": "通用科研",
                "subdomain": "通用科研",
                "stage": "表达发表",
                "function": "科研写作",
                "task": "摘要改写",
                "quality_score": 55,
                "readiness": "provisional",
                "source_repository": "org/repo",
                "source_path": "skills/beta/SKILL.md",
                "review_status": "metadata_reviewed",
            },
        ],
    }
    scores = {
        "schema": "science_skill_critic_scores_v2",
        "scores": [
            {
                "id": "alpha",
                "critic_evidence_level": "full_source",
                "model_source_review_score": 92,
                "static_validation_status": "pass",
                "evaluation_status": "complete",
                "install_recommendation": "recommend_install",
                "instruction_quality": 24,
                "task_actionability": 24,
                "safety": 20,
                "trigger_clarity": 12,
                "package_maintainability": 12,
                "strengths": ["Clear workflow"],
                "risks": [],
                "evidence": ["Source-backed evidence"],
            }
        ],
    }
    if not missing_score:
        scores["scores"].append(
            {
                "id": "beta",
                "critic_evidence_level": "metadata_only",
                "model_source_review_score": None,
                "static_validation_status": "pass",
                "evaluation_status": "unverified",
                "install_recommendation": "unverified",
                "strengths": [],
                "risks": ["Source unavailable"],
                "evidence": [],
            }
        )
    catalog_path = tmp_path / "catalog.json"
    scores_path = tmp_path / "scores.json"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    scores_path.write_text(json.dumps(scores), encoding="utf-8")
    return catalog_path, scores_path


def run_builder(catalog, scores, output):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--catalog",
            str(catalog),
            "--scores",
            str(scores),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )


def test_dashboard_build_is_deterministic_and_embeds_joined_records(tmp_path):
    catalog, scores = write_inputs(tmp_path)
    first = tmp_path / "first.html"
    second = tmp_path / "second.html"

    result = run_builder(catalog, scores, first)
    assert result.returncode == 0, result.stderr
    result = run_builder(catalog, scores, second)
    assert result.returncode == 0, result.stderr

    assert first.read_bytes() == second.read_bytes()
    html = first.read_text(encoding="utf-8")
    assert "科研技能评分" in html
    assert '"id":"alpha"' in html
    assert '"domain":"生命科学"' in html
    assert '"evaluation_status":"complete"' in html
    assert '"id":"beta"' in html
    assert "https://" not in html
    assert "Content-Security-Policy" in html
    assert "default-src 'none'" in html

    scripts = re.findall(r"<script(?:[^>]*)>([\s\S]*?)</script>", html)
    javascript = tmp_path / "dashboard.js"
    javascript.write_text(scripts[-1], encoding="utf-8")
    syntax = subprocess.run(
        ["node", "--check", str(javascript)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert syntax.returncode == 0, syntax.stderr


def test_dashboard_build_rejects_catalog_score_mismatch(tmp_path):
    catalog, scores = write_inputs(tmp_path, missing_score=True)
    result = run_builder(catalog, scores, tmp_path / "dashboard.html")
    assert result.returncode != 0
    assert "catalog/score ID mismatch" in result.stderr
