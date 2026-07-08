# -*- coding: utf-8 -*-
"""Regression tests for the curated retrieval benchmark."""
import json
import pathlib
import sys

SKILL = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))

import bench_retrieval as br  # noqa: E402


def load_bench():
    return json.loads((SKILL / "data" / "retrieval_bench.json").read_text(encoding="utf-8"))


def load_holdout():
    return json.loads((SKILL / "data" / "retrieval_holdout.json").read_text(encoding="utf-8"))


def load_gaps():
    return json.loads((SKILL / "data" / "retrieval_gaps.json").read_text(encoding="utf-8"))


def test_bench_file_is_well_formed_and_representative():
    bench = load_bench()
    br.validate_bench(bench)

    cases = bench["cases"]
    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids))
    assert {case["target"] for case in cases} == {"find", "wiki"}
    assert {case["level"] for case in cases} == {"basic", "medium", "complex"}
    assert {"typical", "complex", "confusing"} <= {case["difficulty"] for case in cases}
    assert len(cases) >= 100
    assert sum(1 for case in cases if case["target"] == "find") >= 65
    assert sum(1 for case in cases if case["target"] == "wiki") >= 35
    assert sum(1 for case in cases if case["level"] == "basic") >= 25
    assert sum(1 for case in cases if case["level"] == "medium") >= 35
    assert sum(1 for case in cases if case["level"] == "complex") >= 35
    assert sum(1 for case in cases if case["difficulty"] == "confusing") >= 25

    thresholds = bench["thresholds"]
    assert bench["minimum_cases"]["difficulties"]["confusing"] >= 25

    for bucket in (
        "overall",
        "find",
        "wiki",
        "level_basic",
        "level_medium",
        "level_complex",
        "difficulty_confusing",
    ):
        assert bucket in thresholds
        assert "top1" in thresholds[bucket]
        assert "top3" in thresholds[bucket]


def test_bench_includes_natural_language_skill_finder_queries():
    bench = load_bench()
    ids = {case["id"] for case in bench["cases"]}

    assert {
        "find_pubmed_natural_language",
        "find_scvi_batch_integration_natural_language",
        "find_opentrons_protocol_natural_language",
        "wiki_pubmed_natural_language",
        "wiki_opentrons_protocol_natural_language",
        "wiki_prisma_flow_diagram_natural_language",
    } <= ids


def test_bench_includes_vercel_style_science_skill_queries():
    bench = load_bench()
    ids = {case["id"] for case in bench["cases"]}

    assert {
        "find_jupyter_reproducible_notebook_natural_language",
        "find_lab_meeting_slide_deck_natural_language",
        "find_inplasy_protocol_registration_natural_language",
        "find_revman_forest_plot_natural_language",
        "wiki_jupyter_reproducible_notebook_natural_language",
        "wiki_lab_meeting_slide_deck_natural_language",
        "wiki_inplasy_protocol_registration_natural_language",
        "wiki_revman_forest_plot_natural_language",
    } <= ids


def test_bench_includes_real_wet_lab_assay_analysis_queries():
    bench = load_bench()
    ids = {case["id"] for case in bench["cases"]}

    assert {
        "find_plate_reader_dose_response_ic50",
        "wiki_plate_reader_dose_response_ic50",
        "find_mtt_cell_viability_ic50",
        "wiki_mtt_cell_viability_ic50",
        "find_immunofluorescence_colocalization",
        "wiki_immunofluorescence_colocalization",
    } <= ids


def test_bench_hard_cases_include_rationale_and_false_positive_risks():
    bench = load_bench()
    cases = {case["id"]: case for case in bench["cases"]}
    audited_ids = {
        "find_instrumental_variables_2sls",
        "wiki_instrumental_variables_2sls",
        "find_pdb_retrieve_not_predict_natural_language",
        "wiki_pdb_retrieve_not_predict_natural_language",
        "wiki_bulk_rnaseq_deseq2_volcano_natural_language",
    }

    assert audited_ids <= set(cases)
    for case_id in audited_ids:
        case = cases[case_id]
        assert case["difficulty"] == "confusing"
        assert len(case.get("rationale", "")) >= 80
        assert len(case.get("false_positive_risks") or []) >= 2


def test_bench_rejects_duplicate_case_ids():
    bench = {
        "schema": "find_science_skills_retrieval_bench_v1",
        "thresholds": {"overall": {"top1": 0.5}},
        "cases": [
            {
                "id": "duplicate",
                "target": "find",
                "level": "basic",
                "difficulty": "typical",
                "query": "DFT",
                "expected_top1_any": ["quantum-espresso"],
                "expected_top3_any": ["quantum-espresso"],
            },
            {
                "id": "duplicate",
                "target": "wiki",
                "level": "basic",
                "difficulty": "typical",
                "query": "DFT",
                "expected_top1_any": ["quantum-espresso"],
                "expected_top3_any": ["quantum-espresso"],
            },
        ],
    }

    try:
        br.validate_bench(bench)
    except ValueError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("duplicate case ids should be rejected")


def test_release_bench_rejects_missing_skill_placeholders():
    bench = {
        "schema": "find_science_skills_retrieval_bench_v1",
        "thresholds": {"overall": {"top1": 0.5}},
        "minimum_cases": {"levels": {"complex": 1}, "difficulties": {"confusing": 1}},
        "cases": [
            {
                "id": "fake_missing_skill_release_case",
                "target": "find",
                "level": "complex",
                "difficulty": "confusing",
                "query": "object detection computer vision YOLO",
                "expected_top1_any": ["__missing_object_detection_yolo_skill__"],
                "expected_top3_any": ["__missing_object_detection_yolo_skill__"],
            }
        ],
    }

    try:
        br.validate_bench(bench)
    except ValueError as exc:
        assert "missing-skill placeholder" in str(exc)
    else:
        raise AssertionError("release bench should reject missing-skill placeholders")


def test_bench_rejects_empty_hard_case_explanation_fields():
    bench = {
        "schema": "find_science_skills_retrieval_bench_v1",
        "thresholds": {"overall": {"top1": 0.5}},
        "minimum_cases": {"levels": {"complex": 1}, "difficulties": {"confusing": 1}},
        "cases": [
            {
                "id": "bad_explanation_case",
                "target": "find",
                "level": "complex",
                "difficulty": "confusing",
                "query": "retrieve PDB not predict AlphaFold",
                "expected_top1_any": ["pdb-database"],
                "expected_top3_any": ["pdb-database"],
                "rationale": "",
                "false_positive_risks": [],
            }
        ],
    }

    try:
        br.validate_bench(bench)
    except ValueError as exc:
        assert "rationale" in str(exc)
    else:
        raise AssertionError("empty hard-case explanation fields should be rejected")


def test_retrieval_bench_meets_release_thresholds():
    report = br.run_bench(load_bench())
    assert "thresholds" in report
    assert "minimum_cases" in report
    assert report["threshold_failures"] == []
    assert report["case_failures"] == []
    assert report["summary"]["overall"]["top1_rate"] >= 0.82
    assert report["summary"]["overall"]["top3_rate"] >= 0.94
    assert report["summary"]["level_basic"]["top1_rate"] >= 0.9
    assert report["summary"]["level_medium"]["top1_rate"] >= 0.84
    assert report["summary"]["level_complex"]["top1_rate"] >= 0.75


def test_holdout_file_tracks_unresolved_or_harder_queries_without_release_gate():
    holdout = load_holdout()
    br.validate_holdout(holdout)

    cases = holdout["cases"]
    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids))
    assert len(cases) >= 12
    assert {case["target"] for case in cases} == {"find", "wiki"}
    assert all(case.get("reason") for case in cases)
    assert all(case.get("expected_top3_any") for case in cases)

    report = br.run_holdout(holdout)
    assert report["schema"] == "find_science_skills_retrieval_holdout_report_v1"
    assert report["summary"]["overall"]["count"] == len(cases)
    assert "threshold_failures" not in report
    assert "case_failures" in report


def test_holdout_report_can_record_failures_without_failing_release_thresholds():
    holdout = {
        "schema": "find_science_skills_retrieval_holdout_v1",
        "version": "test",
        "cases": [
            {
                "id": "synthetic_unmatched_case",
                "target": "find",
                "level": "complex",
                "difficulty": "confusing",
                "query": "synthetic impossible query",
                "reason": "Proves holdout reports misses without release thresholds.",
                "expected_top3_any": ["definitely-not-a-real-skill-id"],
            }
        ],
    }

    report = br.run_holdout(holdout)
    assert report["summary"]["overall"]["top3"] == 0
    assert report["case_failures"][0]["id"] == "synthetic_unmatched_case"
    assert "threshold_failures" not in report


def test_holdout_can_match_high_confidence_missing_skill_gap():
    holdout = {
        "schema": "find_science_skills_retrieval_holdout_v1",
        "version": "test",
        "cases": [
            {
                "id": "synthetic_missing_object_detection",
                "target": "find",
                "level": "medium",
                "difficulty": "confusing",
                "query": "object detection computer vision YOLO",
                "reason": "Proves explicit registry-gap results can satisfy missing-skill holdouts.",
                "expected_top3_any": ["__missing_object_detection_yolo_skill__"],
            }
        ],
    }

    report = br.run_holdout(holdout)

    assert report["case_failures"] == []
    assert report["cases"][0]["top5"][0] == "__missing_object_detection_yolo_skill__"


def test_holdout_report_separates_real_skill_hits_from_registry_gap_hits(capsys):
    holdout = load_holdout()
    report = br.run_holdout(holdout)
    expected_gap_case_ids = {
        "holdout_find_biomedical_ner",
        "holdout_wiki_biomedical_ner",
        "holdout_find_object_detection_yolo",
        "holdout_find_neuroimaging_nifti",
        "holdout_find_gwas_finemapping_coloc",
        "holdout_wiki_object_detection_yolo",
        "holdout_wiki_gwas_finemapping_coloc",
        "holdout_wiki_neuroimaging_nifti",
        "holdout_find_microbiome_qiime2_abundance",
        "holdout_wiki_microbiome_qiime2_abundance",
        "holdout_find_elisa_standard_curve",
        "holdout_wiki_elisa_standard_curve",
        "holdout_find_western_blot_densitometry",
        "holdout_wiki_western_blot_densitometry",
        "holdout_find_qpcr_ddct_analysis",
        "holdout_wiki_qpcr_ddct_analysis",
        "holdout_find_immunofluorescence_colocalization",
        "holdout_wiki_immunofluorescence_colocalization",
        "holdout_find_luciferase_reporter_assay",
        "holdout_wiki_luciferase_reporter_assay",
        "holdout_find_cytof_mass_cytometry",
        "holdout_wiki_cytof_mass_cytometry",
        "holdout_find_chipseq_peak_calling",
        "holdout_wiki_chipseq_peak_calling",
    }

    resolution = report["resolution_summary"]["overall"]
    expected_resolution = report["expected_resolution_summary"]["overall"]
    assert resolution["count"] == len(holdout["cases"])
    assert resolution["top3_real_skill"] == 8
    assert resolution["top3_registry_gap"] == len(expected_gap_case_ids)
    assert resolution["top1_real_skill"] == 8
    assert resolution["top1_registry_gap"] == len(expected_gap_case_ids)
    assert expected_resolution["expected_real_skill"] == 8
    assert expected_resolution["expected_registry_gap"] == len(expected_gap_case_ids)

    gap_rows = [row for row in report["cases"] if row["top1_match_type"] == "registry_gap"]
    assert {row["id"] for row in gap_rows} == expected_gap_case_ids

    br.print_markdown(report)
    out = capsys.readouterr().out
    assert "Expected Target Split" in out
    assert "Registry Gap Matches" in out
    assert "holdout_find_biomedical_ner" in out
    assert "__missing_biomedical_ner_skill__" in out
    assert "holdout_wiki_gwas_finemapping_coloc" in out
    assert "__missing_gwas_finemapping_coloc_skill__" in out
    assert "holdout_wiki_microbiome_qiime2_abundance" in out
    assert "__missing_microbiome_qiime2_abundance_skill__" in out
    assert "holdout_wiki_elisa_standard_curve" in out
    assert "__missing_elisa_standard_curve_skill__" in out
    assert "holdout_wiki_western_blot_densitometry" in out
    assert "__missing_western_blot_densitometry_skill__" in out
    assert "holdout_wiki_qpcr_ddct_analysis" in out
    assert "__missing_qpcr_ddct_analysis_skill__" in out
    assert "holdout_wiki_immunofluorescence_colocalization" in out
    assert "__missing_immunofluorescence_colocalization_skill__" in out
    assert "holdout_wiki_luciferase_reporter_assay" in out
    assert "__missing_luciferase_reporter_assay_skill__" in out
    assert "holdout_wiki_cytof_mass_cytometry" in out
    assert "__missing_cytof_mass_cytometry_skill__" in out
    assert "holdout_wiki_chipseq_peak_calling" in out
    assert "__missing_chipseq_peak_calling_skill__" in out


def test_markdown_printer_handles_non_gating_holdout_report(capsys):
    holdout = {
        "schema": "find_science_skills_retrieval_holdout_v1",
        "version": "test",
        "cases": [
            {
                "id": "synthetic_unmatched_case",
                "target": "find",
                "level": "complex",
                "difficulty": "confusing",
                "query": "synthetic impossible query",
                "reason": "Proves holdout reports misses without release thresholds.",
                "expected_top3_any": ["definitely-not-a-real-skill-id"],
            }
        ],
    }

    br.print_markdown(br.run_holdout(holdout))
    out = capsys.readouterr().out
    assert "Case Failures" in out
    assert "synthetic_unmatched_case" in out


def test_missing_skill_placeholders_are_tracked_as_registry_gaps():
    holdout = load_holdout()
    gaps = load_gaps()
    br.validate_gaps(gaps)
    br.validate_gap_holdout_links(gaps, holdout)

    expected_missing = set()
    for case in holdout["cases"]:
        for skill_id in case.get("expected_top3_any", []):
            if skill_id.startswith("__missing_") and skill_id.endswith("__"):
                expected_missing.add(skill_id)

    gap_ids = {gap["id"] for gap in gaps["gaps"]}
    assert expected_missing
    assert expected_missing <= gap_ids
    assert all(gap.get("status") in {"missing_skill", "ranking_gap", "data_gap"} for gap in gaps["gaps"])

    cases_by_id = {case["id"]: case for case in holdout["cases"]}
    for gap in gaps["gaps"]:
        if gap.get("status") != "missing_skill":
            continue
        tracked_targets = {
            cases_by_id[case_id]["target"]
            for case_id in gap.get("source_holdout_ids", [])
        }
        assert tracked_targets == {"find", "wiki"}, gap["id"]


def test_gap_holdout_links_reject_stale_or_mismatched_backlog_items():
    holdout = {
        "schema": "find_science_skills_retrieval_holdout_v1",
        "version": "test",
        "cases": [
            {
                "id": "holdout_known",
                "target": "find",
                "level": "complex",
                "difficulty": "confusing",
                "query": "object detection computer vision YOLO",
                "reason": "Synthetic linked case.",
                "expected_top3_any": ["__missing_object_detection_yolo_skill__"],
            }
        ],
    }
    base_gap = {
        "status": "missing_skill",
        "title": "General object detection / YOLO",
        "query_examples": ["object detection computer vision YOLO"],
    }

    stale = {
        "schema": "find_science_skills_retrieval_gaps_v1",
        "version": "test",
        "gaps": [
            {
                **base_gap,
                "id": "__missing_object_detection_yolo_skill__",
                "source_holdout_ids": ["holdout_removed"],
            }
        ],
    }
    mismatched = {
        "schema": "find_science_skills_retrieval_gaps_v1",
        "version": "test",
        "gaps": [
            {
                **base_gap,
                "id": "__missing_neuroimaging_nifti_skill__",
                "source_holdout_ids": ["holdout_known"],
            }
        ],
    }

    for gaps, message in ((stale, "unknown holdout case"), (mismatched, "not expected")):
        try:
            br.validate_gap_holdout_links(gaps, holdout)
        except ValueError as exc:
            assert message in str(exc)
        else:
            raise AssertionError("stale gap/holdout links should be rejected")
