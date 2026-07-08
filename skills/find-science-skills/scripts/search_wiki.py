#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Search the static LLM Wiki generated for find-science-skills.

This is a file-backed search helper, not a database. It reads
`wiki/search_index.json`, scores title/tags/text with token IDF, and returns
the most relevant wiki pages.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_INDEX = SKILL_DIR / "wiki" / "search_index.json"
GAPS_CANDIDATE = SKILL_DIR / "data" / "retrieval_gaps.json"

SEMANTIC_ALIASES = {
    "alphafold": "alphafold2 alphafold3 colabfold chai1 openfold openfold3 esmfold esmfold2 boltz protein structure prediction 蛋白质结构预测",
    "protein structure prediction": "alphafold alphafold2 chai1 openfold3 esmfold2 boltz 蛋白质结构预测",
    "蛋白质结构预测": "protein structure prediction alphafold alphafold2 chai1 openfold3 esmfold2 boltz",
    "orca": "quantum chemistry dft density functional theory frequency vibrational thermochemistry optimization single point ir spectrum",
    "vasp": "dft density functional theory plane wave paw poscar incar kpoints potcar band structure dos electronic structure materials hpc",
    "冷冻电镜": "cryo em cryo-em electron microscopy emdb density map micrograph empiar particle picking 3d reconstruction 电子显微镜",
    "电子显微镜": "cryo em cryo-em electron microscopy emdb density map micrograph empiar particle picking 3d reconstruction 冷冻电镜",
    "cryo em": "冷冻电镜 电子显微镜 electron microscopy emdb density map micrograph empiar particle picking 3d reconstruction",
    "cryo-em": "冷冻电镜 电子显微镜 electron microscopy emdb density map micrograph empiar particle picking 3d reconstruction",
    "gromacs": "molecular dynamics md trajectory rmsd rmsf topology mdp force field hpc 分子动力学",
    "rmsd": "molecular dynamics gromacs md trajectory rmsf structural fluctuation 分子动力学",
    "rmsf": "molecular dynamics gromacs md trajectory rmsd structural fluctuation 分子动力学",
    "单细胞": "single cell single-cell scrna scrnaseq scRNA-seq cell type annotation marker gene 标记基因 细胞类型注释",
    "single cell": "单细胞 single-cell scrna scrnaseq cell type annotation marker gene",
    "marker gene": "标记基因 single cell annotation cell type scrnaseq",
    "rna velocity": "single cell scrna scrnaseq trajectory pseudotime scvelo monocle3 velocity 拟时序 轨迹推断",
    "trajectory analysis": "single cell scrna scrnaseq rna velocity pseudotime scvelo monocle3 拟时序 轨迹推断",
    "pseudotime": "single cell scrna scrnaseq trajectory rna velocity scvelo monocle3 拟时序 轨迹推断",
    "引用管理": "citation management reference bibtex zotero 参考文献",
    "citation management": "引用管理 reference bibtex zotero 参考文献",
    "bibtex": "citation management 引用管理 reference zotero 参考文献",
    "zotero": "citation management 引用管理 bibtex reference 参考文献",
    "netcdf": "zarr xarray dask chunked array n-dimensional arrays scientific computing climate data cloud storage parallel io",
    "xarray": "zarr netcdf dask chunked array n-dimensional arrays scientific computing climate data cloud storage parallel io",
    "climate data": "netcdf xarray zarr dask chunked array n-dimensional arrays scientific computing",
    "metabolomics": "代谢组 代谢组学 multi omics multi-omics bulk omics proteomics transcriptomics integrative planner biomedical direction pathway enrichment lcms lc ms",
    "lc-ms": "metabolomics 代谢组 代谢组学 lcms mass spectrometry multi omics bulk omics integrative planner pathway enrichment",
    "lcms": "metabolomics 代谢组 代谢组学 lc ms mass spectrometry multi omics bulk omics integrative planner pathway enrichment",
    "metagenomics": "metagenome taxonomic profiling taxonomy microbial community microbiome shotgun reads kraken2 bracken metaphlan 宏基因组 微生物群落 分类谱",
    "metagenome": "metagenomics taxonomic profiling taxonomy microbial community microbiome shotgun reads kraken2 bracken metaphlan 宏基因组 微生物群落 分类谱",
    "kraken2": "metagenome metagenomics taxonomic profiling taxonomy microbial community microbiome shotgun reads bracken metaphlan 宏基因组 微生物群落 分类谱",
    "metaphlan": "metagenome metagenomics taxonomic profiling taxonomy microbial community microbiome shotgun reads kraken2 bracken 宏基因组 微生物群落 分类谱",
    "immunofluorescence": "fluorescence microscopy colocalization colocalisation bioimage imagej fiji pyimagej scikit image channel pearson manders",
    "colocalization": "immunofluorescence fluorescence microscopy bioimage imagej fiji pyimagej scikit image channel pearson manders",
    "colocalisation": "immunofluorescence fluorescence microscopy bioimage imagej fiji pyimagej scikit image channel pearson manders",
    "mtt": "cell viability assay dose response concentration response ic50 4pl hill curve fitting drug screening",
    "cck8": "cell viability assay dose response concentration response ic50 od450 4pl hill curve fitting drug screening",
    "cell viability": "mtt cck8 dose response concentration response ic50 ec50 4pl hill curve fitting drug screening",
}


def tok(text: str) -> list[str]:
    text = (text or "").lower()
    latin = re.findall(r"[a-z0-9]+", text)
    out = [w for w in latin if len(w) >= 2 or w.isdigit()]
    for run in re.findall(r"[\u4e00-\u9fff]+", text):
        if len(run) == 1:
            out.append(run)
        else:
            out.extend(run[i:i + 2] for i in range(len(run) - 1))
    return out


def query_tokens(query: str) -> list[str]:
    expanded = [query or ""]
    low = (query or "").lower()
    pdb_retrieval_context = (
        "pdb" in low
        and ("retrieve" in low or "retriev" in low or "access" in low or "fetch" in low or "database" in low)
        and ("not predict" in low or "not prediction" in low or "不是预测" in low or "不预测" in low)
    )
    for key, value in SEMANTIC_ALIASES.items():
        if pdb_retrieval_context and key.lower() in {
            "alphafold",
            "protein structure prediction",
            "蛋白质结构预测",
        }:
            continue
        if key.lower() in low:
            expanded.append(value)
    return tok(" ".join(expanded))


def load_index(path: pathlib.Path = DEFAULT_INDEX) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_gaps(path: pathlib.Path = GAPS_CANDIDATE) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("gaps") or []


def gap_match_score(query: str, gap: dict) -> float:
    if gap.get("status") != "missing_skill":
        return -1.0
    q_tokens = set(tok(query))
    if not q_tokens:
        return -1.0
    best = 0.0
    for example in gap.get("query_examples") or []:
        example_tokens = set(tok(example))
        if not example_tokens:
            continue
        matched = q_tokens & example_tokens
        example_cov = len(matched) / max(1, len(example_tokens))
        query_cov = len(matched) / max(1, len(q_tokens))
        if len(matched) >= 3 and example_cov >= 0.75 and query_cov >= 0.6:
            best = max(best, 100.0 + example_cov * 10.0 + query_cov)
    return best if best else -1.0


def missing_gap_docs(query: str, gaps: list[dict] | None = None) -> list[dict]:
    docs = []
    source_gaps = gaps if gaps is not None else load_gaps()
    for gap in source_gaps:
        score = gap_match_score(query, gap)
        if score < 0:
            continue
        gid = gap["id"]
        docs.append({
            "path": f"wiki/gaps/{gid}.md",
            "title": gap.get("title") or gid,
            "type": "skill_gap",
            "tags": ["registry gap", "missing skill"],
            "skill_id": gid,
            "quality_score": 0,
            "summary": gap.get("desired_behavior", ""),
            "text": " ".join([
                gap.get("title", ""),
                " ".join(gap.get("query_examples") or []),
                gap.get("desired_behavior", ""),
            ]),
            "score": round(score, 4),
            "registry_gap_status": gap.get("status"),
            "source_holdout_ids": gap.get("source_holdout_ids") or [],
        })
    docs.sort(key=lambda doc: (-doc["score"], doc["skill_id"]))
    return docs


def build_idf(docs: list[dict]) -> dict[str, float]:
    df = {}
    for doc in docs:
        tokens = set(tok(" ".join([
            doc.get("title", ""),
            " ".join(doc.get("tags") or []),
            doc.get("text", ""),
        ])))
        for token in tokens:
            df[token] = df.get(token, 0) + 1
    total = max(1, len(docs))
    return {token: math.log(1.0 + total / count) for token, count in df.items()}


def intent_score(doc: dict, query: str) -> float:
    q = (query or "").lower()
    q_tokens = set(tok(q))
    title_hay = (doc.get("title", "").lower() + " " + doc.get("skill_id", "").lower())
    hay = " ".join([
        doc.get("title", ""),
        " ".join(doc.get("tags") or []),
        doc.get("text", ""),
        doc.get("skill_id", ""),
    ]).lower()
    bonus = 0.0
    pdb_retrieval_query = (
        "pdb" in q
        and ("retrieve" in q or "retriev" in q or "access" in q or "fetch" in q or "database" in q)
        and ("not predict" in q or "not prediction" in q or "不是预测" in q or "不预测" in q)
    )
    if pdb_retrieval_query:
        if "pdb-database" in title_hay:
            bonus += 40.0
        elif "drug-db-pdb" in title_hay:
            bonus += 10.0
        if any(marker in title_hay for marker in ["alphafold2", "chai1", "openfold", "esmfold", "boltz"]):
            bonus -= 28.0
        elif any(marker in hay for marker in ["structure prediction", "蛋白质结构预测", "predict protein"]):
            bonus -= 12.0
    if not pdb_retrieval_query and "alphafold" in q and ("prediction" in q or "structure" in q or "预测" in q):
        if any(marker in hay for marker in ["alphafold2", "chai1", "openfold", "esmfold", "boltz"]):
            bonus += 10.0
        if any(marker in title_hay for marker in ["alphafold2", "alphafold3", "colabfold"]):
            bonus += 18.0
        elif "alphafold" in title_hay:
            bonus += 6.0
        if "database" in hay or "access" in hay or "fetch" in hay:
            bonus -= 3.0
    cryo_em_query = (
        "冷冻电镜" in q
        or "电子显微镜" in q
        or "cryo-em" in q
        or "electron microscopy" in q
        or "emdb" in q_tokens
        or "empiar" in q_tokens
        or ("cryo" in q_tokens and "em" in q_tokens)
    )
    if cryo_em_query:
        if "tooluniverse-electron-microscopy" in title_hay:
            bonus += 48.0
        elif any(marker in hay for marker in ["electron microscopy", "cryo em", "cryo-em", "emdb", "empiar", "density maps"]):
            bonus += 20.0
        if "trackpy-particle-tracking" in title_hay:
            bonus -= 34.0
        elif any(marker in hay for marker in ["single particle tracking", "video microscopy", "fluorescent spots"]):
            bonus -= 14.0
    single_cell_query = ("单细胞" in q or "single cell" in q or "scrna" in q) and (
        "注释" in q or "annotation" in q or "marker" in q or "gene" in q
    )
    if single_cell_query:
        if any(marker in hay for marker in ["single cell", "single-cell", "scrna", "scrnaseq", "细胞类型注释", "单细胞"]):
            bonus += 8.0
        if "gene circuit" in hay or "基因回路" in hay:
            bonus -= 6.0
    trajectory_query = ("single cell" in q or "scrna" in q or "rna" in q or "单细胞" in q) and any(
        marker in q for marker in ["velocity", "trajectory", "pseudotime", "scvelo", "monocle", "拟时序", "轨迹"]
    )
    if trajectory_query:
        if any(marker in hay for marker in ["rna velocity", "pseudotime", "trajectory", "scvelo", "monocle", "拟时序", "轨迹推断"]):
            bonus += 18.0
        if any(marker in title_hay for marker in ["trajectory", "velocity", "pseudotime"]):
            bonus += 14.0
        if any(marker in hay for marker in ["cell type annotation", "marker based", "reference based", "标记基因", "细胞类型注释"]):
            bonus -= 10.0
    citation_query = any(marker in q for marker in ["引用管理", "citation", "bibtex", "zotero", "reference"])
    if citation_query:
        if any(marker in hay for marker in ["citation management", "引用管理", "zotero", "bibtex"]):
            bonus += 6.0
        if any(marker in title_hay for marker in ["citation-management", "sci-zotero", "zotero", "bibtex-management"]):
            bonus += 5.0
        if any(marker in title_hay for marker in ["reviewer", "review", "审稿"]):
            bonus -= 10.0
        elif any(marker in hay for marker in ["reviewer", "review", "审稿", "投稿"]):
            bonus -= 4.0
    array_data_query = any(marker in q for marker in ["netcdf", "xarray", "zarr", "climate data"])
    if array_data_query:
        if any(marker in hay for marker in ["zarr", "xarray", "chunked", "n-d arrays", "parallel i/o", "scientific computing"]):
            bonus += 12.0
        if any(marker in title_hay for marker in ["zarr-python", "dask"]):
            bonus += 10.0
        if any(marker in hay for marker in ["excel", "csv", "pivot", "clinical", "decision curve", "cerna", "tabular"]):
            bonus -= 5.0
    metabolomics_query = "metabolomics" in q and (
        "lc-ms" in q or "lc ms" in q or "lcms" in q or "pathway" in q or "enrichment" in q
    )
    if metabolomics_query:
        if "bulk-omics-integrative-planner" in title_hay:
            bonus += 28.0
        elif any(marker in hay for marker in ["metabolomics", "multi omics", "multi-omics", "proteomics", "transcriptomics"]):
            bonus += 8.0
        if "predict lc ms/ms" in hay or "adverse outcome pathway" in hay:
            bonus -= 8.0
    rnaseq_de_query = (
        any(marker in q for marker in ["rna-seq", "rnaseq", "bulk rna", "bulk-rna", "deseq2", "edger"])
        and any(marker in q for marker in ["differential expression", "de genes", "deg", "volcano", "count matrix"])
    )
    if rnaseq_de_query:
        bulk_context = any(marker in q for marker in ["bulk", "bulk rna", "bulk-rna", "count matrix"])
        if "rnaseq-differential-expression" in title_hay:
            bonus += 30.0
        elif "pydeseq2" in title_hay:
            bonus += 54.0
        elif "differential-expression-analysis" in title_hay:
            bonus += 20.0
        elif "bulk-rnaseq" in title_hay:
            bonus += 12.0
        if any(marker in hay for marker in ["deseq2", "edger", "differential expression", "volcano", "count matrix"]):
            bonus += 8.0
        if bulk_context and any(marker in title_hay for marker in ["scrnaseq", "single-cell", "single-cell-rna"]):
            bonus -= 42.0
        if bulk_context and any(marker in title_hay for marker in ["atac", "methylation"]):
            bonus -= 12.0
        if "gene-protein-expression-matrix-normalization" in title_hay:
            bonus -= 18.0
        elif any(marker in hay for marker in ["normalization", "log2 transform", "z score", "min max", "not for count model"]):
            bonus -= 6.0
    metagenomics_query = any(marker in q for marker in ["metagenomics", "metagenome", "kraken2", "bracken", "metaphlan", "宏基因组"])
    if metagenomics_query:
        if "metagenome-taxonomic-profiling" in title_hay:
            bonus += 32.0
        elif any(marker in hay for marker in ["metagenome", "metagenomics", "kraken2", "bracken", "metaphlan", "宏基因组"]):
            bonus += 12.0
        if any(marker in hay for marker in ["taxonomic profiling", "taxonomy", "microbial community", "微生物群落", "分类谱"]):
            bonus += 7.0
        if any(marker in title_hay for marker in ["acmg-variant-classification", "cancer-classification"]):
            bonus -= 18.0
        elif any(marker in hay for marker in ["acmg", "variant classification", "cancer classification", "tumor", "oncotree"]):
            bonus -= 8.0
    bioimage_coloc_query = any(marker in q for marker in ["immunofluorescence", "colocalization", "colocalisation"])
    if bioimage_coloc_query:
        if any(marker in title_hay for marker in ["pyimagej-fiji-bridge", "scikit-image-processing"]):
            bonus += 30.0
        elif any(marker in hay for marker in ["pyimagej", "fiji", "imagej", "scikit-image"]):
            bonus += 16.0
        if any(marker in hay for marker in ["microscopy", "bioimage", "image processing", "image analysis", "region property", "region properties", "analyze particles", "bio-formats"]):
            bonus += 8.0
        if any(marker in hay for marker in ["excel", "csv", "pivot", "decision curve", "clinical utility", "cerna", "expression matrix", "feature importance"]):
            bonus -= 12.0
    dose_response_query = any(
        marker in q
        for marker in ["mtt", "cck8", "cell viability", "ic50", "ec50", "dose response", "concentration response"]
    )
    if dose_response_query:
        if "tooluniverse-dose-response" in title_hay:
            bonus += 36.0
        elif any(marker in hay for marker in ["dose response", "concentration response", "ic50", "ec50", "hill slope", "4 parameter logistic", "4pl"]):
            bonus += 18.0
        if any(marker in hay for marker in ["cell assays", "cell assay", "cell viability", "drug screening", "enzyme/cell assays"]):
            bonus += 8.0
        if any(marker in hay for marker in ["decision curve", "decision-tree", "clinical utility", "rebuttal", "author response", "reviewer", "single cell", "cell type annotation"]):
            bonus -= 16.0
    gromacs_md_query = "gromacs" in q_tokens or "rmsd" in q_tokens or "rmsf" in q_tokens
    if gromacs_md_query:
        if "hpc-gromacs" in title_hay:
            bonus += 58.0
        elif "drug-protein-ligand-md" in title_hay:
            bonus += 10.0
        elif any(marker in hay for marker in ["gromacs", "molecular dynamics", "rmsd", "rmsf", "topology", "mdp", "force field"]):
            bonus += 18.0
        if any(marker in title_hay for marker in ["lammps", "reaxff", "deepmd"]):
            bonus -= 36.0
        elif any(marker in hay for marker in ["lammps", "reaxff", "deepmd"]):
            bonus -= 16.0
        if any(marker in title_hay for marker in ["scrnaseq", "single-cell", "single-cell-rna"]):
            bonus -= 120.0
        elif any(marker in hay for marker in ["rna velocity", "pseudotime", "single cell", "cell type annotation"]):
            bonus -= 60.0
    orca_query = "orca" in q_tokens
    if orca_query:
        frequency_query = bool(q_tokens & {"freq", "frequency", "frequencies", "vibrational", "thermochemistry"})
        if frequency_query and "orca-freq" in title_hay:
            bonus += 68.0
        elif "orca" in title_hay:
            bonus += 34.0
        elif any(marker in hay for marker in ["orca", "density functional", "dft", "single point", "optimization", "frequency", "frequencies", "vibrational", "thermochemistry"]):
            bonus += 14.0
        if any(marker in title_hay for marker in ["quantum-espresso", "phonopy", "vasp", "abinit", "gpaw", "dftbplus"]):
            bonus -= 40.0
    vasp_query = "vasp" in q_tokens
    if vasp_query:
        band_query = bool(q_tokens & {"band", "bands", "dos", "electronic"})
        freq_query = bool(q_tokens & {"freq", "frequency", "frequencies", "vibrational", "thermochemistry"})
        if band_query and "hpc-vasp" in title_hay:
            bonus += 72.0
        elif freq_query and "vasp-freq" in title_hay:
            bonus += 124.0
        elif any(marker in title_hay for marker in ["hpc-vasp", "vasp-freq"]):
            bonus += 44.0
        elif "vasp" in title_hay:
            bonus += 28.0
        elif any(marker in hay for marker in ["vasp", "incar", "poscar", "kpoints", "potcar", "band structure", "density of states", "plane wave", "paw", "electronic structure"]):
            bonus += 14.0
        if any(marker in title_hay for marker in ["quantum-espresso", "orca", "phonopy", "abinit", "gpaw", "dftbplus"]):
            bonus -= 42.0
    return bonus


def score_doc(doc: dict, query_tokens: list[str], idf: dict[str, float], query: str = "") -> float:
    if not query_tokens:
        return -1.0
    title_tokens = set(tok(doc.get("title", "")))
    skill_tokens = set(tok(doc.get("skill_id", "")))
    tag_tokens = set(tok(" ".join(doc.get("tags") or [])))
    text_tokens = set(tok(doc.get("text", "")))
    qset = set(query_tokens)
    matched = qset & (title_tokens | tag_tokens | text_tokens)
    if not matched:
        return -1.0
    title_score = sum(idf.get(t, 1.0) for t in qset & title_tokens) * 4.0
    skill_score = sum(idf.get(t, 1.0) for t in qset & skill_tokens) * 3.2
    tag_score = sum(idf.get(t, 1.0) for t in qset & tag_tokens) * 2.0
    text_score = sum(idf.get(t, 1.0) for t in qset & text_tokens)
    coverage = len(matched) / max(1, min(len(qset), 6))
    quality = (doc.get("quality_score") or 0) / 100.0
    type_bonus = 0.4 if doc.get("type") == "skill" else 0.0
    return (
        title_score
        + skill_score
        + tag_score
        + text_score
        + coverage * 2.0
        + quality
        + type_bonus
        + intent_score(doc, query)
    )


def search(index: dict, query: str, limit: int = 8, doc_type: str = "") -> list[dict]:
    docs = index.get("documents") or []
    if doc_type:
        docs = [doc for doc in docs if doc.get("type") == doc_type]
    idf = build_idf(docs)
    q_tokens = query_tokens(query)
    scored = []
    for doc in docs:
        score = score_doc(doc, q_tokens, idf, query)
        if score >= 0:
            item = dict(doc)
            item["score"] = round(score, 4)
            scored.append(item)
    scored.sort(key=lambda d: (-d["score"], -(d.get("quality_score") or 0), d.get("path", "")))
    gap_docs = missing_gap_docs(query) if doc_type in {"", "skill"} else []
    return (gap_docs + scored)[:limit]


def main() -> int:
    ap = argparse.ArgumentParser(description="Search find-science-skills static Wiki pages")
    ap.add_argument("query", nargs="*", help="Wiki search query")
    ap.add_argument("--index", default=str(DEFAULT_INDEX), help="Path to wiki/search_index.json")
    ap.add_argument("--limit", "-n", type=int, default=8)
    ap.add_argument("--type", default="", help="Filter by page type, e.g. skill/capability/domain")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    query = " ".join(args.query)
    if not query:
        ap.print_help()
        return 0
    index = load_index(pathlib.Path(args.index))
    hits = search(index, query, limit=args.limit, doc_type=args.type)
    if args.json:
        print(json.dumps({"query": query, "count": len(hits), "results": hits}, ensure_ascii=False, indent=2))
        return 0
    if not hits:
        print(f"没找到 Wiki 页面：{query}")
        return 0
    print(f"找到 {len(hits)} 个 Wiki 页面：{query}\n")
    for hit in hits:
        title = hit.get("title") or hit.get("path")
        meta = f"{hit.get('type','')} · {hit.get('path','')} · score {hit.get('score')}"
        if hit.get("skill_id"):
            meta += f" · skill {hit['skill_id']}"
        print(title)
        print(f"  {meta}")
        snippet = (hit.get("summary") or hit.get("text") or "").replace("\n", " ")[:180]
        if snippet:
            print(f"  {snippet}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
