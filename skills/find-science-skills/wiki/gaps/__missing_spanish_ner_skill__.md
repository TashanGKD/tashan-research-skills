---
title: "Spanish named entity recognition"
type: skill_gap
tags: ["registry-gap", "missing_skill"]
date: 2026-07-07
updated: 2026-07-07
confidence: gap_backlog
skill_id: "__missing_spanish_ner_skill__"
quality_score: 0
registry_gap_status: "missing_skill"
---

# Spanish named entity recognition

## 缺口定位
- Gap ID：`__missing_spanish_ner_skill__`
- 状态：`missing_skill`
- 期望行为：Recommend a Spanish NER / multilingual information-extraction skill when available; avoid Spanish grant-writing or generic literature-search false positives.

## 用户结论
- 当前 registry 还没有可安装的对应技能；这里命中的是缺口记录，不是推荐安装项。
- 如果检索结果同时出现弱相关技能，应优先把它们理解为候选参考，而不是已验证替代方案。

## 问题说明
- 用户会看到的问题：A user asking for Spanish NER needs entity extraction from Spanish text, not grant-writing in Spanish.
- 为什么不是现有弱相关技能：
  - Spanish grant-writing skills share the language token but solve a writing task, not NER.
  - Generic literature search or document parsing does not provide named-entity tagging for Spanish text.
- 补真技能验收标准：
  - Supports Spanish or multilingual NER model selection and inference.
  - Defines entity labels, evaluation metrics, and input/output format.
  - Handles biomedical or general-domain Spanish text when the query specifies the domain.

## 查询样例
- `西班牙语 命名实体识别`
- `Spanish named entity recognition`
- `NER para textos en español`

## 关联 holdout
- `holdout_find_spanish_ner`
- `holdout_wiki_spanish_ner`

## 维护口径
- 这是 registry gap，不是可安装技能。
- 补真技能时，需要覆盖查询样例里的核心任务，并能解释为什么旧的弱相关命中不再应排在前面。
- 只有补入真实技能或注册表数据后，才应把相关 holdout 期望替换为真实 skill id。
