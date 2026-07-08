---
title: "Western blot densitometry quantification"
type: skill_gap
tags: ["registry-gap", "missing_skill"]
date: 2026-07-07
updated: 2026-07-07
confidence: gap_backlog
skill_id: "__missing_western_blot_densitometry_skill__"
quality_score: 0
registry_gap_status: "missing_skill"
---

# Western blot densitometry quantification

## 缺口定位
- Gap ID：`__missing_western_blot_densitometry_skill__`
- 状态：`missing_skill`
- 期望行为：Recommend a western blot/immunoblot densitometry analysis skill when available; avoid figure-legend, RNA-seq transcript-quantification, or generic bioinformatics false positives.

## 用户结论
- 当前 registry 还没有可安装的对应技能；这里命中的是缺口记录，不是推荐安装项。
- 如果检索结果同时出现弱相关技能，应优先把它们理解为候选参考，而不是已验证替代方案。

## 问题说明
- 用户会看到的问题：A user needs lane/band intensity measurement and normalization to loading controls, not RNA-seq transcript quantification or manuscript figure text.
- 为什么不是现有弱相关技能：
  - RNA-seq quantification skills operate on sequencing reads or count matrices, not gel/blot images.
  - Figure-legend or image-caption skills can describe a blot but do not quantify band intensity.
- 补真技能验收标准：
  - Handles band ROI intensity, background subtraction, and loading-control normalization.
  - Supports replicate summaries and fold-change reporting.
  - States image quality assumptions such as non-saturated bands and comparable exposure.

## 查询样例
- `western blot densitometry quantification`
- `western blot band intensity quantification`
- `immunoblot densitometry normalized protein bands`

## 关联 holdout
- `holdout_find_western_blot_densitometry`
- `holdout_wiki_western_blot_densitometry`

## 维护口径
- 这是 registry gap，不是可安装技能。
- 补真技能时，需要覆盖查询样例里的核心任务，并能解释为什么旧的弱相关命中不再应排在前面。
- 只有补入真实技能或注册表数据后，才应把相关 holdout 期望替换为真实 skill id。
