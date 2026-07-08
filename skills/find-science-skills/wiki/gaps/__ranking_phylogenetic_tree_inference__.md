---
title: "Phylogenetic tree inference ranking"
type: skill_gap
tags: ["registry-gap", "ranking_gap"]
date: 2026-07-07
updated: 2026-07-07
confidence: gap_backlog
skill_id: "__ranking_phylogenetic_tree_inference__"
quality_score: 0
registry_gap_status: "ranking_gap"
---

# Phylogenetic tree inference ranking

## 缺口定位
- Gap ID：`__ranking_phylogenetic_tree_inference__`
- 状态：`ranking_gap`
- 期望行为：Prefer phylogenetics/ETE toolkit skills for evolutionary tree inference; avoid decision-tree machine-learning false positives caused by the token tree.

## 用户结论
- 当前 registry 还没有可安装的对应技能；这里命中的是缺口记录，不是推荐安装项。
- 如果检索结果同时出现弱相关技能，应优先把它们理解为候选参考，而不是已验证替代方案。

## 问题说明
- 用户会看到的问题：A user asking for phylogenetic tree inference wants evolutionary/bioinformatics tree construction, not decision-tree classification or generic statistical inference.
- 为什么不是现有弱相关技能：
  - Decision-tree analysis is a machine-learning model and does not infer evolutionary or taxonomic phylogenies.
  - Generic computational-inference pages match the word inference but do not provide phylogenetic tree workflows.
- 补真技能验收标准：
  - Ranks etetoolkit or phylogenetics ahead of decision-tree-analysis for phylogenetic tree queries.
  - Explains that tree means evolutionary phylogeny in this context, not ML decision trees.
  - Keeps biology-specific tree reconstruction terms such as phylogeny, phylogenetic, clade, and ETE together.

## 查询样例
- `phylogenetic tree inference`
- `系统发育树 推断 构建`
- `phylogeny tree reconstruction`

## 关联 holdout
- `holdout_find_phylogenetic_tree_inference`
- `holdout_wiki_phylogenetic_tree_inference`

## 维护口径
- 这是 registry gap，不是可安装技能。
- 补真技能时，需要覆盖查询样例里的核心任务，并能解释为什么旧的弱相关命中不再应排在前面。
- 只有补入真实技能或注册表数据后，才应把相关 holdout 期望替换为真实 skill id。
