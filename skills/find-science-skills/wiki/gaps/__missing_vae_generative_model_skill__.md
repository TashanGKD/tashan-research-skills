---
title: "Variational autoencoder generative modeling"
type: skill_gap
tags: ["registry-gap", "missing_skill"]
date: 2026-07-07
updated: 2026-07-07
confidence: gap_backlog
skill_id: "__missing_vae_generative_model_skill__"
quality_score: 0
registry_gap_status: "missing_skill"
---

# Variational autoencoder generative modeling

## 缺口定位
- Gap ID：`__missing_vae_generative_model_skill__`
- 状态：`missing_skill`
- 期望行为：Recommend a VAE/generative-modeling skill when available; avoid sparse-autoencoder interpretability, BLIP vision-language, or code-model evaluation false positives.

## 用户结论
- 当前 registry 还没有可安装的对应技能；这里命中的是缺口记录，不是推荐安装项。
- 如果检索结果同时出现弱相关技能，应优先把它们理解为候选参考，而不是已验证替代方案。

## 问题说明
- 用户会看到的问题：A user asking for VAE generative modeling needs latent-variable model design/training/evaluation, not sparse autoencoder interpretability or unrelated multimodal model pages.
- 为什么不是现有弱相关技能：
  - Sparse autoencoders in mechanistic interpretability are not variational autoencoders for generative modeling.
  - BLIP-style vision-language pages and code-model evaluation do not teach or run VAE training.
- 补真技能验收标准：
  - Covers encoder/decoder, latent distribution, KL term, reconstruction loss, and sampling.
  - Supports VAE training or experiment setup for images, tabular data, or scientific latent models.
  - Reports model diagnostics such as reconstruction quality, latent traversal, and posterior collapse risks.

## 查询样例
- `变分自编码器 生成模型`
- `variational autoencoder VAE generative model`
- `VAE latent generative modeling`

## 关联 holdout
- `holdout_find_vae_generative_model`
- `holdout_wiki_vae_generative_model`

## 维护口径
- 这是 registry gap，不是可安装技能。
- 补真技能时，需要覆盖查询样例里的核心任务，并能解释为什么旧的弱相关命中不再应排在前面。
- 只有补入真实技能或注册表数据后，才应把相关 holdout 期望替换为真实 skill id。
