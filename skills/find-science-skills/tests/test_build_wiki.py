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


def tiny_gaps():
    return {
        "schema": "find_science_skills_retrieval_gaps_v1",
        "version": "test",
        "gaps": [
            {
                "id": "__missing_object_detection_yolo_skill__",
                "status": "missing_skill",
                "title": "General object detection / YOLO",
                "query_examples": ["object detection computer vision YOLO"],
                "desired_behavior": "Recommend a general object-detection skill when available.",
                "user_facing_problem": "Object-detection requests may otherwise be routed to broad image-analysis pages.",
                "avoid_false_positives": [
                    "Generic image processing does not provide YOLO-style detection training or inference."
                ],
                "acceptance_criteria": [
                    "Covers object-detection model selection, inference, and result interpretation."
                ],
                "source_holdout_ids": ["holdout_find_object_detection_yolo"],
            }
        ],
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


def test_static_build_uses_stable_source_timestamp(tmp_path):
    graph = tiny_graph()
    graph["generated_at"] = "2026-01-02T03:04:05"
    bw.generate_static_knowledge_base(graph, tmp_path)

    search_index = json.loads((tmp_path / "wiki" / "search_index.json").read_text(encoding="utf-8"))
    view = json.loads((tmp_path / "data" / "skill_graph_view.json").read_text(encoding="utf-8"))
    skill_page = (tmp_path / "wiki" / "skills" / "tooluniverse-electron-microscopy.md").read_text(
        encoding="utf-8"
    )
    log_page = (tmp_path / "wiki" / "log.md").read_text(encoding="utf-8")

    assert search_index["generated_at"] == "2026-01-02T03:04:05"
    assert view["generated_at"] == "2026-01-02T03:04:05"
    assert "date: 2026-01-02" in skill_page
    assert "updated: 2026-01-02" in skill_page
    assert "- 2026-01-02: 从 `data/skill_graph_index.json` 生成静态 Wiki" in log_page


def test_graph_view_includes_registry_gap_nodes(tmp_path):
    bw.generate_static_knowledge_base(tiny_graph(), tmp_path, gaps=tiny_gaps())

    view = json.loads((tmp_path / "data" / "skill_graph_view.json").read_text(encoding="utf-8"))
    gap_node = next(n for n in view["nodes"] if n["id"] == "__missing_object_detection_yolo_skill__")
    assert gap_node["type"] == "skill_gap"
    assert gap_node["label"] == "General object detection / YOLO"
    assert gap_node["group"] == "Registry gaps"
    assert gap_node["domain_l2"] == "missing_skill"
    assert gap_node["wiki"] == "../wiki/gaps/__missing_object_detection_yolo_skill__.md"

    html = (tmp_path / "site" / "graph.html").read_text(encoding="utf-8")
    assert "${n.type}" in html
    assert "nodes ·" in html


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


def test_generates_registry_gap_wiki_pages_and_search_docs(tmp_path):
    bw.generate_static_knowledge_base(tiny_graph(), tmp_path, gaps=tiny_gaps())

    gap_page = (tmp_path / "wiki" / "gaps" / "__missing_object_detection_yolo_skill__.md").read_text(
        encoding="utf-8"
    )
    assert 'title: "General object detection / YOLO"' in gap_page
    assert "type: skill_gap" in gap_page
    assert "object detection computer vision YOLO" in gap_page
    assert "holdout_find_object_detection_yolo" in gap_page
    assert "当前 registry 还没有可安装的对应技能" in gap_page
    assert "不是推荐安装项" in gap_page
    assert "## 问题说明" in gap_page
    assert "用户会看到的问题" in gap_page
    assert "为什么不是现有弱相关技能" in gap_page
    assert "补真技能验收标准" in gap_page
    assert "补真技能时，需要覆盖查询样例里的核心任务" in gap_page

    index = json.loads((tmp_path / "wiki" / "search_index.json").read_text(encoding="utf-8"))
    gap_doc = next(doc for doc in index["documents"] if doc["skill_id"] == "__missing_object_detection_yolo_skill__")
    assert gap_doc["type"] == "skill_gap"
    assert "registry-gap" in gap_doc["tags"]
    assert "General object detection / YOLO" in gap_doc["text"]


def test_search_wiki_ranks_matching_skill_page(tmp_path):
    bw.generate_static_knowledge_base(tiny_graph(), tmp_path)
    index = sw.load_index(tmp_path / "wiki" / "search_index.json")

    hits = sw.search(index, "冷冻电镜 EMDB", limit=3)
    assert hits
    assert hits[0]["skill_id"] == "tooluniverse-electron-microscopy"
    assert hits[0]["path"] == "wiki/skills/tooluniverse-electron-microscopy.md"


def test_search_wiki_uses_shared_intent_rules_data():
    assert sw.INTENT_RULES["schema"] == "find_science_skills_intent_rules_v1"
    assert "protein structure prediction" in sw.SEMANTIC_ALIASES
    assert "orca_quantum_chemistry" in sw.NAMED_TOOL_RULES
    assert "vasp_materials_dft" in sw.NAMED_TOOL_RULES


def test_search_wiki_keeps_cryo_em_above_generic_particle_tracking():
    index = {
        "documents": [
            {
                "path": "wiki/skills/trackpy-particle-tracking.md",
                "title": "trackpy-particle-tracking",
                "type": "skill",
                "tags": ["microscopy", "particle tracking"],
                "skill_id": "trackpy-particle-tracking",
                "quality_score": 65,
                "text": "Python library for single particle tracking in video microscopy with fluorescent spots.",
            },
            {
                "path": "wiki/skills/tooluniverse-electron-microscopy.md",
                "title": "tooluniverse-electron-microscopy",
                "type": "skill",
                "tags": ["electron microscopy", "cryo-EM", "EMDB"],
                "skill_id": "tooluniverse-electron-microscopy",
                "quality_score": 55,
                "text": "Search and analyze electron microscopy data, cryo-EM density maps, EMDB, EMPIAR, raw micrographs, particle picking, and 3D reconstruction.",
            },
        ]
    }

    hits = sw.search(index, "cryo EM particle picking 3D reconstruction", limit=2, doc_type="skill")
    assert hits
    assert hits[0]["skill_id"] == "tooluniverse-electron-microscopy"
    assert hits[0]["skill_id"] != "trackpy-particle-tracking"


def test_search_wiki_gromacs_trajectory_query_avoids_scrnaseq_trajectory_and_lammps():
    index = {
        "documents": [
            {
                "path": "wiki/skills/scrnaseq-trajectory-analysis.md",
                "title": "scrnaseq-trajectory-analysis",
                "type": "skill",
                "tags": ["统计分析"],
                "skill_id": "scrnaseq-trajectory-analysis",
                "quality_score": 52,
                "text": "Pseudotime inference and RNA velocity trajectory analysis of single cell RNA seq data.",
            },
            {
                "path": "wiki/skills/lammps-reaxff.md",
                "title": "lammps-reaxff",
                "type": "skill",
                "tags": ["建模仿真"],
                "skill_id": "lammps-reaxff",
                "quality_score": 64,
                "text": "LAMMPS ReaxFF molecular dynamics simulation workflows.",
            },
            {
                "path": "wiki/skills/hpc-gromacs.md",
                "title": "hpc-gromacs",
                "type": "skill",
                "tags": ["建模仿真"],
                "skill_id": "hpc-gromacs",
                "quality_score": 68,
                "text": "Build, debug, and automate GROMACS molecular dynamics trajectories, RMSD, RMSF, topology, and MDP workflows.",
            },
        ]
    }

    hits = sw.search(index, "molecular dynamics trajectory analysis GROMACS RMSD RMSF", limit=3, doc_type="skill")
    ids = [hit["skill_id"] for hit in hits]
    assert ids[0] == "hpc-gromacs"
    assert "scrnaseq-trajectory-analysis" not in ids[:3]
    assert "lammps-reaxff" not in ids[:1]


def test_search_wiki_orca_frequency_query_prefers_orca_freq_over_generic_dft():
    index = {
        "documents": [
            {
                "path": "wiki/skills/quantum-espresso.md",
                "title": "quantum-espresso",
                "type": "skill",
                "tags": ["建模仿真"],
                "skill_id": "quantum-espresso",
                "quality_score": 64,
                "text": "Quantum ESPRESSO DFT plane wave calculations.",
            },
            {
                "path": "wiki/skills/phonopy.md",
                "title": "phonopy",
                "type": "skill",
                "tags": ["建模仿真"],
                "skill_id": "phonopy",
                "quality_score": 64,
                "text": "Phonon frequency and thermochemistry workflows for periodic DFT calculations.",
            },
            {
                "path": "wiki/skills/chem-dft-orca-advanced-calculation.md",
                "title": "chem-dft-orca-advanced-calculation",
                "type": "skill",
                "tags": ["建模仿真"],
                "skill_id": "chem-dft-orca-advanced-calculation",
                "quality_score": 67,
                "text": "Write and run custom ORCA input files for advanced electronic structure methods.",
            },
            {
                "path": "wiki/skills/orca-freq.md",
                "title": "orca-freq",
                "type": "skill",
                "tags": ["建模仿真"],
                "skill_id": "orca-freq",
                "quality_score": 64,
                "text": "ORCA frequency calculation, vibrational frequencies, IR intensities, zero point energy, and thermochemistry.",
            },
        ]
    }

    hits = sw.search(index, "quantum chemistry ORCA DFT frequency calculation", limit=4, doc_type="skill")
    ids = [hit["skill_id"] for hit in hits]
    assert ids[0] == "orca-freq"
    assert "quantum-espresso" not in ids[:3]
    assert "phonopy" not in ids[:3]


def test_search_wiki_vasp_band_query_prefers_vasp_over_generic_dft_tools():
    index = {
        "documents": [
            {
                "path": "wiki/skills/quantum-espresso.md",
                "title": "quantum-espresso",
                "type": "skill",
                "tags": ["建模仿真"],
                "skill_id": "quantum-espresso",
                "quality_score": 64,
                "text": "Quantum ESPRESSO DFT plane wave calculations.",
            },
            {
                "path": "wiki/skills/phonopy.md",
                "title": "phonopy",
                "type": "skill",
                "tags": ["建模仿真"],
                "skill_id": "phonopy",
                "quality_score": 64,
                "text": "Phonon band structure and vibrational properties for periodic DFT calculations.",
            },
            {
                "path": "wiki/skills/chem-dft-orca-advanced-calculation.md",
                "title": "chem-dft-orca-advanced-calculation",
                "type": "skill",
                "tags": ["建模仿真"],
                "skill_id": "chem-dft-orca-advanced-calculation",
                "quality_score": 67,
                "text": "Write and run custom ORCA input files for advanced electronic structure methods.",
            },
            {
                "path": "wiki/skills/hpc-vasp.md",
                "title": "hpc-vasp",
                "type": "skill",
                "tags": ["建模仿真"],
                "skill_id": "hpc-vasp",
                "quality_score": 68,
                "text": "Build and automate VASP workflows with INCAR, POSCAR, KPOINTS, POTCAR, band structure, DOS, and electronic structure calculations.",
            },
        ]
    }

    hits = sw.search(index, "VASP DFT band structure calculation", limit=4, doc_type="skill")
    ids = [hit["skill_id"] for hit in hits]
    assert ids[0] == "hpc-vasp"
    assert "quantum-espresso" not in ids[:3]
    assert "chem-dft-orca-advanced-calculation" not in ids[:3]


def test_search_wiki_vasp_frequency_query_prefers_vasp_freq_over_router():
    index = {
        "documents": [
            {
                "path": "wiki/skills/hpc-vasp.md",
                "title": "hpc-vasp",
                "type": "skill",
                "tags": ["建模仿真"],
                "skill_id": "hpc-vasp",
                "quality_score": 68,
                "text": "Build and automate VASP workflows with INCAR, POSCAR, KPOINTS, POTCAR, band structure, DOS, and electronic structure calculations.",
            },
            {
                "path": "wiki/skills/vasp-freq.md",
                "title": "vasp-freq",
                "type": "skill",
                "tags": ["建模仿真"],
                "skill_id": "vasp-freq",
                "quality_score": 64,
                "text": "VASP vibrational frequency calculation, zero point energy, thermochemistry, and frozen atoms for slab systems.",
            },
            {
                "path": "wiki/skills/chem-thermochemistry.md",
                "title": "chem-thermochemistry",
                "type": "skill",
                "tags": ["建模仿真"],
                "skill_id": "chem-thermochemistry",
                "quality_score": 64,
                "text": "Compute gas phase thermochemistry using ideal gas, rigid rotor, and harmonic oscillator approximations.",
            },
        ]
    }

    hits = sw.search(index, "VASP vibrational frequency thermochemistry", limit=3, doc_type="skill")
    ids = [hit["skill_id"] for hit in hits]
    assert ids[0] == "vasp-freq"
    assert ids.index("vasp-freq") < ids.index("hpc-vasp")


def test_search_wiki_expands_protein_structure_prediction_aliases():
    index = {
        "documents": [
            {
                "path": "wiki/skills/protein-structure-analysis.md",
                "title": "protein-structure-analysis",
                "type": "skill",
                "tags": ["数据分析"],
                "skill_id": "protein-structure-analysis",
                "quality_score": 70,
                "text": "Analyze protein structures after prediction.",
            },
            {
                "path": "wiki/skills/boltz.md",
                "title": "boltz",
                "type": "skill",
                "tags": ["建模仿真"],
                "skill_id": "boltz",
                "quality_score": 88,
                "text": "General protein structure prediction workflows and analysis.",
            },
            {
                "path": "wiki/skills/alphafold2.md",
                "title": "alphafold2",
                "type": "skill",
                "tags": ["建模仿真"],
                "skill_id": "alphafold2",
                "quality_score": 66,
                "text": "Run AlphaFold2 style protein structure prediction workflows.",
            },
        ]
    }

    hits = sw.search(index, "protein structure prediction alphafold", limit=2, doc_type="skill")
    assert hits[0]["skill_id"] == "alphafold2"


def test_search_wiki_pdb_retrieval_query_prefers_database_over_prediction():
    index = {
        "documents": [
            {
                "path": "wiki/skills/pdb-database.md",
                "title": "pdb-database",
                "type": "skill",
                "tags": ["数据库检索"],
                "skill_id": "pdb-database",
                "quality_score": 49,
                "text": "PDB database retrieve experimental protein structure records.",
            },
            {
                "path": "wiki/skills/alphafold2.md",
                "title": "alphafold2",
                "type": "skill",
                "tags": ["建模仿真"],
                "skill_id": "alphafold2",
                "quality_score": 66,
                "text": "Run AlphaFold2 style protein structure prediction workflows.",
            },
            {
                "path": "wiki/skills/chai1.md",
                "title": "chai1",
                "type": "skill",
                "tags": ["建模仿真"],
                "skill_id": "chai1",
                "quality_score": 66,
                "text": "Structure prediction for protein complexes and small molecules.",
            },
        ]
    }

    hits = sw.search(index, "I want to retrieve a PDB structure not predict a new AlphaFold model", limit=3, doc_type="skill")
    ids = [hit["skill_id"] for hit in hits]
    assert ids[0] == "pdb-database"
    assert "alphafold2" not in ids[:1]


def test_search_wiki_single_cell_marker_query_avoids_gene_circuit_false_positive():
    index = {
        "documents": [
            {
                "path": "wiki/skills/synthetic-biology-simulate-gene-circuit-with-growth-feedback.md",
                "title": "synthetic-biology-simulate-gene-circuit-with-growth-feedback",
                "type": "skill",
                "tags": ["建模仿真"],
                "skill_id": "synthetic-biology-simulate-gene-circuit-with-growth-feedback",
                "quality_score": 56,
                "text": "Simulate gene regulatory circuit dynamics with growth feedback.",
            },
            {
                "path": "wiki/skills/single-cell-annotation.md",
                "title": "single-cell-annotation",
                "type": "skill",
                "tags": ["统计分析"],
                "skill_id": "single-cell-annotation",
                "quality_score": 66,
                "text": "Best practices for single cell RNA seq cell type annotation with marker based methods.",
            },
        ]
    }

    hits = sw.search(index, "单细胞 注释 marker gene", limit=2, doc_type="skill")
    assert hits[0]["skill_id"] == "single-cell-annotation"


def test_search_wiki_citation_query_prefers_citation_management_over_bibtex_guide():
    index = {
        "documents": [
            {
                "path": "wiki/skills/citation-reference-reviewer.md",
                "title": "citation-reference-reviewer",
                "type": "skill",
                "tags": ["引用管理"],
                "skill_id": "citation-reference-reviewer",
                "quality_score": 78,
                "text": "Audit BibTeX references and review citation formatting for manuscript review.",
            },
            {
                "path": "wiki/skills/bibtex-management-guide.md",
                "title": "bibtex-management-guide",
                "type": "skill",
                "tags": ["引用管理"],
                "skill_id": "bibtex-management-guide",
                "quality_score": 59,
                "text": "Guide for BibTeX entry cleanup and export formatting.",
            },
            {
                "path": "wiki/skills/citation-management.md",
                "title": "citation-management",
                "type": "skill",
                "tags": ["引用管理"],
                "skill_id": "citation-management",
                "quality_score": 74,
                "text": "Manage citations, Zotero libraries, references, and BibTeX workflows.",
            },
        ]
    }

    hits = sw.search(index, "引用管理 bibtex", limit=2, doc_type="skill")
    assert hits[0]["skill_id"] == "citation-management"


def test_search_wiki_array_data_query_prefers_zarr_over_generic_analysis():
    index = {
        "documents": [
            {
                "path": "wiki/skills/data-analysis.md",
                "title": "data-analysis",
                "type": "skill",
                "tags": ["统计分析"],
                "skill_id": "data-analysis",
                "quality_score": 84,
                "text": "Excel CSV pivot table structured data analysis for uploaded spreadsheets.",
            },
            {
                "path": "wiki/skills/zarr-python.md",
                "title": "zarr-python",
                "type": "skill",
                "tags": ["数据处理"],
                "skill_id": "zarr-python",
                "quality_score": 57,
                "text": "Chunked N-D arrays, Zarr, Dask, and Xarray compatible scientific computing pipelines.",
            },
        ]
    }

    hits = sw.search(index, "climate netcdf xarray analysis", limit=2, doc_type="skill")
    assert hits[0]["skill_id"] == "zarr-python"


def test_search_wiki_metabolomics_lcms_prefers_broad_omics_planner():
    index = {
        "documents": [
            {
                "path": "wiki/skills/chem-msms-predict.md",
                "title": "chem-msms-predict",
                "type": "skill",
                "tags": ["统计分析"],
                "skill_id": "chem-msms-predict",
                "quality_score": 64,
                "text": "Predict LC MS/MS spectra from SMILES and generate MS2 fragment plots.",
            },
            {
                "path": "wiki/skills/rnaseq-functional-enrichment.md",
                "title": "rnaseq-functional-enrichment",
                "type": "skill",
                "tags": ["统计分析"],
                "skill_id": "rnaseq-functional-enrichment",
                "quality_score": 52,
                "text": "Gene set enrichment and pathway analysis for RNA-seq results.",
            },
            {
                "path": "wiki/skills/bulk-omics-integrative-planner.md",
                "title": "bulk-omics-integrative-planner",
                "type": "skill",
                "tags": ["智能体编排"],
                "skill_id": "bulk-omics-integrative-planner",
                "quality_score": 61,
                "text": "Design integrated research plans for transcriptomics, proteomics, metabolomics, and related multi omics studies.",
            },
        ]
    }

    hits = sw.search(index, "metabolomics LC-MS pathway enrichment", limit=3, doc_type="skill")
    assert hits[0]["skill_id"] == "bulk-omics-integrative-planner"


def test_search_wiki_rna_velocity_prefers_trajectory_over_annotation():
    index = {
        "documents": [
            {
                "path": "wiki/skills/scrnaseq-cell-type-annotation.md",
                "title": "scrnaseq-cell-type-annotation",
                "type": "skill",
                "tags": ["数据处理"],
                "skill_id": "scrnaseq-cell-type-annotation",
                "quality_score": 56,
                "text": "Marker based and reference based cell type annotation of single cell RNA seq clusters.",
            },
            {
                "path": "wiki/skills/scrnaseq-trajectory-analysis.md",
                "title": "scrnaseq-trajectory-analysis",
                "type": "skill",
                "tags": ["统计分析"],
                "skill_id": "scrnaseq-trajectory-analysis",
                "quality_score": 52,
                "text": "Pseudotime inference and RNA velocity analysis of single cell RNA seq data using Monocle3 and scVelo.",
            },
        ]
    }

    hits = sw.search(index, "RNA velocity trajectory analysis single cell", limit=2, doc_type="skill")
    assert hits[0]["skill_id"] == "scrnaseq-trajectory-analysis"


def test_search_wiki_metagenomics_taxonomy_prefers_kraken_skill_over_generic_classification():
    index = {
        "documents": [
            {
                "path": "wiki/skills/tooluniverse-acmg-variant-classification.md",
                "title": "tooluniverse-acmg-variant-classification",
                "type": "skill",
                "tags": ["数据库检索"],
                "skill_id": "tooluniverse-acmg-variant-classification",
                "quality_score": 53,
                "text": "Systematic ACMG variant classification for clinical significance.",
            },
            {
                "path": "wiki/skills/tooluniverse-cancer-classification.md",
                "title": "tooluniverse-cancer-classification",
                "type": "skill",
                "tags": ["统计分析"],
                "skill_id": "tooluniverse-cancer-classification",
                "quality_score": 46,
                "text": "Cancer subtype classification and OncoTree nomenclature.",
            },
            {
                "path": "wiki/skills/metagenome-taxonomic-profiling.md",
                "title": "metagenome-taxonomic-profiling",
                "type": "skill",
                "tags": ["数据处理"],
                "skill_id": "metagenome-taxonomic-profiling",
                "quality_score": 56,
                "text": "Profile microbial community composition from shotgun metagenomic reads using Kraken2, Bracken, or MetaPhlAn.",
            },
        ]
    }

    hits = sw.search(index, "metagenomics taxonomy classification Kraken2", limit=3, doc_type="skill")
    assert hits[0]["skill_id"] == "metagenome-taxonomic-profiling"


def test_search_wiki_phylogenetic_tree_query_avoids_decision_tree_false_positive():
    index = {
        "documents": [
            {
                "path": "wiki/skills/decision-tree-analysis.md",
                "title": "decision-tree-analysis",
                "type": "skill",
                "tags": ["统计分析", "机器学习"],
                "skill_id": "decision-tree-analysis",
                "quality_score": 72,
                "text": "Decision tree model in R with feature importance, classification and regression outputs.",
            },
            {
                "path": "wiki/skills/etetoolkit.md",
                "title": "etetoolkit",
                "type": "skill",
                "tags": ["数据库检索", "生物信息学"],
                "skill_id": "etetoolkit",
                "quality_score": 67,
                "text": "Phylogenetic tree toolkit ETE for Newick tree manipulation, evolutionary event detection, orthology, paralogy, and NCBI taxonomy.",
            },
            {
                "path": "wiki/skills/phylogenetics.md",
                "title": "phylogenetics",
                "type": "skill",
                "tags": ["数据处理", "生物信息学"],
                "skill_id": "phylogenetics",
                "quality_score": 64,
                "text": "Build and analyze phylogenetic trees using MAFFT, IQ-TREE 2, FastTree, ETE3, and FigTree for evolutionary analysis.",
            },
        ]
    }

    hits = sw.search(index, "phylogenetic tree inference", limit=3, doc_type="skill")
    ids = [hit["skill_id"] for hit in hits]
    assert ids[0] in {"etetoolkit", "phylogenetics"}
    assert {"etetoolkit", "phylogenetics"} <= set(ids[:2])
    assert "decision-tree-analysis" not in ids[:2]


def test_search_wiki_immunofluorescence_colocalization_prefers_bioimage_tools():
    index = {
        "documents": [
            {
                "path": "wiki/skills/data-analysis.md",
                "title": "data-analysis",
                "type": "skill",
                "tags": ["统计分析"],
                "skill_id": "data-analysis",
                "quality_score": 84,
                "text": "Excel CSV pivot table structured data analysis for uploaded spreadsheets.",
            },
            {
                "path": "wiki/skills/decision-curve-analysis.md",
                "title": "decision-curve-analysis",
                "type": "skill",
                "tags": ["统计分析"],
                "skill_id": "decision-curve-analysis",
                "quality_score": 77,
                "text": "Clinical utility decision curve analysis for binary prediction models.",
            },
            {
                "path": "wiki/skills/pyimagej-fiji-bridge.md",
                "title": "pyimagej-fiji-bridge",
                "type": "skill",
                "tags": ["数据处理"],
                "skill_id": "pyimagej-fiji-bridge",
                "quality_score": 66,
                "text": "Automate Fiji and ImageJ2 plugins for microscopy, Bio-Formats, image measurement, and bioimage analysis.",
            },
            {
                "path": "wiki/skills/scikit-image-processing.md",
                "title": "scikit-image-processing",
                "type": "skill",
                "tags": ["统计分析"],
                "skill_id": "scikit-image-processing",
                "quality_score": 66,
                "text": "Python image processing for microscopy and bioimage analysis with segmentation and region property measurement.",
            },
        ]
    }

    hits = sw.search(index, "immunofluorescence colocalization analysis", limit=3, doc_type="skill")
    assert hits[0]["skill_id"] in {"pyimagej-fiji-bridge", "scikit-image-processing"}
    assert "data-analysis" not in [hit["skill_id"] for hit in hits[:3]]
    assert "decision-curve-analysis" not in [hit["skill_id"] for hit in hits[:3]]


def test_search_wiki_bulk_rnaseq_de_prefers_differential_expression_over_normalization():
    index = {
        "documents": [
            {
                "path": "wiki/skills/gene-protein-expression-matrix-normalization.md",
                "title": "gene-protein-expression-matrix-normalization",
                "type": "skill",
                "tags": ["数据处理"],
                "skill_id": "gene-protein-expression-matrix-normalization",
                "quality_score": 70,
                "text": "Normalize bulk gene expression matrices with log2 transform. NOT for count model normalization such as DESeq2 size factors.",
            },
            {
                "path": "wiki/skills/rnaseq-differential-expression.md",
                "title": "rnaseq-differential-expression",
                "type": "skill",
                "tags": ["统计分析"],
                "skill_id": "rnaseq-differential-expression",
                "quality_score": 52,
                "text": "Statistical differential expression analysis using DESeq2 or edgeR with count matrix input.",
            },
            {
                "path": "wiki/skills/pydeseq2.md",
                "title": "pydeseq2",
                "type": "skill",
                "tags": ["统计分析"],
                "skill_id": "pydeseq2",
                "quality_score": 64,
                "text": "Differential gene expression analysis from bulk RNA-seq counts with volcano plots.",
            },
            {
                "path": "wiki/skills/differential-expression-analysis.md",
                "title": "differential-expression-analysis",
                "type": "skill",
                "tags": ["统计分析"],
                "skill_id": "differential-expression-analysis",
                "quality_score": 72,
                "text": "Analyze bulk RNA-seq expression data to identify differentially expressed genes with volcano plots.",
            },
            {
                "path": "wiki/skills/scrnaseq-differential-expression.md",
                "title": "scrnaseq-differential-expression",
                "type": "skill",
                "tags": ["统计分析"],
                "skill_id": "scrnaseq-differential-expression",
                "quality_score": 55,
                "text": "Single cell differential expression with pseudobulk DESeq2 or edgeR.",
            },
        ]
    }

    hits = sw.search(
        index,
        "I have bulk RNA-seq count matrix and need DESeq2 differential expression with volcano plot",
        limit=4,
        doc_type="skill",
    )
    ids = [hit["skill_id"] for hit in hits]
    assert ids[0] in {"rnaseq-differential-expression", "pydeseq2"}
    assert "gene-protein-expression-matrix-normalization" not in ids[:3]
    assert "scrnaseq-differential-expression" not in ids[:3]


def test_search_wiki_can_surface_high_confidence_registry_gap():
    hits = sw.search({"documents": []}, "neuroimaging NIfTI MRI fMRI analysis", limit=3, doc_type="skill")

    assert hits
    assert hits[0]["skill_id"] == "__missing_neuroimaging_nifti_skill__"
    assert hits[0]["type"] == "skill_gap"


def test_search_wiki_surfaces_gwas_finemapping_registry_gap():
    hits = sw.search({"documents": []}, "GWAS summary statistics fine mapping colocalization", limit=3, doc_type="skill")

    assert hits
    assert hits[0]["skill_id"] == "__missing_gwas_finemapping_coloc_skill__"
    assert hits[0]["type"] == "skill_gap"


def test_search_wiki_surfaces_immunofluorescence_colocalization_registry_gap():
    hits = sw.search(
        {"documents": []},
        "immunofluorescence colocalization microscopy Pearson Manders",
        limit=3,
        doc_type="skill",
    )

    assert hits
    assert hits[0]["skill_id"] == "__missing_immunofluorescence_colocalization_skill__"
    assert hits[0]["type"] == "skill_gap"


def test_search_wiki_surfaces_microbiome_qiime2_registry_gap():
    hits = sw.search({"documents": []}, "microbiome differential abundance qiime2", limit=3, doc_type="skill")

    assert hits
    assert hits[0]["skill_id"] == "__missing_microbiome_qiime2_abundance_skill__"
    assert hits[0]["type"] == "skill_gap"


def test_search_wiki_surfaces_elisa_standard_curve_registry_gap():
    hits = sw.search({"documents": []}, "ELISA standard curve analysis", limit=3, doc_type="skill")

    assert hits
    assert hits[0]["skill_id"] == "__missing_elisa_standard_curve_skill__"
    assert hits[0]["type"] == "skill_gap"


def test_search_wiki_surfaces_western_blot_densitometry_registry_gap():
    hits = sw.search({"documents": []}, "western blot densitometry quantification", limit=3, doc_type="skill")

    assert hits
    assert hits[0]["skill_id"] == "__missing_western_blot_densitometry_skill__"
    assert hits[0]["type"] == "skill_gap"


def test_search_wiki_surfaces_qpcr_ddct_registry_gap():
    hits = sw.search({"documents": []}, "qPCR Ct ddCt gene expression analysis", limit=3, doc_type="skill")

    assert hits
    assert hits[0]["skill_id"] == "__missing_qpcr_ddct_analysis_skill__"
    assert hits[0]["type"] == "skill_gap"


def test_search_wiki_surfaces_luciferase_reporter_registry_gap():
    hits = sw.search(
        {"documents": []},
        "luciferase reporter assay normalization dual luciferase",
        limit=3,
        doc_type="skill",
    )

    assert hits
    assert hits[0]["skill_id"] == "__missing_luciferase_reporter_assay_skill__"
    assert hits[0]["type"] == "skill_gap"
