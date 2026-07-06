---
title: "LLM Wiki 维护约定"
type: schema
tags: ["schema", "maintenance"]
date: 2026-07-07
updated: 2026-07-07
confidence: well_sourced
---

# LLM Wiki 维护约定

本 Wiki 采用 Karpathy-style LLM Wiki：`data/` 是机器索引，`wiki/` 是可维护解释层，`site/graph.html` 是静态浏览入口。

## 维护原则
- 优先更新已有页面，避免重复页面。
- 关键判断保留来源、质量分和待复核状态。
- 推荐排序问题优先修 `data/skill_graph_index.json` 或 `scripts/find_skills.py`，不要只改 wiki 文案。
- Wiki 页面用于解释和审查，不作为“该装哪个 skill”的主推荐引擎。
- 需要找解释页、证据页、能力组页时使用 `scripts/search_wiki.py`，它读取静态 `wiki/search_index.json`。
