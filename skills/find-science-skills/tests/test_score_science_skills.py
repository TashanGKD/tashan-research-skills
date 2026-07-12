import importlib.util
import hashlib
import json
import pathlib


SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_DIR / "scripts" / "score_science_skills.py"
CATALOG_PATH = SKILL_DIR / "data" / "science_skill_catalog.json"
SCORECARD_PATH = SKILL_DIR / "data" / "science_skill_critic_scores.json"


def load_module():
    spec = importlib.util.spec_from_file_location("score_science_skills", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_resolve_source_uses_repository_and_source_path(tmp_path):
    module = load_module()
    source = tmp_path / "owner__repo" / "skills" / "demo" / "SKILL.md"
    source.parent.mkdir(parents=True)
    source.write_text("---\nname: demo\ndescription: Demo\n---\n", encoding="utf-8")
    assert module.resolve_source(
        {
            "source_repository": "owner/repo",
            "source_path": "skills/demo/SKILL.md",
        },
        tmp_path,
    ) == source


def test_metadata_review_is_always_low_confidence():
    module = load_module()
    review = {
        "instruction_quality": 20,
        "task_actionability": 20,
        "safety": 18,
        "trigger_clarity": 12,
        "package_maintainability": 10,
        "overall": 80,
        "verdict": "recommend",
        "confidence": "high",
        "skill_type": "guidance",
        "strengths": ["clear"],
        "risks": [],
        "evidence": ["metadata"],
    }
    result = module.normalize_review(review, evidence_level="metadata_only")
    assert result["critic_content_score"] == 80
    assert result["critic_confidence"] == "low"


def test_low_score_is_always_rejected_even_if_model_verdict_is_inconsistent():
    module = load_module()
    result = module.normalize_review(
        {
            "instruction_quality": 2,
            "task_actionability": 1,
            "safety": 10,
            "trigger_clarity": 1,
            "package_maintainability": 3,
            "overall": 17,
            "verdict": "fix_first",
            "confidence": "high",
            "skill_type": "guidance",
        },
        evidence_level="full_source",
    )
    assert result["critic_content_score"] == 17
    assert result["critic_verdict"] == "reject"


def test_normalize_review_clamps_dimensions_and_recomputes_total():
    module = load_module()
    result = module.normalize_review(
        {
            "instruction_quality": 99,
            "task_actionability": -2,
            "safety": 18,
            "trigger_clarity": 12,
            "package_maintainability": 10,
            "overall": 999,
            "verdict": "recommend",
            "confidence": "high",
            "skill_type": "hybrid",
        },
        evidence_level="full_source",
    )
    assert result["instruction_quality"] == 25
    assert result["task_actionability"] == 0
    assert result["critic_content_score"] == 65


def test_directory_manifest_is_relative_and_deterministic(tmp_path):
    module = load_module()
    skill = tmp_path / "demo" / "SKILL.md"
    skill.parent.mkdir()
    (skill.parent / "references").mkdir()
    skill.write_text("demo", encoding="utf-8")
    (skill.parent / "references" / "guide.md").write_text("guide", encoding="utf-8")
    assert module.directory_manifest(skill) == ["SKILL.md", "references/guide.md"]


def test_bundled_critic_kernel_is_the_default():
    module = load_module()
    critic_root = module.resolve_critic_root(None)
    assert critic_root == module.BUNDLED_CRITIC_ROOT
    assert (critic_root / "src" / "core" / "skill_validator.py").is_file()
    assert module.load_validator(critic_root) is not None


def test_generated_scorecard_covers_the_catalog_without_secret_material():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    scorecard = json.loads(SCORECARD_PATH.read_text(encoding="utf-8"))
    catalog_ids = {skill["id"] for skill in catalog["skills"]}
    score_ids = [record["id"] for record in scorecard["scores"]]
    assert scorecard["schema"] == "science_skill_critic_scores_v2"
    assert scorecard["model"] == "deepseek-v4-flash-260425"
    assert scorecard["score_count"] == len(catalog_ids) == 1391
    assert len(score_ids) == len(set(score_ids))
    assert set(score_ids) == catalog_ids
    assert scorecard["failures"] == []
    assert scorecard["catalog_sha256"] == hashlib.sha256(
        CATALOG_PATH.read_bytes()
    ).hexdigest()
    assert all(
        record["model_source_review_score"] is None
        or 0 <= record["model_source_review_score"] <= 100
        for record in scorecard["scores"]
    )
    assert all(
        record["critic_confidence"] == "low"
        for record in scorecard["scores"]
        if record["critic_evidence_level"] == "metadata_only"
    )
    assert all(
        record["model_source_review_score"] is None
        and record["evaluation_status"] == "unverified"
        for record in scorecard["scores"]
        if record["critic_evidence_level"] == "metadata_only"
    )
    assert all(
        record["install_recommendation"] != "recommend_install"
        or (
            record["static_validation_status"] == "pass"
            and record["behavior_evaluation"]["status"] == "pass"
            and record["trigger_evaluation"]["status"] == "pass"
        )
        for record in scorecard["scores"]
    )
    raw = SCORECARD_PATH.read_text(encoding="utf-8")
    assert "ARK_API_KEY" not in raw
    assert "Authorization: Bearer" not in raw
