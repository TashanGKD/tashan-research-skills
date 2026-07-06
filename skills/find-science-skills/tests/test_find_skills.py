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
    out = []
    for sid, n in d["nodes"].items():
        if cap and n.get("group") != cap:
            continue
        s = fs.score_node(n, q, set(fs.tok(n.get("name", "") + " " + sid)), idf, intent_cap)
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


def test_capability_filter_scoped():
    hits = _search("", cap="建模仿真", limit=10)
    assert hits and all(n["group"] == "建模仿真" for n in hits)


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


def test_no_substring_false_positive():
    # exact-token match: "em" must not match via substring of 'system'/'chemistry'
    d = load()
    fs.ensure_blobs(d["nodes"])
    n = next(iter(d["nodes"].values()))
    assert isinstance(n["_blob"], set)  # token set, not a joined string
