---
title: "qPCR Ct/ddCt expression analysis"
type: skill_gap
tags: ["registry-gap", "missing_skill"]
date: 2026-07-07
updated: 2026-07-07
confidence: gap_backlog
skill_id: "__missing_qpcr_ddct_analysis_skill__"
quality_score: 0
registry_gap_status: "missing_skill"
---

# qPCR Ct/ddCt expression analysis

## 缺口定位
- Gap ID：`__missing_qpcr_ddct_analysis_skill__`
- 状态：`missing_skill`
- 期望行为：Recommend a qPCR Ct/ddCt expression-analysis skill when available; keep qPCR primer-design skills for primer design queries, and avoid generic expression-matrix or RNA-seq differential-expression false positives.

## 用户结论
- 当前 registry 还没有可安装的对应技能；这里命中的是缺口记录，不是推荐安装项。
- 如果检索结果同时出现弱相关技能，应优先把它们理解为候选参考，而不是已验证替代方案。

## 问题说明
- 用户会看到的问题：A user has Ct values and needs delta-delta Ct relative expression, not primer design or RNA-seq differential-expression analysis.
- 为什么不是现有弱相关技能：
  - qPCR primer-design skills help before the experiment; they do not analyze Ct tables.
  - RNA-seq differential-expression skills assume count matrices and statistical models, not Ct normalization.
- 补真技能验收标准：
  - Accepts target/reference gene Ct tables with control and treatment groups.
  - Computes delta Ct, delta-delta Ct, fold change, and replicate summaries.
  - Flags missing reference genes, high Ct values, and inconsistent technical replicates.

## 查询样例
- `qPCR Ct ddCt gene expression analysis`
- `RT-qPCR delta delta Ct analysis`
- `qPCR Ct values relative expression normalization`

## 关联 holdout
- `holdout_find_qpcr_ddct_analysis`
- `holdout_wiki_qpcr_ddct_analysis`

## 维护口径
- 这是 registry gap，不是可安装技能。
- 补真技能时，需要覆盖查询样例里的核心任务，并能解释为什么旧的弱相关命中不再应排在前面。
- 只有补入真实技能或注册表数据后，才应把相关 holdout 期望替换为真实 skill id。
