---
title: "Luciferase reporter assay normalization"
type: skill_gap
tags: ["registry-gap", "missing_skill"]
date: 2026-07-07
updated: 2026-07-07
confidence: gap_backlog
skill_id: "__missing_luciferase_reporter_assay_skill__"
quality_score: 0
registry_gap_status: "missing_skill"
---

# Luciferase reporter assay normalization

## 缺口定位
- Gap ID：`__missing_luciferase_reporter_assay_skill__`
- 状态：`missing_skill`
- 期望行为：Recommend a luciferase reporter-assay analysis skill with Firefly/Renilla normalization and reporter activity quantification when available; avoid drug bioactivity, expression-matrix normalization, or transcriptome-planning false positives.

## 用户结论
- 当前 registry 还没有可安装的对应技能；这里命中的是缺口记录，不是推荐安装项。
- 如果检索结果同时出现弱相关技能，应优先把它们理解为候选参考，而不是已验证替代方案。

## 问题说明
- 用户会看到的问题：A user has Firefly/Renilla luminescence readings and needs reporter-activity normalization, not drug bioactivity scoring or expression-matrix normalization.
- 为什么不是现有弱相关技能：
  - Bioactivity skills may analyze compound response but do not normalize dual-luciferase reporter controls.
  - Expression-matrix normalization skills operate on gene/protein matrices, not paired Firefly/Renilla assay readings.
- 补真技能验收标准：
  - Accepts Firefly and Renilla readings with blank/control groups.
  - Computes normalized reporter activity, fold change, and replicate summaries.
  - Explains blank subtraction, transfection-control normalization, and outlier handling.

## 查询样例
- `luciferase reporter assay normalization dual luciferase`
- `dual luciferase reporter assay firefly renilla normalization`
- `reporter gene assay luciferase activity normalization`

## 关联 holdout
- `holdout_find_luciferase_reporter_assay`
- `holdout_wiki_luciferase_reporter_assay`

## 维护口径
- 这是 registry gap，不是可安装技能。
- 补真技能时，需要覆盖查询样例里的核心任务，并能解释为什么旧的弱相关命中不再应排在前面。
- 只有补入真实技能或注册表数据后，才应把相关 holdout 期望替换为真实 skill id。
