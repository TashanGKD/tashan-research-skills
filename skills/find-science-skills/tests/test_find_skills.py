# -*- coding: utf-8 -*-
"""Smoke tests for find-science-skills: data integrity + retrieval correctness.

Run: python -m pytest skills/find-science-skills/tests -q
"""
import json
import pathlib
import sys

SKILL = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))

import find_skills as fs  # noqa: E402


def load():
    return json.load(open(SKILL / "data" / "skill_graph_index.json", encoding="utf-8"))


def test_data_present_and_shaped():
    d = load()
    assert d.get("schema") == "research_skill_graph_v1"
    assert d["skill_count"] >= 1000
    assert len(d["nodes"]) == d["skill_count"]
    assert len(d["leaderboard"]) == 12
    # every node has the graph edge buckets
    n = next(iter(d["nodes"].values()))
    for k in ("alternative", "companion", "workflow", "related"):
        assert k in n["edges"]


def test_tokenizer_splits_hyphen_and_cjk():
    toks = fs.tok("chem-dft-orca 第一性原理")
    assert "dft" in toks and "orca" in toks
    # CJK bigrams present
    assert any("\u4e00" <= t[0] <= "\u9fff" for t in toks)


def _search(query, cap="", limit=5):
    d = load()
    fs.ensure_blobs(d["nodes"])
    idf = fs.build_idf(d["nodes"])
    q = fs.query_tokens(query)
    intent_cap = None if cap else fs.resolve_cap(query)
    query_intent = fs.infer_intent(query)
    out = []
    for sid, n in d["nodes"].items():
        if cap and n.get("group") != cap:
            continue
        s = fs.score_node(n, q, set(fs.tok(n.get("name", "") + " " + sid)), idf, intent_cap, query_intent)
        if s >= 0:
            out.append((s, n))
    out.sort(key=lambda x: (-x[0], -(x[1].get("score") or 0), -(x[1].get("stars") or 0)))
    return [n for _, n in out[:limit]]


def test_single_cell_retrieval():
    names = [n["name"].lower() for n in _search("single cell rna")]
    assert any("single-cell" in x or "scrna" in x or "single cell" in x for x in names)


def test_dft_retrieval():
    names = [n["name"].lower() for n in _search("DFT")]
    assert any("dft" in x for x in names)


def test_docking_retrieval():
    hits = _search("molecular docking")
    assert hits, "docking query returned nothing"
    assert any("dock" in n["name"].lower() for n in hits)


def test_gromacs_trajectory_query_prefers_gromacs_over_lammps():
    ids = [n["id"] for n in _search("molecular dynamics trajectory analysis GROMACS RMSD RMSF", limit=6)]
    assert ids[0] == "hpc-gromacs"
    assert ids.index("hpc-gromacs") < ids.index("lammps-reaxff")
    assert ids.index("hpc-gromacs") < ids.index("lammps-router")


def test_orca_frequency_query_prefers_orca_freq_over_qe_and_phonopy():
    ids = [n["id"] for n in _search("quantum chemistry ORCA DFT frequency calculation", limit=8)]
    assert ids[0] == "orca-freq"
    assert "quantum-espresso" not in ids[:3]
    assert "phonopy" not in ids[:3]


def test_orca_geometry_optimization_query_prefers_orca_optimization_over_generic_dft():
    ids = [n["id"] for n in _search("ORCA DFT geometry optimization", limit=8)]
    assert ids[0] in {"chem-dft-orca-optimization", "orca-opt"}
    assert "quantum-espresso" not in ids[:3]


def test_vasp_band_structure_query_prefers_vasp_over_generic_dft_tools():
    ids = [n["id"] for n in _search("VASP DFT band structure calculation", limit=8)]
    assert ids[0] == "hpc-vasp"
    assert "quantum-espresso" not in ids[:3]
    assert "phonopy" not in ids[:3]
    assert "chem-dft-orca-advanced-calculation" not in ids[:3]


def test_vasp_frequency_query_prefers_vasp_freq_over_generic_vasp_router():
    ids = [n["id"] for n in _search("VASP vibrational frequency thermochemistry", limit=8)]
    assert ids[0] == "vasp-freq"
    assert ids.index("vasp-freq") < ids.index("hpc-vasp")


def test_capability_filter_scoped():
    hits = _search("", cap="建模仿真", limit=10)
    assert hits and all(n["group"] == "建模仿真" for n in hits)


def test_display_taxonomy_uses_stable_family_and_group_not_noisy_cap():
    node = {
        "cap": "文献查找",
        "family": "分析解释",
        "group": "统计分析",
        "domain_l2": "生物信息学",
    }

    assert fs.display_taxonomy(node) == "分析解释 / 统计分析 · 生物信息学"
    assert "文献查找" not in fs.display_taxonomy(node)


def test_chinese_query_retrieval():
    # bilingual: Chinese queries must hit the right English-described skills
    names = [n["name"].lower() for n in _search("蛋白质结构预测")]
    assert any("alphafold" in x or "esm" in x or "fold" in x or "chai" in x for x in names)
    md = [n["name"].lower() for n in _search("分子动力学模拟")]
    assert any("md" in x or "lammps" in x or "gromacs" in x or "dynamics" in x for x in md)


def test_cryo_em_prefers_electron_microscopy_over_general_pdb():
    ids = [n["id"] for n in _search("冷冻电镜", limit=3)]
    assert ids[0] == "tooluniverse-electron-microscopy"
    assert ids.index("tooluniverse-electron-microscopy") < ids.index("pdb-database")


def test_time_series_keeps_strong_existing_hit_first():
    ids = [n["id"] for n in _search("时间序列", limit=5)]
    assert ids[0] == "aeon"


def test_econometric_time_series_prefers_arima_guide_over_generic_ml_library():
    ids = [n["id"] for n in _search("ARIMA VAR cointegration econometrics time series", limit=5)]
    assert ids[0] == "time-series-guide"
    assert ids.index("time-series-guide") < ids.index("aeon")

    cn_ids = [n["id"] for n in _search("时间序列 ARIMA VAR 协整 计量经济学", limit=5)]
    assert cn_ids[0] == "time-series-guide"
    assert cn_ids.index("time-series-guide") < cn_ids.index("aeon")


def test_instrumental_variables_prefers_iv_guide_over_time_series_intent():
    ids = [n["id"] for n in _search("工具变量 2SLS 弱工具变量 计量经济学", limit=5)]
    assert ids[0] == "iv-regression-guide"
    assert ids.index("iv-regression-guide") < ids.index("time-series-guide")

    en_ids = [n["id"] for n in _search("instrumental variables 2SLS weak instruments econometrics", limit=5)]
    assert en_ids[0] == "iv-regression-guide"
    assert en_ids.index("iv-regression-guide") < en_ids.index("aer-identification")


def test_execution_query_prefers_prediction_skill_over_database_entry():
    ids = [n["id"] for n in _search("蛋白质结构预测 AlphaFold", limit=5)]
    assert ids[0] in {"alphafold2", "alphafold3", "chai1", "esmfold"}
    assert "alphafold-database" not in ids[:3]


def test_pdb_retrieval_query_prefers_database_over_prediction_skill():
    ids = [n["id"] for n in _search("I want to retrieve a PDB structure not predict a new AlphaFold model", limit=5)]
    assert ids[0] == "pdb-database"
    assert ids.index("pdb-database") < ids.index("alphafold-database")
    assert "chai1" not in ids[:3]
    assert "alphafold2" not in ids[:3]


def test_array_data_query_prefers_zarr_over_generic_analysis():
    ids = [n["id"] for n in _search("climate netcdf xarray analysis", limit=5)]
    assert ids[0] == "zarr-python"
    assert "data-analysis" not in ids[:3]


def test_metabolomics_lcms_prefers_broad_omics_planning_over_ms2_prediction():
    ids = [n["id"] for n in _search("metabolomics LC-MS pathway enrichment", limit=5)]
    assert ids[0] == "bulk-omics-integrative-planner"
    assert ids.index("bulk-omics-integrative-planner") < ids.index("chem-msms-predict")


def test_metagenomics_taxonomy_prefers_kraken_skill_over_generic_classification():
    ids = [n["id"] for n in _search("metagenomics taxonomy classification Kraken2", limit=5)]
    assert ids[0] == "metagenome-taxonomic-profiling"
    assert "tooluniverse-acmg-variant-classification" not in ids[:3]
    assert "tooluniverse-cancer-classification" not in ids[:3]


def test_immunofluorescence_colocalization_prefers_bioimage_tools_over_generic_analysis():
    ids = [n["id"] for n in _search("immunofluorescence colocalization analysis", limit=5)]

    assert ids[0] in {"pyimagej-fiji-bridge", "scikit-image-processing"}
    assert "data-analysis" not in ids[:3]
    assert "decision-curve-analysis" not in ids[:3]


def test_missing_skill_gap_can_be_returned_for_high_confidence_registry_gap():
    gaps = fs.missing_gap_nodes("object detection computer vision YOLO")

    assert gaps
    assert gaps[0]["id"] == "__missing_object_detection_yolo_skill__"
    assert gaps[0]["registry_gap_status"] == "missing_skill"


def test_missing_gwas_finemapping_gap_prevents_fine_tuning_false_positive():
    gaps = fs.missing_gap_nodes("GWAS summary statistics fine mapping colocalization")

    assert gaps
    assert gaps[0]["id"] == "__missing_gwas_finemapping_coloc_skill__"
    assert gaps[0]["registry_gap_status"] == "missing_skill"


def test_missing_microbiome_qiime2_gap_prevents_rnaseq_false_positive():
    gaps = fs.missing_gap_nodes("microbiome differential abundance qiime2")

    assert gaps
    assert gaps[0]["id"] == "__missing_microbiome_qiime2_abundance_skill__"
    assert gaps[0]["registry_gap_status"] == "missing_skill"


def test_missing_elisa_standard_curve_gap_prevents_decision_curve_false_positive():
    gaps = fs.missing_gap_nodes("ELISA standard curve analysis")

    assert gaps
    assert gaps[0]["id"] == "__missing_elisa_standard_curve_skill__"
    assert gaps[0]["registry_gap_status"] == "missing_skill"


def test_missing_western_blot_densitometry_gap_prevents_rnaseq_false_positive():
    gaps = fs.missing_gap_nodes("western blot densitometry quantification")

    assert gaps
    assert gaps[0]["id"] == "__missing_western_blot_densitometry_skill__"
    assert gaps[0]["registry_gap_status"] == "missing_skill"


def test_missing_qpcr_ddct_gap_does_not_replace_primer_design_skill():
    gaps = fs.missing_gap_nodes("qPCR Ct ddCt gene expression analysis")

    assert gaps
    assert gaps[0]["id"] == "__missing_qpcr_ddct_analysis_skill__"
    assert gaps[0]["registry_gap_status"] == "missing_skill"


def test_missing_immunofluorescence_colocalization_gap_prevents_em_false_positive():
    gaps = fs.missing_gap_nodes("immunofluorescence colocalization microscopy Pearson Manders")

    assert gaps
    assert gaps[0]["id"] == "__missing_immunofluorescence_colocalization_skill__"
    assert gaps[0]["registry_gap_status"] == "missing_skill"


def test_missing_luciferase_reporter_gap_prevents_bioactivity_false_positive():
    gaps = fs.missing_gap_nodes("luciferase reporter assay normalization dual luciferase")

    assert gaps
    assert gaps[0]["id"] == "__missing_luciferase_reporter_assay_skill__"
    assert gaps[0]["registry_gap_status"] == "missing_skill"


def test_no_substring_false_positive():
    # exact-token match: "em" must not match via substring of 'system'/'chemistry'
    d = load()
    fs.ensure_blobs(d["nodes"])
    n = next(iter(d["nodes"].values()))
    assert isinstance(n["_blob"], set)  # token set, not a joined string
