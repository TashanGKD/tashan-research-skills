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


def load_index(path: pathlib.Path = DEFAULT_INDEX) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def score_doc(doc: dict, query_tokens: list[str], idf: dict[str, float]) -> float:
    if not query_tokens:
        return -1.0
    title_tokens = set(tok(doc.get("title", "")))
    tag_tokens = set(tok(" ".join(doc.get("tags") or [])))
    text_tokens = set(tok(doc.get("text", "")))
    query = set(query_tokens)
    matched = query & (title_tokens | tag_tokens | text_tokens)
    if not matched:
        return -1.0
    title_score = sum(idf.get(t, 1.0) for t in query & title_tokens) * 4.0
    tag_score = sum(idf.get(t, 1.0) for t in query & tag_tokens) * 2.0
    text_score = sum(idf.get(t, 1.0) for t in query & text_tokens)
    coverage = len(matched) / max(1, min(len(query), 6))
    quality = (doc.get("quality_score") or 0) / 100.0
    type_bonus = 0.4 if doc.get("type") == "skill" else 0.0
    return title_score + tag_score + text_score + coverage * 2.0 + quality + type_bonus


def search(index: dict, query: str, limit: int = 8, doc_type: str = "") -> list[dict]:
    docs = index.get("documents") or []
    if doc_type:
        docs = [doc for doc in docs if doc.get("type") == doc_type]
    idf = build_idf(docs)
    q_tokens = tok(query)
    scored = []
    for doc in docs:
        score = score_doc(doc, q_tokens, idf)
        if score >= 0:
            item = dict(doc)
            item["score"] = round(score, 4)
            scored.append(item)
    scored.sort(key=lambda d: (-d["score"], -(d.get("quality_score") or 0), d.get("path", "")))
    return scored[:limit]


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
