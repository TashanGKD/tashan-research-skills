---
title: "全局概览"
type: overview
tags: ["overview", "find-science-skills"]
date: 2026-07-07
updated: 2026-07-07
confidence: well_sourced
---

# 全局概览

本 Wiki 是 `find-science-skills` 的静态知识层。它不替代 `find_skills.py` 的机器检索，而是为每个推荐结果提供可读解释、来源、质量信号和图关系。

## 当前状态
- 技能节点：1398
- 能力组：12
- 学科细分：27
- 数据 schema：`research_skill_graph_v1`

## 使用方式
1. Agent 先运行 `python scripts/find_skills.py "科研需求"` 获取推荐。
2. 根据推荐结果打开对应 `wiki/skills/<skill-id>.md` 查看证据和边界。
3. 需要浏览全局关系时打开 `site/graph.html`。
