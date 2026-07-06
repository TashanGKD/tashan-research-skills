# -*- coding: utf-8 -*-
import json
import pathlib
import sys

SKILL = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))

import build_wiki as bw  # noqa: E402
import search_wiki as sw  # noqa: E402


def tiny_graph():
    return {
        "schema": "research_skill_graph_v1",
        "nodes": {
            "tooluniverse-electron-microscopy": {
                "id": "tooluniverse-electron-microscopy",
                "name": "tooluniverse-electron-microscopy",
                "cap": "数据分析",
                "group": "建模仿真",
                "family": "执行实验",
                "domain": "生命科学",
                "domain_l2": "蛋白与结构生物学",
                "facet": "分析",
                "stars": 0,
                "repo_count": 1,
                "review": False,
                "desc": "Search and analyze cryo-EM density maps and electron microscopy data.",
                "example_repo": "mims-harvard/ToolUniverse",
                "path": "plugin/skills/tooluniverse-electron-microscopy/SKILL.md",
                "zh": "冷冻电镜密度图, EMDB, 电子显微镜",
                "score": 55,
                "tier": "C",
                "deep": None,
                "edges": {
                    "alternative": [["pdb-database", 0.42]],
                    "companion": [],
                    "workflow": [],
                    "related": [],
                },
            },
            "pdb-database": {
                "id": "pdb-database",
                "name": "pdb-database",
                "cap": "数据搜寻",
                "group": "数据库检索",
                "family": "发现获取",
                "domain": "生命科学",
                "domain_l2": "蛋白与结构生物学",
                "facet": "数据",
                "stars": 2227,
                "repo_count": 1,
                "review": False,
                "desc": "Search the Protein Data Bank for structural biology models.",
                "example_repo": "google-deepmind/science-skills",
                "path": "skills/pdb_database/SKILL.md",
                "zh": "PDB数据库, 蛋白质结构, 冷冻电镜结构",
                "score": 49,
                "tier": "D",
                "deep": None,
                "edges": {
                    "alternative": [["tooluniverse-electron-microscopy", 0.42]],
                    "companion": [],
                    "workflow": [],
                    "related": [],
                },
            },
        },
        "leaderboard": {
            "建模仿真": {"count": 1, "top": ["tooluniverse-electron-microscopy"]},
            "数据库检索": {"count": 1, "top": ["pdb-database"]},
        },
    }


def test_generates_karpathy_style_wiki_pages(tmp_path):
    bw.generate_static_knowledge_base(tiny_graph(), tmp_path)

    index = (tmp_path / "wiki" / "index.md").read_text(encoding="utf-8")
    assert "[[overview]]" in index
    assert "[[skills/tooluniverse-electron-microscopy]]" in index
    assert "[[capabilities/建模仿真]]" in index

    skill_page = (tmp_path / "wiki" / "skills" / "tooluniverse-electron-microscopy.md").read_text(encoding="utf-8")
    assert 'title: "tooluniverse-electron-microscopy"' in skill_page
    assert "type: skill" in skill_page
    assert "quality_score: 55" in skill_page
    assert "plugin/skills/tooluniverse-electron-microscopy/SKILL.md" in skill_page
    assert "[[skills/pdb-database]]" in skill_page
    assert "[来源]" in skill_page


def test_generates_graph_view_json_and_static_html(tmp_path):
    bw.generate_static_knowledge_base(tiny_graph(), tmp_path)

    view = json.loads((tmp_path / "data" / "skill_graph_view.json").read_text(encoding="utf-8"))
    assert view["schema"] == "research_skill_graph_view_v1"
    assert {n["id"] for n in view["nodes"]} == {"tooluniverse-electron-microscopy", "pdb-database"}
    assert view["edges"][0]["type"] == "alternative"

    html = (tmp_path / "site" / "graph.html").read_text(encoding="utf-8")
    assert "../data/skill_graph_view.json" in html
    assert "Find Science Skills Graph" in html
    assert "https://d3js.org" not in html
    assert "<canvas id=\"graph\"" in html
    assert "function visibleState()" in html
    assert "const MAX_DEFAULT_NODES = 120" in html
    assert "const MAX_DEFAULT_EDGES = 220" in html
    assert "const DEFAULT_LABEL_SCORE = 79" in html
    assert "Showing a quiet summary graph" in html
    assert 'id="edgeMode"' in html
    assert 'value="selected"' in html
    assert "function displayEdges()" in html
    assert "Selected-node relations" in html


def test_generates_static_wiki_search_index(tmp_path):
    bw.generate_static_knowledge_base(tiny_graph(), tmp_path)

    index = json.loads((tmp_path / "wiki" / "search_index.json").read_text(encoding="utf-8"))
    assert index["schema"] == "find_science_skills_wiki_search_v1"
    paths = {doc["path"] for doc in index["documents"]}
    assert "wiki/skills/tooluniverse-electron-microscopy.md" in paths
    em_doc = next(doc for doc in index["documents"] if doc["skill_id"] == "tooluniverse-electron-microscopy")
    assert em_doc["type"] == "skill"
    assert em_doc["quality_score"] == 55
    assert "冷冻电镜" in em_doc["text"]


def test_search_wiki_ranks_matching_skill_page(tmp_path):
    bw.generate_static_knowledge_base(tiny_graph(), tmp_path)
    index = sw.load_index(tmp_path / "wiki" / "search_index.json")

    hits = sw.search(index, "冷冻电镜 EMDB", limit=3)
    assert hits
    assert hits[0]["skill_id"] == "tooluniverse-electron-microscopy"
    assert hits[0]["path"] == "wiki/skills/tooluniverse-electron-microscopy.md"
