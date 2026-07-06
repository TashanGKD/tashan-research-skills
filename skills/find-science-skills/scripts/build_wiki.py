#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate a Karpathy-style static LLM Wiki for find-science-skills.

The search path stays in data/skill_graph_index.json + find_skills.py. This
script creates the human-maintainable layer around it: Markdown wiki pages,
a compact graph JSON, and a static HTML graph viewer. No database or runtime
service is required.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import pathlib
import re
import shutil
from collections import defaultdict

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DATA_PATH = SKILL_DIR / "data" / "skill_graph_index.json"

EDGE_LABELS = {
    "alternative": "可替代",
    "companion": "配套",
    "workflow": "下一步",
    "related": "相关",
}


def today() -> str:
    return dt.date.today().isoformat()


def yaml_quote(value) -> str:
    s = "" if value is None else str(value)
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def md_escape(value) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()


def wiki_link(page: str, label: str | None = None) -> str:
    if label and label != page.rsplit("/", 1)[-1]:
        return f"[[{page}|{label}]]"
    return f"[[{page}]]"


def ensure_clean_dir(path: pathlib.Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(clean_markdown(text), encoding="utf-8", newline="\n")


def clean_markdown(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


def load_graph(path: pathlib.Path = DATA_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sorted_nodes(graph: dict) -> list[dict]:
    nodes = list(graph["nodes"].values())
    return sorted(nodes, key=lambda n: (n.get("group") or "", -(n.get("score") or 0), n["id"]))


def frontmatter(fields: dict) -> str:
    lines = ["---"]
    bare_keys = {"type", "date", "updated", "confidence", "tier"}
    for key, value in fields.items():
        if isinstance(value, list):
            safe = [str(v).replace('"', '\\"') for v in value if v not in (None, "")]
            lines.append(f'{key}: [{", ".join(yaml_quote(v) for v in safe)}]')
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
        elif key in bare_keys and re.fullmatch(r"[A-Za-z0-9_.-]+", str(value or "")):
            lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {yaml_quote(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def top_nodes(nodes: list[dict], limit: int = 12) -> list[dict]:
    return sorted(nodes, key=lambda n: (-(n.get("score") or 0), -(n.get("repo_count") or 1), n["id"]))[:limit]


def collect_groups(graph: dict, key: str) -> dict[str, list[dict]]:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for node in graph["nodes"].values():
        buckets[node.get(key) or "未分类"].append(node)
    return dict(sorted(buckets.items(), key=lambda kv: kv[0]))


def collect_inbound(graph: dict) -> dict[str, list[tuple[str, str, float | None]]]:
    inbound: dict[str, list[tuple[str, str, float | None]]] = defaultdict(list)
    for source, node in graph["nodes"].items():
        for edge_type, pairs in (node.get("edges") or {}).items():
            for target, weight in pairs:
                if target in graph["nodes"]:
                    inbound[target].append((source, edge_type, weight))
    return inbound


def skill_page(node: dict, graph: dict, inbound: dict[str, list[tuple[str, str, float | None]]]) -> str:
    fields = {
        "title": node["name"],
        "type": "skill",
        "tags": [node.get("group"), node.get("domain_l2"), node.get("tier")],
        "date": today(),
        "updated": today(),
        "confidence": "well_sourced" if not node.get("review") else "draft",
        "skill_id": node["id"],
        "quality_score": node.get("score") or 0,
        "tier": node.get("tier") or "",
        "needs_review": bool(node.get("review")),
        "source_repo": node.get("example_repo") or "",
        "source_path": node.get("path") or "",
    }
    desc = node.get("desc") or "暂无描述。"
    zh = node.get("zh") or ""
    lines = [frontmatter(fields), f"# {node['name']}\n"]
    lines.append("## 一句话定位\n")
    lines.append(f"[来源] {desc.strip()}\n\n")
    lines.append("## 检索线索\n")
    lines.append(f"- 能力组：{node.get('group') or '未分类'}\n")
    lines.append(f"- 功能家族：{node.get('family') or '未分类'}\n")
    lines.append(f"- 学科：{node.get('domain') or '未分类'} / {node.get('domain_l2') or '未分类'}\n")
    lines.append(f"- 中文关键词：{zh or '暂无'}\n\n")
    lines.append("## 质量信号\n")
    lines.append("| 指标 | 值 |\n| --- | --- |\n")
    lines.append(f"| 质量分 | {node.get('score') or 0} |\n")
    lines.append(f"| Tier | {node.get('tier') or ''} |\n")
    lines.append(f"| 深评 | {node.get('deep') or '未深评'} |\n")
    lines.append(f"| 来源仓库数 | {node.get('repo_count') or 1} |\n")
    lines.append(f"| stars | {node.get('stars') or 0} |\n")
    lines.append(f"| 待复核 | {'是' if node.get('review') else '否'} |\n\n")
    lines.append("## 获取方式\n")
    lines.append(f"- 仓库：`{node.get('example_repo') or ''}`\n")
    lines.append(f"- 路径：`{node.get('path') or ''}`\n\n")
    lines.append("## 图关系\n")
    has_edges = False
    for edge_type, label in EDGE_LABELS.items():
        pairs = (node.get("edges") or {}).get(edge_type) or []
        linked = []
        for target, weight in pairs[:8]:
            target_node = graph["nodes"].get(target)
            if target_node:
                suffix = f" ({weight:.3f})" if isinstance(weight, (int, float)) else ""
                linked.append(f"{wiki_link('skills/' + target, target_node['name'])}{suffix}")
        if linked:
            has_edges = True
            lines.append(f"- {label}：" + "、".join(linked) + "\n")
    if not has_edges:
        lines.append("- 暂无显式图关系。\n")
    lines.append("\n## 反向链接\n")
    refs = inbound.get(node["id"], [])
    if not refs:
        lines.append("- 暂无。\n")
    else:
        for source, edge_type, weight in refs[:12]:
            source_node = graph["nodes"].get(source)
            if source_node:
                suffix = f" ({weight:.3f})" if isinstance(weight, (int, float)) else ""
                lines.append(f"- {wiki_link('skills/' + source, source_node['name'])}（{EDGE_LABELS.get(edge_type, edge_type)}{suffix}）\n")
    return "".join(lines)


def listing_page(title: str, page_type: str, tag: str, nodes: list[dict], summary: str) -> str:
    fields = {
        "title": title,
        "type": page_type,
        "tags": [tag],
        "date": today(),
        "updated": today(),
        "confidence": "well_sourced",
    }
    lines = [frontmatter(fields), f"# {title}\n\n", summary.strip() + "\n\n"]
    lines.append("## 代表技能\n")
    lines.append("| Skill | 能力组 | 学科 | 质量分 | 来源 |\n| --- | --- | --- | ---: | --- |\n")
    for node in top_nodes(nodes, 30):
        lines.append(
            f"| {wiki_link('skills/' + node['id'], md_escape(node['name']))} "
            f"| {md_escape(node.get('group'))} "
            f"| {md_escape(node.get('domain_l2'))} "
            f"| {node.get('score') or 0} "
            f"| `{md_escape(node.get('example_repo'))}` |\n"
        )
    return "".join(lines)


def index_page(graph: dict) -> str:
    nodes = list(graph["nodes"].values())
    cap_groups = collect_groups(graph, "group")
    domains = collect_groups(graph, "domain_l2")
    fields = {
        "title": "Find Science Skills Wiki Index",
        "type": "index",
        "tags": ["find-science-skills", "index"],
        "date": today(),
        "updated": today(),
        "confidence": "well_sourced",
    }
    lines = [frontmatter(fields), "# Find Science Skills Wiki Index\n\n"]
    lines.append(f"- 技能数：{len(nodes)}\n")
    lines.append(f"- 能力组：{len(cap_groups)}\n")
    lines.append(f"- 学科细分：{len(domains)}\n")
    lines.append("- 机器检索入口：`scripts/find_skills.py`\n")
    lines.append("- 机器索引：`data/skill_graph_index.json`\n")
    lines.append("- 可视化：`site/graph.html`\n\n")
    lines.append("## 概览\n")
    lines.append("- [[overview]] — 全局概览\n")
    lines.append("- [[synthesis]] — 跨能力链路综合\n")
    lines.append("- [[comparisons/conflicts]] — 待复核与冲突汇总\n")
    lines.append("- [[log]] — 生成日志\n\n")
    lines.append("## 能力组\n")
    for name, bucket in cap_groups.items():
        lines.append(f"- {wiki_link('capabilities/' + name)} — {len(bucket)} 技能\n")
    lines.append("\n## 学科细分\n")
    for name, bucket in domains.items():
        lines.append(f"- {wiki_link('domains/' + name)} — {len(bucket)} 技能\n")
    lines.append("\n## 高分技能\n")
    for node in top_nodes(nodes, 40):
        lines.append(f"- {wiki_link('skills/' + node['id'])} — {node.get('group')} / {node.get('domain_l2')} / 质量分 {node.get('score') or 0}\n")
    return "".join(lines)


def overview_page(graph: dict) -> str:
    nodes = list(graph["nodes"].values())
    cap_groups = collect_groups(graph, "group")
    domains = collect_groups(graph, "domain_l2")
    fields = {
        "title": "全局概览",
        "type": "overview",
        "tags": ["overview", "find-science-skills"],
        "date": today(),
        "updated": today(),
        "confidence": "well_sourced",
    }
    lines = [frontmatter(fields), "# 全局概览\n\n"]
    lines.append("本 Wiki 是 `find-science-skills` 的静态知识层。它不替代 `find_skills.py` 的机器检索，")
    lines.append("而是为每个推荐结果提供可读解释、来源、质量信号和图关系。\n\n")
    lines.append("## 当前状态\n")
    lines.append(f"- 技能节点：{len(nodes)}\n")
    lines.append(f"- 能力组：{len(cap_groups)}\n")
    lines.append(f"- 学科细分：{len(domains)}\n")
    lines.append(f"- 数据 schema：`{graph.get('schema')}`\n\n")
    lines.append("## 使用方式\n")
    lines.append("1. Agent 先运行 `python scripts/find_skills.py \"科研需求\"` 获取推荐。\n")
    lines.append("2. 根据推荐结果打开对应 `wiki/skills/<skill-id>.md` 查看证据和边界。\n")
    lines.append("3. 需要浏览全局关系时打开 `site/graph.html`。\n")
    return "".join(lines)


def synthesis_page(graph: dict) -> str:
    fields = {
        "title": "跨能力链路综合",
        "type": "synthesis",
        "tags": ["synthesis", "skill-graph"],
        "date": today(),
        "updated": today(),
        "confidence": "well_sourced",
    }
    lines = [frontmatter(fields), "# 跨能力链路综合\n\n"]
    lines.append("本页记录从 skill graph 得到的工作流理解：发现获取 → 构思编排 → 执行实验 → 数据分析 → 表达发表。\n\n")
    families = collect_groups(graph, "family")
    for family, nodes in families.items():
        lines.append(f"## {family}\n")
        for node in top_nodes(nodes, 10):
            lines.append(f"- {wiki_link('skills/' + node['id'], node['name'])} — {node.get('group')} / {node.get('domain_l2')}\n")
        lines.append("\n")
    return "".join(lines)


def conflicts_page(graph: dict) -> str:
    fields = {
        "title": "待复核与冲突汇总",
        "type": "comparison",
        "tags": ["conflicts", "review"],
        "date": today(),
        "updated": today(),
        "confidence": "well_sourced",
    }
    review_nodes = [n for n in graph["nodes"].values() if n.get("review")]
    low_nodes = [n for n in graph["nodes"].values() if (n.get("score") or 0) < 50]
    lines = [frontmatter(fields), "# 待复核与冲突汇总\n\n"]
    lines.append("## 待复核技能\n")
    if not review_nodes:
        lines.append("- 当前索引无显式 `[待复核]` 标记。\n")
    for node in top_nodes(review_nodes, 80):
        lines.append(f"- {wiki_link('skills/' + node['id'], node['name'])} — {node.get('group')} / {node.get('domain_l2')}\n")
    lines.append("\n## 低质量分技能\n")
    for node in sorted(low_nodes, key=lambda n: ((n.get("score") or 0), n["id"]))[:80]:
        lines.append(f"- {wiki_link('skills/' + node['id'], node['name'])} — 质量分 {node.get('score') or 0}\n")
    return "".join(lines)


def log_page(graph: dict) -> str:
    fields = {
        "title": "生成日志",
        "type": "log",
        "tags": ["log"],
        "date": today(),
        "updated": today(),
        "confidence": "well_sourced",
    }
    return (
        frontmatter(fields)
        + "# 生成日志\n\n"
        + f"- {today()}: 从 `data/skill_graph_index.json` 生成静态 Wiki、graph view 和 HTML 图谱。"
        + f"节点数 {len(graph['nodes'])}。\n"
    )


def schema_page() -> str:
    fields = {
        "title": "LLM Wiki 维护约定",
        "type": "schema",
        "tags": ["schema", "maintenance"],
        "date": today(),
        "updated": today(),
        "confidence": "well_sourced",
    }
    return (
        frontmatter(fields)
        + "# LLM Wiki 维护约定\n\n"
        + "本 Wiki 采用 Karpathy-style LLM Wiki：`data/` 是机器索引，`wiki/` 是可维护解释层，"
        + "`site/graph.html` 是静态浏览入口。\n\n"
        + "## 维护原则\n"
        + "- 优先更新已有页面，避免重复页面。\n"
        + "- 关键判断保留来源、质量分和待复核状态。\n"
        + "- 推荐排序问题优先修 `data/skill_graph_index.json` 或 `scripts/find_skills.py`，不要只改 wiki 文案。\n"
        + "- Wiki 页面用于解释和审查，不作为“该装哪个 skill”的主推荐引擎。\n"
        + "- 需要找解释页、证据页、能力组页时使用 `scripts/search_wiki.py`，它读取静态 `wiki/search_index.json`。\n"
    )


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    raw = text[4:end].splitlines()
    body = text[end + 5:]
    fields = {}
    for line in raw:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            parts = [p.strip().strip('"') for p in value[1:-1].split(",") if p.strip()]
            fields[key.strip()] = parts
        elif value.lower() in {"true", "false"}:
            fields[key.strip()] = value.lower() == "true"
        else:
            clean = value.strip('"')
            if re.fullmatch(r"-?\d+", clean):
                fields[key.strip()] = int(clean)
            elif re.fullmatch(r"-?\d+\.\d+", clean):
                fields[key.strip()] = float(clean)
            else:
                fields[key.strip()] = clean
    return fields, body


def compact_text(text: str, max_chars: int = 900) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[\[([^|\]]+)\|?([^\]]*)\]\]", lambda m: m.group(2) or m.group(1), text)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", text)
    text = re.sub(r"[#>*_|`~-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def build_search_index(wiki_dir: pathlib.Path) -> dict:
    documents = []
    for page in sorted(wiki_dir.rglob("*.md")):
        if page.name == "search_index.json":
            continue
        text = page.read_text(encoding="utf-8")
        fields, body = parse_frontmatter(text)
        rel = page.relative_to(wiki_dir.parent).as_posix()
        title = fields.get("title") or page.stem
        doc_type = fields.get("type") or "page"
        body_compact = compact_text(body)
        documents.append({
            "path": rel,
            "title": title,
            "type": doc_type,
            "tags": fields.get("tags") or [],
            "skill_id": fields.get("skill_id") or "",
            "quality_score": fields.get("quality_score") or 0,
            "source_repo": fields.get("source_repo") or "",
            "source_path": fields.get("source_path") or "",
            "summary": body_compact[:260],
            "text": " ".join([
                str(title),
                " ".join(fields.get("tags") or []),
                str(fields.get("skill_id") or ""),
                str(fields.get("source_repo") or ""),
                str(fields.get("source_path") or ""),
                body_compact,
            ]).strip(),
        })
    return {
        "schema": "find_science_skills_wiki_search_v1",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "document_count": len(documents),
        "documents": documents,
    }


def build_graph_view(graph: dict, edge_limit_per_type: int = 4) -> dict:
    nodes = []
    for node in graph["nodes"].values():
        nodes.append({
            "id": node["id"],
            "label": node.get("name") or node["id"],
            "group": node.get("group") or "",
            "family": node.get("family") or "",
            "domain": node.get("domain") or "",
            "domain_l2": node.get("domain_l2") or "",
            "score": node.get("score") or 0,
            "tier": node.get("tier") or "",
            "stars": node.get("stars") or 0,
            "repo_count": node.get("repo_count") or 1,
            "review": bool(node.get("review")),
            "wiki": f"../wiki/skills/{node['id']}.md",
        })
    edges = []
    seen = set()
    for source, node in graph["nodes"].items():
        for edge_type in EDGE_LABELS:
            for target, weight in ((node.get("edges") or {}).get(edge_type) or [])[:edge_limit_per_type]:
                if target not in graph["nodes"]:
                    continue
                key = (source, target, edge_type)
                if key in seen:
                    continue
                seen.add(key)
                edges.append({
                    "source": source,
                    "target": target,
                    "type": edge_type,
                    "label": EDGE_LABELS[edge_type],
                    "weight": weight,
                })
    return {
        "schema": "research_skill_graph_view_v1",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "nodes": nodes,
        "edges": edges,
    }


def graph_html(view: dict) -> str:
    embedded = json.dumps(view, ensure_ascii=False)
    escaped = html.escape(embedded, quote=False)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Find Science Skills Graph</title>
<style>
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; height: 100%; overflow: hidden; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #0f1720; color: #d8dee9; }}
  header {{ position: fixed; top: 0; left: 0; right: 0; height: 58px; display: flex; align-items: center; gap: 12px; padding: 10px 16px; background: rgba(15,23,32,.96); border-bottom: 1px solid #263442; z-index: 2; }}
  h1 {{ font-size: 17px; margin: 0; font-weight: 650; white-space: nowrap; }}
  input {{ width: min(420px, 38vw); background: #111c26; color: #f4f7fb; border: 1px solid #334658; border-radius: 6px; padding: 8px 10px; }}
  select, button {{ background: #111c26; color: #f4f7fb; border: 1px solid #334658; border-radius: 6px; padding: 8px; }}
  button {{ cursor: pointer; }}
  #graph {{ display: block; width: 100vw; height: 100vh; }}
  .panel {{ position: fixed; right: 16px; top: 74px; width: 340px; max-height: calc(100vh - 92px); overflow: auto; background: rgba(17,28,38,.96); border: 1px solid #334658; border-radius: 8px; padding: 14px; z-index: 3; }}
  .panel h2 {{ font-size: 16px; margin: 0 0 8px; overflow-wrap: anywhere; }}
  .panel p {{ color: #b7c2cf; line-height: 1.45; font-size: 13px; }}
  .meta {{ display: grid; grid-template-columns: 94px 1fr; gap: 5px 8px; font-size: 12px; color: #b7c2cf; }}
  .legend {{ position: fixed; left: 16px; bottom: 12px; color: #7e8b99; font-size: 12px; background: rgba(15,23,32,.72); padding: 7px 9px; border-radius: 6px; }}
  .pill {{ color: #9fb4c8; font-size: 12px; white-space: nowrap; }}
  a {{ color: #8bd3ff; }}
</style>
</head>
<body>
<header>
  <h1>Find Science Skills Graph</h1>
  <input id="search" placeholder="搜索 skill / 能力 / 学科">
  <select id="groupFilter"><option value="">全部能力组</option></select>
  <select id="edgeMode">
    <option value="selected">Selected-node relations</option>
    <option value="none">隐藏关联线</option>
    <option value="focused">显示当前子图精选关联</option>
  </select>
  <button id="reset">重置</button>
  <span id="count"></span>
</header>
<canvas id="graph"></canvas>
<aside class="panel" id="panel">
  <h2>静态技能图谱</h2>
  <p>Showing a quiet summary graph by default. 搜索或选择能力组后会显示匹配节点及一跳邻居，避免全量边一屏糊住。</p>
  <p>数据也可从 <code>../data/skill_graph_view.json</code> 读取；本页内嵌数据，离线打开也可用。</p>
</aside>
<div class="legend">No database. No CDN. Canvas renders a focused static subgraph.</div>
<script id="embedded-graph" type="application/json">{escaped}</script>
<script>
const GRAPH_DATA_URL = "../data/skill_graph_view.json";
const MAX_DEFAULT_NODES = 120;
const MAX_DEFAULT_EDGES = 220;
const MAX_FOCUSED_NODES = 260;
const MAX_FOCUSED_EDGES = 520;
const DEFAULT_LABEL_SCORE = 79;
const FOCUSED_LABEL_SCORE = 72;
const embedded = JSON.parse(document.getElementById("embedded-graph").textContent);
const palette = ["#6cb6ff","#a5d6ff","#7ee787","#d2a8ff","#ffa657","#ffdf5d","#56d4dd","#8bffb0","#f0a6ca","#c6b6ff","#ff7b72","#9ecbff"];
let graphData = embedded;
let state = {{ nodes: [], edges: [], selected: null, scale: 1, ox: 0, oy: 0, dragging: null, last: null }};

function loadData() {{
  if (location.protocol === "file:") return Promise.resolve(embedded);
  return fetch(GRAPH_DATA_URL).then(r => r.ok ? r.json() : embedded).catch(() => embedded);
}}

function colorFor(group) {{
  const groups = Array.from(new Set(graphData.nodes.map(d => d.group).filter(Boolean))).sort();
  const idx = Math.max(0, groups.indexOf(group));
  return palette[idx % palette.length];
}}

function nodeRank(n, degree) {{
  return (degree.get(n.id) || 0) * 4 + (n.score || 0) + Math.log10((n.stars || 0) + 1) * 8 + (n.repo_count || 1) * 2;
}}

function visibleState() {{
  const q = document.getElementById("search").value.trim().toLowerCase();
  const group = document.getElementById("groupFilter").value;
  const degree = new Map();
  for (const e of graphData.edges) {{
    degree.set(e.source, (degree.get(e.source) || 0) + 1);
    degree.set(e.target, (degree.get(e.target) || 0) + 1);
  }}
  const byId = new Map(graphData.nodes.map(n => [n.id, n]));
  let ids = new Set();
  if (!q && !group) {{
    graphData.nodes
      .slice()
      .sort((a, b) => nodeRank(b, degree) - nodeRank(a, degree))
      .slice(0, MAX_DEFAULT_NODES)
      .forEach(n => ids.add(n.id));
  }} else {{
    for (const n of graphData.nodes) {{
      const blob = `${{n.id}} ${{n.label}} ${{n.group}} ${{n.domain}} ${{n.domain_l2}}`.toLowerCase();
      if ((!group || n.group === group) && (!q || blob.includes(q))) ids.add(n.id);
    }}
    for (const e of graphData.edges) {{
      if (ids.has(e.source)) ids.add(e.target);
      if (ids.has(e.target)) ids.add(e.source);
      if (ids.size > MAX_FOCUSED_NODES) break;
    }}
  }}
  const nodes = Array.from(ids).map(id => byId.get(id)).filter(Boolean);
  const allowed = new Set(nodes.map(n => n.id));
  const limit = (!q && !group) ? MAX_DEFAULT_EDGES : MAX_FOCUSED_EDGES;
  const edges = graphData.edges
    .filter(e => allowed.has(e.source) && allowed.has(e.target))
    .sort((a, b) => (b.weight || 0) - (a.weight || 0))
    .slice(0, limit);
  return {{ nodes, edges, mode: (!q && !group) ? "default" : "focused" }};
}}

function layout(nodes) {{
  const w = window.innerWidth, h = window.innerHeight;
  const cx = w * .48, cy = h * .55;
  const groups = Array.from(new Set(nodes.map(n => n.group).filter(Boolean))).sort();
  const buckets = new Map(groups.map(g => [g, []]));
  for (const n of nodes) (buckets.get(n.group) || buckets.get(groups[0]) || []).push(n);
  groups.forEach((g, gi) => {{
    const bucket = buckets.get(g) || [];
    const angle0 = (Math.PI * 2 * gi) / Math.max(1, groups.length);
    const ring = Math.min(w, h) * (.18 + (gi % 3) * .075);
    bucket.forEach((n, i) => {{
      const a = angle0 + (i - bucket.length / 2) * 0.045;
      n.x = cx + Math.cos(a) * ring + Math.cos(i * 2.399) * 24;
      n.y = cy + Math.sin(a) * ring + Math.sin(i * 2.399) * 24;
      n.r = 3.4 + Math.sqrt(Math.max(1, n.score || 1)) * .58;
    }});
  }});
}}

function draw() {{
  const canvas = document.getElementById("graph");
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.floor(window.innerWidth * dpr);
  canvas.height = Math.floor(window.innerHeight * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
  ctx.save();
  ctx.translate(state.ox, state.oy);
  ctx.scale(state.scale, state.scale);
  const byId = new Map(state.nodes.map(n => [n.id, n]));
  const edgesToDraw = displayEdges();
  ctx.lineCap = "round";
  for (const e of edgesToDraw) {{
    const a = byId.get(e.source), b = byId.get(e.target);
    if (!a || !b) continue;
    ctx.strokeStyle = e.type === "workflow" ? "rgba(255,223,93,.28)" : "rgba(126,139,153,.13)";
    ctx.lineWidth = e.type === "workflow" ? 1.0 : .55;
    ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
  }}
  ctx.font = "11px -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
  for (const n of state.nodes) {{
    ctx.fillStyle = colorFor(n.group);
    ctx.strokeStyle = state.selected && state.selected.id === n.id ? "#ffffff" : (n.review ? "#ff7b72" : "#0f1720");
    ctx.lineWidth = state.selected && state.selected.id === n.id ? 2.4 : 1.2;
    ctx.beginPath(); ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    const labelScore = (document.getElementById("search").value.trim() || document.getElementById("groupFilter").value) ? FOCUSED_LABEL_SCORE : DEFAULT_LABEL_SCORE;
    if (state.scale > .9 || n.score >= labelScore || (state.selected && state.selected.id === n.id)) {{
      ctx.fillStyle = "#d8dee9";
      const label = n.label.length > 30 ? n.label.slice(0, 28) + "..." : n.label;
      ctx.fillText(label, n.x + n.r + 3, n.y + 3);
    }}
  }}
  ctx.restore();
  document.getElementById("count").textContent = `${{state.nodes.length}} shown / ${{graphData.nodes.length}} skills · ${{edgesToDraw.length}} visible / ${{graphData.edges.length}} relations`;
}}

function refresh() {{
  const v = visibleState();
  state.nodes = v.nodes.map(n => ({{...n}}));
  state.edges = v.edges;
  layout(state.nodes);
  draw();
}}

function displayEdges() {{
  const mode = document.getElementById("edgeMode").value;
  if (mode === "none") return [];
  if (mode === "focused") return state.edges;
  if (!state.selected) return [];
  const selectedId = state.selected.id;
  return state.edges.filter(e => e.source === selectedId || e.target === selectedId);
}}

function pickNode(x, y) {{
  const px = (x - state.ox) / state.scale;
  const py = (y - state.oy) / state.scale;
  for (let i = state.nodes.length - 1; i >= 0; i--) {{
    const n = state.nodes[i];
    const dx = px - n.x, dy = py - n.y;
    if (dx * dx + dy * dy <= (n.r + 5) * (n.r + 5)) return n;
  }}
  return null;
}}

function showPanel(d) {{
    document.getElementById("panel").innerHTML = `
      <h2>${{d.label}}</h2>
      <div class="meta">
        <span>能力组</span><strong>${{d.group || ""}}</strong>
        <span>学科</span><strong>${{d.domain_l2 || ""}}</strong>
        <span>质量分</span><strong>${{d.score}}</strong>
        <span>Tier</span><strong>${{d.tier || ""}}</strong>
        <span>来源仓库数</span><strong>${{d.repo_count}}</strong>
      </div>
      <p><a href="${{d.wiki}}">打开 Wiki 页面</a></p>`;
}}

function wireInteractions() {{
  const canvas = document.getElementById("graph");
  canvas.addEventListener("mousedown", e => {{
    const n = pickNode(e.clientX, e.clientY);
    state.dragging = n || "pan";
    state.last = {{x: e.clientX, y: e.clientY}};
    if (n) {{ state.selected = n; showPanel(n); draw(); }}
  }});
  canvas.addEventListener("mousemove", e => {{
    if (!state.dragging) return;
    const dx = e.clientX - state.last.x, dy = e.clientY - state.last.y;
    if (state.dragging === "pan") {{ state.ox += dx; state.oy += dy; }}
    else {{ state.dragging.x += dx / state.scale; state.dragging.y += dy / state.scale; }}
    state.last = {{x: e.clientX, y: e.clientY}};
    draw();
  }});
  window.addEventListener("mouseup", () => state.dragging = null);
  canvas.addEventListener("wheel", e => {{
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.12 : .89;
    state.scale = Math.max(.22, Math.min(4, state.scale * factor));
    draw();
  }}, {{passive: false}});
  document.getElementById("search").addEventListener("input", refresh);
  document.getElementById("groupFilter").addEventListener("change", refresh);
  document.getElementById("edgeMode").addEventListener("change", draw);
  document.getElementById("reset").addEventListener("click", () => {{
    document.getElementById("search").value = "";
    document.getElementById("groupFilter").value = "";
    document.getElementById("edgeMode").value = "selected";
    state.scale = 1; state.ox = 0; state.oy = 0; state.selected = null;
    refresh();
  }});
  window.addEventListener("resize", draw);
}}

loadData().then(data => {{
  graphData = data;
  const groups = Array.from(new Set(data.nodes.map(d => d.group).filter(Boolean))).sort();
  const select = document.getElementById("groupFilter");
  for (const group of groups) {{
    const option = document.createElement("option");
    option.value = group;
    option.textContent = group;
    select.appendChild(option);
  }}
  wireInteractions();
  refresh();
}});
</script>
</body>
</html>
"""


def generate_static_knowledge_base(graph: dict, out_root: pathlib.Path) -> None:
    wiki_dir = out_root / "wiki"
    site_dir = out_root / "site"
    ensure_clean_dir(wiki_dir)
    site_dir.mkdir(parents=True, exist_ok=True)
    (out_root / "data").mkdir(parents=True, exist_ok=True)

    inbound = collect_inbound(graph)
    for node in sorted_nodes(graph):
        write_text(wiki_dir / "skills" / f"{node['id']}.md", skill_page(node, graph, inbound))

    for group, bucket in collect_groups(graph, "group").items():
        write_text(
            wiki_dir / "capabilities" / f"{group}.md",
            listing_page(group, "capability", group, bucket, f"`{group}` 能力组下共有 {len(bucket)} 个技能。"),
        )
    for domain, bucket in collect_groups(graph, "domain_l2").items():
        write_text(
            wiki_dir / "domains" / f"{domain}.md",
            listing_page(domain, "domain", domain, bucket, f"`{domain}` 学科细分下共有 {len(bucket)} 个技能。"),
        )

    write_text(wiki_dir / "index.md", index_page(graph))
    write_text(wiki_dir / "overview.md", overview_page(graph))
    write_text(wiki_dir / "synthesis.md", synthesis_page(graph))
    write_text(wiki_dir / "comparisons" / "conflicts.md", conflicts_page(graph))
    write_text(wiki_dir / "log.md", log_page(graph))
    write_text(wiki_dir / "wiki-schema.md", schema_page())
    search_index = build_search_index(wiki_dir)
    write_text(wiki_dir / "search_index.json", json.dumps(search_index, ensure_ascii=False, separators=(",", ":")))

    view = build_graph_view(graph)
    write_text(out_root / "data" / "skill_graph_view.json", json.dumps(view, ensure_ascii=False, separators=(",", ":")))
    write_text(site_dir / "graph.html", graph_html(view))


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate static Wiki + graph viewer for find-science-skills")
    ap.add_argument("--data", default=str(DATA_PATH), help="Path to skill_graph_index.json")
    ap.add_argument("--out", default=str(SKILL_DIR), help="find-science-skills package directory")
    args = ap.parse_args()
    graph = load_graph(pathlib.Path(args.data))
    out_root = pathlib.Path(args.out)
    generate_static_knowledge_base(graph, out_root)
    view = json.loads((out_root / "data" / "skill_graph_view.json").read_text(encoding="utf-8"))
    print(json.dumps({
        "wiki_pages": len(list((out_root / "wiki").rglob("*.md"))),
        "graph_nodes": len(view["nodes"]),
        "graph_edges": len(view["edges"]),
        "html": str(out_root / "site" / "graph.html"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
