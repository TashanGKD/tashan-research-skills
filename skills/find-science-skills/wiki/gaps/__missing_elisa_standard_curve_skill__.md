---
title: "ELISA standard-curve analysis"
type: skill_gap
tags: ["registry-gap", "missing_skill"]
date: 2026-07-07
updated: 2026-07-07
confidence: gap_backlog
skill_id: "__missing_elisa_standard_curve_skill__"
quality_score: 0
registry_gap_status: "missing_skill"
---

# ELISA standard-curve analysis

## 缺口定位
- Gap ID：`__missing_elisa_standard_curve_skill__`
- 状态：`missing_skill`
- 期望行为：Recommend an ELISA/immunoassay standard-curve analysis skill when available; avoid decision-curve, decision-tree, or generic spreadsheet-analysis false positives.

## 用户结论
- 当前 registry 还没有可安装的对应技能；这里命中的是缺口记录，不是推荐安装项。
- 如果检索结果同时出现弱相关技能，应优先把它们理解为候选参考，而不是已验证替代方案。

## 问题说明
- 用户会看到的问题：A user with ELISA plate absorbance and standards needs concentration interpolation and 4PL/5PL curve fitting, not a clinical decision-curve or generic spreadsheet helper.
- 为什么不是现有弱相关技能：
  - Decision-curve or decision-tree skills evaluate clinical models; they do not fit ELISA standard curves.
  - Generic spreadsheet analysis can be a manual workaround, but it is not a validated immunoassay quantification workflow.
- 补真技能验收标准：
  - Accepts standard concentrations and absorbance/OD values.
  - Fits 4PL or 5PL standard curves and reports sample concentration interpolation.
  - Explains dilution factors, replicate handling, outlier flags, and curve-fit diagnostics.

## 查询样例
- `ELISA standard curve analysis`
- `enzyme linked immunosorbent assay standard curve`
- `ELISA absorbance concentration 4PL curve fitting`

## 关联 holdout
- `holdout_find_elisa_standard_curve`
- `holdout_wiki_elisa_standard_curve`

## 维护口径
- 这是 registry gap，不是可安装技能。
- 补真技能时，需要覆盖查询样例里的核心任务，并能解释为什么旧的弱相关命中不再应排在前面。
- 只有补入真实技能或注册表数据后，才应把相关 holdout 期望替换为真实 skill id。
