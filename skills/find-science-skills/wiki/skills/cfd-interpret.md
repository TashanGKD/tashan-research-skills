---
title: "cfd-interpret"
type: skill
tags: ["建模仿真", "计算机视觉", "C"]
date: 2026-07-07
updated: 2026-07-07
confidence: draft
skill_id: "cfd-interpret"
quality_score: 50
tier: C
needs_review: true
source_repo: "csml-rpi/AI-CFD-Scientist"
source_path: "cfd-skills/cfd-interpret/SKILL.md"
---

# cfd-interpret
## 一句话定位
[来源] Per-case decision agent — PROCEED, REVISE, or RERUN. Reads run_result.json + diagnostic figures, judges physics plausibility through a vision-LLM pass, returns decision.json. Self-contained — embeds ResultsInterpreterAgent.interpretation_* and vision_* prompts

## 检索线索
- 能力组：建模仿真
- 功能家族：执行实验
- 学科：AI与计算机 / 计算机视觉
- 中文关键词：CFD仿真结果判读, vision-LLM, run_result.json, 诊断图像分析, 物理合理性判断, 决策代理, PROCEED_REVISE_RERUN, cfd-interpret, 建模仿真, AI判读, 计算流体力学

## 质量信号
| 指标 | 值 |
| --- | --- |
| 质量分 | 50 |
| Tier | C |
| 深评 | 未深评 |
| 来源仓库数 | 1 |
| stars | 31 |
| 待复核 | 是 |

## 获取方式
- 仓库：`csml-rpi/AI-CFD-Scientist`
- 路径：`cfd-skills/cfd-interpret/SKILL.md`

## 图关系
- 可替代：[[skills/cfd-viz]] (0.466)、[[skills/openfoam-agent]] (0.280)、[[skills/cfd-cross-analyze]] (0.265)、[[skills/linear-solvers]] (0.259)、[[skills/numerical-stability]] (0.259)、[[skills/numerical-integration]] (0.259)、[[skills/nonlinear-solvers]] (0.259)、[[skills/mesh-generation]] (0.259)
- 配套：[[skills/cfd-paper-writer]]、[[skills/cfd-mesh-gate]]、[[skills/cfd-code-mod]]、[[skills/cfd-viz]]、[[skills/cfd-experiment]]、[[skills/cfd-mesh-independence]]、[[skills/cfd-research]]、[[skills/cfd-pipeline]]
- 下一步：[[skills/image-analysis]] (0.223)、[[skills/data-anomaly-detection]] (0.203)
- 相关：[[skills/fair-simulation-packager]] (0.259)、[[skills/simulation-failure-triage]] (0.259)、[[skills/performance-profiling]] (0.259)、[[skills/parameter-optimization]] (0.259)、[[skills/differentiation-schemes]] (0.259)、[[skills/time-stepping]] (0.259)、[[skills/md-analysis-planner]] (0.259)、[[skills/convergence-study]] (0.259)

## 反向链接
- [[skills/cfd-cross-analyze]]（可替代 (0.265)）
- [[skills/drug-pocket-detection]]（可替代 (0.199)）
- [[skills/cfd-viz]]（可替代 (0.466)）
- [[skills/cfd-analyze]]（可替代 (0.254)）
- [[skills/cfd-paper]]（可替代 (0.208)）
