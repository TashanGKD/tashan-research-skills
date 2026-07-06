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


def score_node(node, q_tokens, name_tokens, idf=None):
    if not q_tokens:
        base = 0.0
    else:
        toks = node["_blob"]                       # a set of tokens
        uq = set(q_tokens)
        matched = uq & toks                        # exact-token overlap
        if not matched:
            return -1
        # IDF weighting: rare terms (有限元) count far more than generic ones (分析)
        hitw = sum((idf.get(t, 1.0) if idf else 1.0) for t in matched)
        nh = sum((idf.get(t, 1.0) if idf else 1.0) for t in (uq & name_tokens))
        base = hitw + nh * 1.5 + len(matched) / len(uq) * 3
    stars = node.get("stars") or 0
    ev = math.log10(stars + 1) * 0.5 + math.log2((node.get("repo_count") or 1) + 1) * 0.5
    qs = (node.get("score") or 0) / 100 * 1.4
    deepb = 0.8 if node.get("deep") == "建议安装" else (-0.6 if node.get("deep") == "先修复" else 0)
    pen = 0.85 if node.get("review") else 1.0
    return (base + ev + qs + deepb) * pen


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


def print_hit(node, nodes, show_graph, indent=""):
    stars = stars_str(node.get("stars") or 0)
    prov = f"{node['repo_count']} 仓库" if node.get("repo_count", 1) > 1 else node.get("example_repo", "")
    flag = f" {Y}[待复核]{R}" if node.get("review") else ""
    q = qtag(node)
    qpart = f"  {D}质量分 {q}{R}" if q else ""
    print(f"{indent}{B}{node['name']}{R}  {D}{node.get('cap','')} / {node.get('group','')} · {node.get('domain_l2','')}{R}{flag}{deep_tag(node)}")
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
    q_tokens = tok(args.query)

    scored = []
    for sid, n in nodes.items():
        if cap and n.get("group") != cap:
            continue
        if args.owner and args.owner.lower() not in (n.get("example_repo", "").split("/")[0].lower()):
            continue
        s = score_node(n, q_tokens, set(tok(n.get("name", "") + " " + sid)), idf)
        if s >= 0:
            scored.append((s, n))
    scored.sort(key=lambda x: (-x[0], -(x[1].get("score") or 0), -(x[1].get("stars") or 0)))
    results = [n for _, n in scored[: args.limit]]

    if args.json:
        slim = []
        for n in results:
            e = n.get("edges", {})
            slim.append({
                "id": n["id"], "name": n["name"], "capability": n.get("cap"),
                "group": n.get("group"), "domain": n.get("domain"), "domain_l2": n.get("domain_l2"),
                "stars": n.get("stars"), "repo_count": n.get("repo_count"),
                "example_repo": n.get("example_repo"), "path": n.get("path"),
                "quality_score": n.get("score"), "tier": n.get("tier"),
                "deep_verdict": n.get("deep"), "needs_review": n.get("review"),
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
