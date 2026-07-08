---
title: "CyTOF / mass cytometry analysis"
type: skill_gap
tags: ["registry-gap", "missing_skill"]
date: 2026-07-07
updated: 2026-07-07
confidence: gap_backlog
skill_id: "__missing_cytof_mass_cytometry_skill__"
quality_score: 0
registry_gap_status: "missing_skill"
---

# CyTOF / mass cytometry analysis

## 缺口定位
- Gap ID：`__missing_cytof_mass_cytometry_skill__`
- 状态：`missing_skill`
- 期望行为：Recommend a CyTOF/mass-cytometry analysis skill when available; keep FCS parsing and generic clustering skills as weak references rather than complete substitutes.

## 用户结论
- 当前 registry 还没有可安装的对应技能；这里命中的是缺口记录，不是推荐安装项。
- 如果检索结果同时出现弱相关技能，应优先把它们理解为候选参考，而不是已验证替代方案。

## 问题说明
- 用户会看到的问题：A user with CyTOF marker-intensity data needs mass-cytometry preprocessing, clustering, gating, and population abundance interpretation, not just FCS file parsing or generic clustering.
- 为什么不是现有弱相关技能：
  - flowio/flow cytometry parsing skills can read FCS-like data but do not provide CyTOF-specific transformation, clustering, marker annotation, or abundance interpretation.
  - Generic clustering skills can cluster matrices but do not explain CyTOF marker panels, arcsinh transformation, batch effects, or cell-population labeling.
- 补真技能验收标准：
  - Supports CyTOF or mass-cytometry marker-intensity matrices with arcsinh/cofactor transformation.
  - Provides clustering or gating workflows such as FlowSOM/Phenograph-style population discovery.
  - Reports marker-based population labels, abundance summaries, and reproducible preprocessing parameters.

## 查询样例
- `CyTOF mass cytometry clustering gating analysis`
- `mass cytometry arcsinh transformation FlowSOM clustering`
- `CyTOF marker expression cell population abundance analysis`

## 关联 holdout
- `holdout_find_cytof_mass_cytometry`
- `holdout_wiki_cytof_mass_cytometry`

## 维护口径
- 这是 registry gap，不是可安装技能。
- 补真技能时，需要覆盖查询样例里的核心任务，并能解释为什么旧的弱相关命中不再应排在前面。
- 只有补入真实技能或注册表数据后，才应把相关 holdout 期望替换为真实 skill id。
