---
title: "Microbiome QIIME2 differential abundance"
type: skill_gap
tags: ["registry-gap", "missing_skill"]
date: 2026-07-07
updated: 2026-07-07
confidence: gap_backlog
skill_id: "__missing_microbiome_qiime2_abundance_skill__"
quality_score: 0
registry_gap_status: "missing_skill"
---

# Microbiome QIIME2 differential abundance

## 缺口定位
- Gap ID：`__missing_microbiome_qiime2_abundance_skill__`
- 状态：`missing_skill`
- 期望行为：Recommend a microbiome differential-abundance skill for QIIME2/ANCOM/LEfSe/ALDEx2 workflows when available; avoid RNA-seq differential-expression or clinical differential-diagnosis false positives.

## 用户结论
- 当前 registry 还没有可安装的对应技能；这里命中的是缺口记录，不是推荐安装项。
- 如果检索结果同时出现弱相关技能，应优先把它们理解为候选参考，而不是已验证替代方案。

## 查询样例
- `microbiome differential abundance qiime2`
- `QIIME2 ANCOM differential abundance microbiome`
- `microbiome LEfSe ALDEx2 differential abundance`

## 关联 holdout
- `holdout_find_microbiome_qiime2_abundance`
- `holdout_wiki_microbiome_qiime2_abundance`

## 维护口径
- 这是 registry gap，不是可安装技能。
- 补真技能时，需要覆盖查询样例里的核心任务，并能解释为什么旧的弱相关命中不再应排在前面。
- 只有补入真实技能或注册表数据后，才应把相关 holdout 期望替换为真实 skill id。
