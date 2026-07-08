---
title: "Immunofluorescence colocalization quantification"
type: skill_gap
tags: ["registry-gap", "missing_skill"]
date: 2026-07-07
updated: 2026-07-07
confidence: gap_backlog
skill_id: "__missing_immunofluorescence_colocalization_skill__"
quality_score: 0
registry_gap_status: "missing_skill"
---

# Immunofluorescence colocalization quantification

## 缺口定位
- Gap ID：`__missing_immunofluorescence_colocalization_skill__`
- 状态：`missing_skill`
- 期望行为：Recommend an immunofluorescence colocalization analysis skill with Pearson, Manders, and channel-overlap quantification when available; keep generic Fiji/scikit-image skills for broad microscopy processing queries and avoid electron-microscopy false positives.

## 用户结论
- 当前 registry 还没有可安装的对应技能；这里命中的是缺口记录，不是推荐安装项。
- 如果检索结果同时出现弱相关技能，应优先把它们理解为候选参考，而不是已验证替代方案。

## 问题说明
- 用户会看到的问题：A user needs channel colocalization coefficients and thresholding guidance, not broad microscopy viewing or electron-microscopy database search.
- 为什么不是现有弱相关技能：
  - Generic Fiji/scikit-image skills can process images but do not guarantee Pearson/Manders colocalization workflow decisions.
  - Electron-microscopy skills target EM density/map retrieval, not fluorescence channel overlap quantification.
- 补真技能验收标准：
  - Supports Pearson, Manders, and thresholded overlap metrics.
  - Explains channel preprocessing, background subtraction, ROI selection, and threshold choices.
  - Reports per-image/per-cell summaries with reproducible parameters.

## 查询样例
- `immunofluorescence colocalization microscopy Pearson Manders`
- `fluorescence microscopy Pearson Manders colocalization analysis`
- `IF colocalization coefficient quantification`

## 关联 holdout
- `holdout_find_immunofluorescence_colocalization`
- `holdout_wiki_immunofluorescence_colocalization`

## 维护口径
- 这是 registry gap，不是可安装技能。
- 补真技能时，需要覆盖查询样例里的核心任务，并能解释为什么旧的弱相关命中不再应排在前面。
- 只有补入真实技能或注册表数据后，才应把相关 holdout 期望替换为真实 skill id。
