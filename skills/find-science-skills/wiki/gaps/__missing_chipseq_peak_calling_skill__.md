---
title: "ChIP-seq peak calling and differential binding"
type: skill_gap
tags: ["registry-gap", "missing_skill"]
date: 2026-07-07
updated: 2026-07-07
confidence: gap_backlog
skill_id: "__missing_chipseq_peak_calling_skill__"
quality_score: 0
registry_gap_status: "missing_skill"
---

# ChIP-seq peak calling and differential binding

## 缺口定位
- Gap ID：`__missing_chipseq_peak_calling_skill__`
- 状态：`missing_skill`
- 期望行为：Recommend a ChIP-seq peak-calling and differential-binding skill when available; keep ATAC-seq peak-calling skills as weak references rather than complete substitutes.

## 用户结论
- 当前 registry 还没有可安装的对应技能；这里命中的是缺口记录，不是推荐安装项。
- 如果检索结果同时出现弱相关技能，应优先把它们理解为候选参考，而不是已验证替代方案。

## 问题说明
- 用户会看到的问题：A user with ChIP-seq aligned reads needs immunoprecipitation peak calling, control/input handling, annotation, and differential binding analysis, not ATAC-seq accessibility analysis.
- 为什么不是现有弱相关技能：
  - ATAC-seq peak-calling skills target open-chromatin accessibility and ATAC-specific parameters, not ChIP immunoprecipitation controls.
  - Generic differential-expression skills compare expression matrices, not genomic binding peaks or occupancy changes.
- 补真技能验收标准：
  - Supports ChIP-seq peak calling with input/control handling and MACS2/MACS3-style parameters.
  - Annotates peaks to genes or genomic features and reports QC such as FRiP or peak counts.
  - Supports differential binding workflows such as DiffBind-style contrasts with reproducible design metadata.

## 查询样例
- `ChIP-seq MACS2 peak calling differential binding DiffBind`
- `chromatin immunoprecipitation sequencing peak calling MACS2`
- `ChIP-seq differential binding analysis DiffBind`

## 关联 holdout
- `holdout_find_chipseq_peak_calling`
- `holdout_wiki_chipseq_peak_calling`

## 维护口径
- 这是 registry gap，不是可安装技能。
- 补真技能时，需要覆盖查询样例里的核心任务，并能解释为什么旧的弱相关命中不再应排在前面。
- 只有补入真实技能或注册表数据后，才应把相关 holdout 期望替换为真实 skill id。
