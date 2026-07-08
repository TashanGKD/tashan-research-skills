#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""find-science-skills — 科研版技能发现命令（对标 vercel-labs/skills 的 `npx skills find`）。

给一句科研需求（中/英文），在**他山科研技能图谱**上检索并推荐。相比纯关键词表，带两层优化：
  1. 证据排序：命中度 + CriticAgent 质量分 + 深度评测 + 多仓库共识 + stars。
  2. 图感知推荐（skill graph）：每个命中带出图邻居——同类可替代 / 同仓库配套 / 工作流下一步，
     帮 agent 组出一条连贯的技能序列，而不是给一堆孤立结果。

数据源：与本脚本同一 skill 包内的 `data/skill_graph_index.json`（节点=清洗后科研技能、
边=技能↔技能关系，含质量分/深评）。数据托管在 `github.com/TashanGKD/tashan-research-skills`，
用 `--update` 可先 `git pull` 拉取最新版本再检索。

用法：
  python find_skills.py "single cell rna"
  python find_skills.py "DFT 第一性原理" -n 5 --graph
  python find_skills.py --update "molecular docking"      # 先更新数据再检索
  python find_skills.py --capability 建模仿真 -n 10
  python find_skills.py --list-capabilities
  python find_skills.py --show diffdock
  python find_skills.py "cryo em" --json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import re
import subprocess
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent

# 数据文件候选（打包在 skill 包内优先，其次开发目录回退）
DATA_CANDIDATES = [
    SKILL_DIR / "data" / "skill_graph_index.json",
    SCRIPT_DIR / "skill_graph_index.json",
    SCRIPT_DIR / "research_skill_graph_index.json",
]
GAPS_CANDIDATE = SKILL_DIR / "data" / "retrieval_gaps.json"

# 能力簇别名（中英/同义 -> 标准功能组），让中英文过滤都命中
CAP_ALIASES = {
    "论文检索": ["文献", "检索", "literature", "search", "paper", "arxiv", "pubmed", "scholar", "论文检索"],
    "综述阅读": ["综述", "阅读", "review", "读论文", "survey"],
    "数据库检索": ["数据库", "database", "查库", "chembl", "uniprot", "pdb", "数据库检索"],
    "智能体编排": ["智能体", "agent", "编排", "orchestration", "workflow agent", "pipeline"],
    "建模仿真": ["仿真", "模拟", "建模", "simulation", "modeling", "dft", "md", "cfd", "openfoam", "vasp", "docking", "对接"],
    "仪器实验": ["仪器", "实验", "instrument", "opentrons", "hardware", "lab", "自动化", "automation"],
    "数据处理": ["数据处理", "preprocess", "processing", "cleaning", "清洗", "dask", "预处理"],
    "统计分析": ["统计", "分析", "analysis", "statistics", "single cell", "单细胞", "组学", "omics", "eda"],
    "论文写作": ["写作", "manuscript", "writing", "latex", "论文写作", "起草"],
    "引用管理": ["引用", "citation", "reference", "bibtex", "参考文献", "引用管理"],
    "投稿评审": ["投稿", "评审", "review", "rebuttal", "submission", "审稿", "期刊"],
    "可视化展示": ["可视化", "展示", "figure", "plot", "poster", "slides", "ppt", "报告", "配图"],
}

INTENT_RULES_CANDIDATE = SKILL_DIR / "data" / "intent_rules.json"


def load_intent_rules(path: pathlib.Path = INTENT_RULES_CANDIDATE) -> dict:
    if not path.exists():
        return {"semantic_aliases": {}, "intent_keywords": {}, "named_tool_rules": {}}
    return json.loads(path.read_text(encoding="utf-8"))


INTENT_RULES = load_intent_rules()

# Lightweight semantic layer and intent rules are data-backed so installer search
# and static Wiki search do not drift into separate hand-tuned truth sources.
SEMANTIC_ALIASES = INTENT_RULES.get("semantic_aliases", {})
INTENT_KEYWORDS = INTENT_RULES.get("intent_keywords", {})
NAMED_TOOL_RULES = INTENT_RULES.get("named_tool_rules", {})


def _contains_any(hay: str, needles: list[str] | None) -> bool:
    return any(str(needle).lower() in hay for needle in (needles or []))


def _rule_matches(rule: dict, q_tokens: set[str], hay: str, title_hay: str) -> bool:
    q_any = {str(token).lower() for token in (rule.get("query_tokens_any") or [])}
    if q_any and not (q_tokens & q_any):
        return False
    if rule.get("hay_contains_any") and not _contains_any(hay, rule.get("hay_contains_any")):
        return False
    if rule.get("title_contains_any") and not _contains_any(title_hay, rule.get("title_contains_any")):
        return False
    return True


def apply_intent_adjustments(rule_set: dict, q_tokens: set[str], hay: str, title_hay: str = "") -> float:
    total = 0.0
    for rule in rule_set.get("ordered_adjustments") or []:
        if _rule_matches(rule, q_tokens, hay, title_hay):
            total += float(rule.get("score") or 0.0)
            break
    for bucket in ("additive_boosts", "additive_penalties"):
        for rule in rule_set.get(bucket) or []:
            if _rule_matches(rule, q_tokens, hay, title_hay):
                total += float(rule.get("score") or 0.0)
    return total


R, B, D, C, Y, G = "\x1b[0m", "\x1b[1m", "\x1b[2m", "\x1b[36m", "\x1b[33m", "\x1b[32m"
if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
    R = B = D = C = Y = G = ""


def repo_root(start: pathlib.Path) -> pathlib.Path | None:
    p = start
    for _ in range(6):
        if (p / ".git").exists():
            return p
        if p.parent == p:
            break
        p = p.parent
    return None


def git_update() -> None:
    root = repo_root(SCRIPT_DIR)
    if not root:
        print(f"{D}未找到 git 仓库根，跳过更新（可能是脱离仓库单独拷贝的脚本）。{R}", file=sys.stderr)
        return
    print(f"{D}正在更新技能图谱：git -C {root.name} pull --ff-only …{R}", file=sys.stderr)
    try:
        r = subprocess.run(["git", "-C", str(root), "pull", "--ff-only"],
                           capture_output=True, text=True, timeout=60)
        out = (r.stdout + r.stderr).strip().splitlines()
        tail = out[-1] if out else ""
        if r.returncode == 0:
            print(f"{G}✓ 已更新（{tail}）{R}", file=sys.stderr)
        else:
            print(f"{Y}更新失败（{tail}），继续用本地数据。{R}", file=sys.stderr)
    except Exception as e:  # noqa
        print(f"{Y}更新异常（{type(e).__name__}），继续用本地数据。{R}", file=sys.stderr)


def load_graph():
    for c in DATA_CANDIDATES:
        if c.exists():
            return json.load(open(c, encoding="utf-8"))
    sys.exit(f"缺少技能图谱数据。请确认 {DATA_CANDIDATES[0]} 存在，或先 `git pull` / `--update`。")


def load_gaps(path: pathlib.Path = GAPS_CANDIDATE) -> list[dict]:
    if not path.exists():
        return []
    data = json.load(open(path, encoding="utf-8"))
    return data.get("gaps") or []


def tok(s: str):
    """Latin alnum runs (splits hyphen/dot so chem-dft-orca -> chem,dft,orca)
    + CJK bigrams（避免短中文查询靠单字乱命中）。"""
    s = (s or "").lower()
    latin = re.findall(r"[a-z0-9]+", s)
    out = [w for w in latin if len(w) >= 2 or w.isdigit()]
    for run in re.findall(r"[\u4e00-\u9fff]+", s):
        if len(run) == 1:
            out.append(run)
        else:
            out.extend(run[i:i + 2] for i in range(len(run) - 1))
    return out


def query_tokens(query: str, semantic: bool = True):
    tokens = tok(query)
    if not semantic or not query:
        return tokens
    q = query.lower()
    pdb_retrieval_context = (
        "pdb" in q
        and ("retrieve" in q or "retriev" in q or "access" in q or "fetch" in q or "database" in q)
        and ("not predict" in q or "not prediction" in q or "不是预测" in q or "不预测" in q)
    )
    extra = []
    for trigger, aliases in SEMANTIC_ALIASES.items():
        if pdb_retrieval_context and trigger.lower() in {
            "alphafold",
            "protein structure prediction",
            "蛋白质结构预测",
        }:
            continue
        if trigger.lower() in q:
            extra.extend(tok(aliases))
    if not extra:
        return tokens
    seen = set()
    merged = []
    for t in tokens + extra:
        if t not in seen:
            seen.add(t)
            merged.append(t)
    return merged


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


def missing_gap_nodes(query: str, gaps: list[dict] | None = None) -> list[dict]:
    scored = []
    source_gaps = gaps if gaps is not None else load_gaps()
    for gap in source_gaps:
        score = gap_match_score(query, gap)
        if score >= 0:
            scored.append((score, gap))
    scored.sort(key=lambda item: (-item[0], item[1].get("id", "")))
    nodes = []
    for score, gap in scored:
        nodes.append({
            "id": gap["id"],
            "name": gap.get("title") or gap["id"],
            "cap": "registry gap",
            "group": "技能缺口",
            "domain_l2": "未覆盖",
            "desc": gap.get("desired_behavior", ""),
            "example_repo": "",
            "repo_count": 0,
            "stars": 0,
            "score": round(score, 4),
            "tier": "gap",
            "review": True,
            "registry_gap_status": gap.get("status"),
            "registry_gap": True,
            "source_holdout_ids": gap.get("source_holdout_ids") or [],
            "edges": {"alternative": [], "companion": [], "workflow": [], "related": []},
        })
    return nodes


def infer_intent(query: str) -> str | None:
    q = (query or "").lower()
    matched = []
    for intent, rules in INTENT_KEYWORDS.items():
        score = sum(1 for kw in rules["query"] if kw.lower() in q)
        if score:
            matched.append((score, intent))
    if not matched:
        return None
    matched.sort(reverse=True)
    if len(matched) > 1 and matched[0][0] == matched[1][0]:
        return None
    return matched[0][1]


def resolve_cap(term: str):
    if not term:
        return None
    if term in CAP_ALIASES:
        return term
    t = term.lower()
    for cap, al in CAP_ALIASES.items():
        if t == cap or any(t == a.lower() for a in al):
            return cap
    for cap, al in CAP_ALIASES.items():
        if any(a.lower() in t or t in a.lower() for a in al):
            return cap
    return None


def stars_str(n):
    if not n:
        return ""
    return (f"{n/1000:.1f}".rstrip("0").rstrip(".") + "k★") if n >= 1000 else f"{n}★"


def blob_of(node):
    """Token SET for exact-token matching (not substring — avoids 'em' hitting
    'system'). Includes Chinese search terms (`zh`) so 中文 queries match."""
    return set(tok(" ".join([
        node.get("name", ""), node.get("desc", ""), node.get("cap", ""),
        node.get("group", ""), node.get("domain", ""), node.get("domain_l2", ""),
        node.get("facet", ""), node.get("zh", ""),
    ])))


def score_node(node, q_tokens, name_tokens, idf=None, intent_cap=None, query_intent: str | None = None):
    if not q_tokens:
        base = 0.0
    else:
        toks = node["_blob"]                       # a set of tokens
        uq = set(q_tokens)
        matched = uq & toks                        # exact-token overlap
        if not matched:
            return -1
        # IDF weighting: rare terms (有限元) count far more than generic ones (分析).
        # Semantic alias tokens are allowed into q_tokens, so coverage uses a soft
        # denominator; otherwise a rich alias expansion would over-penalize good hits.
        hitw = sum((idf.get(t, 1.0) if idf else 1.0) for t in matched)
        nh = sum((idf.get(t, 1.0) if idf else 1.0) for t in (uq & name_tokens))
        cov = len(matched) / max(1, min(len(uq), 6))
        base = hitw + nh * 1.5 + cov * 3
    stars = node.get("stars") or 0
    ev = math.log10(stars + 1) * 0.5 + math.log2((node.get("repo_count") or 1) + 1) * 0.5
    # quality: rank-percentile (spread evenly) if present, else raw/100 fallback
    qpct = node.get("qpct")
    qs = (qpct if qpct is not None else (node.get("score") or 0) / 100) * 1.6
    deepb = 0.8 if node.get("deep") == "建议安装" else (-0.6 if node.get("deep") == "先修复" else 0)
    # intent alignment: query implies a capability group -> boost that group
    intentb = 1.2 if (intent_cap and node.get("group") == intent_cap) else 0.0
    intentq = 0.0
    if query_intent:
        hay = " ".join([
            node.get("name", ""), node.get("desc", ""), node.get("group", ""),
            node.get("cap", ""), node.get("family", ""), node.get("zh", ""),
        ]).lower()
        rules = INTENT_KEYWORDS[query_intent]
        prefer_hits = sum(1 for kw in rules["prefer"] if kw.lower() in hay)
        avoid_hits = sum(1 for kw in rules["avoid"] if kw.lower() in hay)
        intentq = min(1.4, prefer_hits * 0.45) - min(1.6, avoid_hits * 0.55)
        group = node.get("group") or ""
        family = node.get("family") or ""
        if query_intent == "execution":
            name_desc = " ".join([node.get("name", ""), node.get("desc", "")]).lower()
            if group == "数据库检索":
                intentq -= 2.2
            if family == "发现获取":
                intentq -= 0.8
            if group == "建模仿真":
                intentq += 0.8
            if family == "执行实验":
                intentq += 0.35
            if any(marker in name_desc for marker in ["database", "access", "fetch", "download", "uniprot id"]):
                intentq -= 2.1
        elif query_intent == "database":
            qset = set(q_tokens)
            name_desc = " ".join([
                node.get("id", ""), node.get("name", ""), node.get("desc", ""), node.get("zh", ""),
            ]).lower()
            if group == "数据库检索":
                intentq += 1.6
            if family == "发现获取":
                intentq += 0.5
            if "pdb" in qset and "pdb-database" in name_desc:
                intentq += 8.0
            if {"pdb", "retrieve"} <= qset and any(
                marker in name_desc for marker in ["alphafold2", "chai1", "openfold", "esmfold", "boltz"]
            ):
                intentq -= 5.0
            if "not" in qset and ("predict" in qset or "prediction" in qset) and any(
                marker in name_desc for marker in ["structure prediction", "蛋白质结构预测", "alphafold2", "chai1"]
            ):
                intentq -= 5.0
        elif query_intent == "array_data":
            name_desc = " ".join([node.get("name", ""), node.get("desc", ""), node.get("zh", "")]).lower()
            if group == "数据处理":
                intentq += 1.2
            if any(marker in name_desc for marker in ["zarr", "xarray", "chunked", "n-d arrays", "并行i/o"]):
                intentq += 4.0
            if any(marker in name_desc for marker in ["dask", "parallel", "scientific computing", "科学计算"]):
                intentq += 1.2
            if group == "统计分析" and not any(marker in name_desc for marker in ["scientific data file", "xarray", "zarr"]):
                intentq -= 2.4
        elif query_intent == "econometric_time_series":
            name_desc = " ".join([node.get("id", ""), node.get("name", ""), node.get("desc", ""), node.get("zh", "")]).lower()
            if "time-series-guide" in name_desc:
                intentq += 8.0
            if "statsmodels-statistical-modeling" in name_desc:
                intentq += 5.0
            if "jqte-econometric-methods" in name_desc:
                intentq += 3.0
            if any(marker in name_desc for marker in ["arima", "sarimax", "var", "cointegration", "协整", "计量经济学", "econometric"]):
                intentq += 4.5
            if "aeon" in name_desc or any(
                marker in name_desc
                for marker in ["classification", "clustering", "segmentation", "similarity search", "machine learning tasks"]
            ):
                intentq -= 4.0
        elif query_intent == "instrumental_variables":
            name_desc = " ".join([node.get("id", ""), node.get("name", ""), node.get("desc", ""), node.get("zh", "")]).lower()
            if "iv-regression-guide" in name_desc:
                intentq += 9.0
            if any(marker in name_desc for marker in ["causal-inference-r", "r-econometrics", "stata-causal-inference"]):
                intentq += 4.0
            if any(marker in name_desc for marker in ["instrumental variables", "iv regression", "2sls", "weak instruments", "工具变量法", "两阶段最小二乘", "弱工具变量", "内生性"]):
                intentq += 5.0
            if any(marker in name_desc for marker in ["time-series-guide", "arima", "sarimax", "cointegration", "协整", "time series", "时间序列"]):
                intentq -= 5.0
            if any(marker in name_desc for marker in ["manuscript", "journal", "投稿", "写作"]):
                intentq -= 1.5
        elif query_intent == "metagenomics_taxonomy":
            name_desc = " ".join([node.get("name", ""), node.get("desc", ""), node.get("zh", "")]).lower()
            if any(marker in name_desc for marker in ["metagenome", "metagenomics", "kraken2", "bracken", "metaphlan", "宏基因组"]):
                intentq += 7.5
            if any(marker in name_desc for marker in ["taxonomic profiling", "taxonomy", "microbial community", "微生物群落", "分类谱"]):
                intentq += 3.0
            if any(marker in name_desc for marker in ["acmg", "variant classification", "cancer classification", "tumor", "oncotree", "clinical significance"]):
                intentq -= 4.5
        elif query_intent == "bioimage_colocalization":
            name_desc = " ".join([node.get("name", ""), node.get("desc", ""), node.get("zh", "")]).lower()
            if any(marker in name_desc for marker in ["pyimagej", "fiji", "imagej", "scikit-image"]):
                intentq += 7.5
            if any(marker in name_desc for marker in ["microscopy", "bioimage", "image processing", "image analysis", "region properties", "analyze particles", "bio-formats"]):
                intentq += 3.0
            if node.get("group") == "数据处理":
                intentq += 1.0
            if any(marker in name_desc for marker in ["excel", "csv", "pivot", "decision curve", "clinical utility", "cerna", "expression matrix", "feature importance"]):
                intentq -= 4.5
        elif query_intent == "dose_response_assay":
            name_desc = " ".join([node.get("name", ""), node.get("desc", ""), node.get("zh", "")]).lower()
            if "tooluniverse-dose-response" in name_desc:
                intentq += 10.0
            elif any(marker in name_desc for marker in ["dose response", "concentration response", "ic50", "ec50", "hill slope", "4 parameter logistic", "4pl"]):
                intentq += 7.0
            if any(marker in name_desc for marker in ["cell assays", "cell assay", "cell viability", "drug screening", "enzyme/cell assays"]):
                intentq += 2.5
            if any(marker in name_desc for marker in ["decision curve", "decision-tree", "clinical utility", "rebuttal", "author response", "reviewer", "single cell", "cell type annotation"]):
                intentq -= 6.0
        elif query_intent in NAMED_TOOL_RULES:
            name_desc = " ".join([node.get("id", ""), node.get("name", ""), node.get("desc", ""), node.get("zh", "")]).lower()
            intentq += apply_intent_adjustments(
                NAMED_TOOL_RULES[query_intent].get("find", {}),
                set(q_tokens),
                name_desc,
                name_desc,
            )
    pen = 0.85 if node.get("review") else 1.0
    return (base + ev + qs + deepb + intentb + intentq) * pen


def deep_tag(node):
    dv = node.get("deep")
    if not dv:
        return ""
    col = G if dv == "建议安装" else (Y if dv == "先修复" else R)
    return f" {col}[深评:{dv}]{R}"


def qtag(node):
    sc = node.get("score")
    if sc is None:
        return ""
    col = G if sc >= 70 else (Y if sc >= 50 else R)
    return f"{col}{sc}{R}"


def display_taxonomy(node):
    family = node.get("family") or "未分家族"
    group = node.get("group") or "未分组"
    domain = node.get("domain_l2") or node.get("domain") or "未分领域"
    return f"{family} / {group} · {domain}"


def print_hit(node, nodes, show_graph, indent=""):
    if node.get("registry_gap"):
        print(f"{indent}{B}{node['name']}{R}  {Y}[registry gap: {node.get('registry_gap_status')}]{R}")
        desc = node.get("desc")
        if desc:
            print(f"{indent}  {D}{desc}{R}")
        if node.get("source_holdout_ids"):
            print(f"{indent}  {D}└ holdout: {', '.join(node['source_holdout_ids'])}{R}")
        print()
        return
    stars = stars_str(node.get("stars") or 0)
    prov = f"{node['repo_count']} 仓库" if node.get("repo_count", 1) > 1 else node.get("example_repo", "")
    flag = f" {Y}[待复核]{R}" if node.get("review") else ""
    q = qtag(node)
    qpart = f"  {D}质量分 {q}{R}" if q else ""
    print(f"{indent}{B}{node['name']}{R}  {D}{display_taxonomy(node)}{R}{flag}{deep_tag(node)}")
    print(f"{indent}  {C}{node.get('example_repo','')}{R} {D}{stars} · {prov}{R}{qpart}")
    if node.get("path"):
        print(f"{indent}  {D}└ {node['path']}{R}")
    if show_graph:
        e = node.get("edges", {})

        def names(pairs, k=3):
            out = []
            for pid, _ in pairs[:k]:
                m = nodes.get(pid)
                if m:
                    out.append(m["name"])
            return out
        alt, comp, wf = names(e.get("alternative", [])), names(e.get("companion", [])), names(e.get("workflow", []))
        if alt:
            print(f"{indent}  {D}↔ 可替代:{R} {', '.join(alt)}")
        if comp:
            print(f"{indent}  {D}+ 配套(同仓库):{R} {', '.join(comp)}")
        if wf:
            print(f"{indent}  {D}→ 下一步:{R} {', '.join(wf)}")
    print()


def ensure_blobs(nodes):
    for n in nodes.values():
        if "_blob" not in n:
            n["_blob"] = blob_of(n)


def build_idf(nodes):
    """Document frequency over all node token sets -> idf weight per token."""
    import math as _m
    df = {}
    for n in nodes.values():
        for t in n["_blob"]:
            df[t] = df.get(t, 0) + 1
    N = max(1, len(nodes))
    return {t: _m.log(1.0 + N / c) for t, c in df.items()}


def run_search(args, data):
    nodes = data["nodes"]
    ensure_blobs(nodes)
    idf = build_idf(nodes)
    cap = resolve_cap(args.capability) if args.capability else None
    if args.capability and not cap:
        print(f"{D}未知能力过滤 '{args.capability}'，可用：{', '.join(CAP_ALIASES)}{R}", file=sys.stderr)
    q_tokens = query_tokens(args.query, semantic=not args.no_semantic)
    # infer intent capability from the query itself (only when unambiguous)
    intent_cap = None if cap else resolve_cap(args.query)
    query_intent = infer_intent(args.query)

    scored = []
    for sid, n in nodes.items():
        if cap and n.get("group") != cap:
            continue
        if args.owner and args.owner.lower() not in (n.get("example_repo", "").split("/")[0].lower()):
            continue
        s = score_node(n, q_tokens, set(tok(n.get("name", "") + " " + sid)), idf, intent_cap, query_intent)
        if s >= 0:
            scored.append((s, n))
    scored.sort(key=lambda x: (-x[0], -(x[1].get("score") or 0), -(x[1].get("stars") or 0)))
    gap_results = [] if cap or args.owner else missing_gap_nodes(args.query)
    results = (gap_results + [n for _, n in scored])[: args.limit]

    if args.json:
        slim = []
        for n in results:
            e = n.get("edges", {})
            slim.append({
                "id": n["id"], "name": n["name"], "capability": n.get("group"),
                "family": n.get("family"), "group": n.get("group"),
                "legacy_capability": n.get("cap"),
                "display_taxonomy": display_taxonomy(n),
                "domain": n.get("domain"), "domain_l2": n.get("domain_l2"),
                "stars": n.get("stars"), "repo_count": n.get("repo_count"),
                "example_repo": n.get("example_repo"), "path": n.get("path"),
                "quality_score": n.get("score"), "tier": n.get("tier"),
                "deep_verdict": n.get("deep"), "needs_review": n.get("review"),
                "registry_gap_status": n.get("registry_gap_status"),
                "alternative": [p[0] for p in e.get("alternative", [])[:5]],
                "companion": [p[0] for p in e.get("companion", [])[:5]],
                "workflow_next": [p[0] for p in e.get("workflow", [])[:5]],
            })
        print(json.dumps({"query": args.query, "capability": cap, "count": len(slim),
                          "results": slim}, ensure_ascii=False, indent=2))
        return

    if not results:
        print(f"{D}没找到匹配的科研 skill：\"{args.query}\"{R}")
        print(f"{D}换更具体的关键词，或 --list-capabilities 浏览能力簇。{R}")
        return
    header = f"找到 {len(results)} 个科研 skill" + (f"（能力：{cap}）" if cap else "")
    print(f"{B}{header}{R}")
    print(f"{D}排序=命中+质量分+深评+多仓库共识+stars · 安装：git clone <repo> 取 <path>{R}\n")
    for n in results:
        print_hit(n, nodes, show_graph=args.graph)


def list_capabilities(data):
    lb = data["leaderboard"]
    nodes = data["nodes"]
    order = list(CAP_ALIASES.keys())
    print(f"{B}科研能力簇 leaderboard（技能数 / 高分代表）{R}\n")
    for cap in sorted(lb, key=lambda k: order.index(k) if k in order else 99):
        info = lb[cap]
        top = ", ".join(nodes[s]["name"] for s in info["top"][:6] if s in nodes)
        print(f"{B}{cap}{R} {D}· {info['count']} 技能{R}")
        print(f"  {D}{top}{R}\n")


def show_skill(args, data):
    nodes = data["nodes"]
    ensure_blobs(nodes)
    n = nodes.get(args.show)
    if not n:
        cand = [x for x in nodes.values() if args.show.lower() in x["name"].lower()]
        if not cand:
            print(f"{D}没有该技能：{args.show}{R}")
            return
        n = cand[0]
    print_hit(n, nodes, show_graph=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="find-science-skills — 科研版技能发现（skill graph 优化）")
    ap.add_argument("query", nargs="*", help="科研需求关键词（中/英文）")
    ap.add_argument("--update", "-u", action="store_true", help="先 git pull 拉取最新技能图谱再检索")
    ap.add_argument("--capability", "-c", default="", help="按能力簇过滤，如 建模仿真 / literature")
    ap.add_argument("--owner", "-o", default="", help="按 GitHub owner 过滤")
    ap.add_argument("--limit", "-n", type=int, default=8)
    ap.add_argument("--graph", "-g", action="store_true", help="展开图邻居（可替代/配套/下一步）")
    ap.add_argument("--show", default="", help="查看单个技能及其图邻居")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-semantic", action="store_true", help="关闭轻量语义同义扩展，仅用原始关键词")
    ap.add_argument("--list-capabilities", action="store_true", help="能力簇 leaderboard")
    args = ap.parse_args()
    args.query = " ".join(args.query)

    if args.update:
        git_update()

    data = load_graph()
    if args.list_capabilities:
        list_capabilities(data)
        return 0
    if args.show:
        show_skill(args, data)
        return 0
    if not args.query and not args.capability:
        ap.print_help()
        return 0
    run_search(args, data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
