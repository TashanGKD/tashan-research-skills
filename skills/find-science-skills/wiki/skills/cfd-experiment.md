---
title: "cfd-experiment"
type: skill
tags: ["建模仿真", "计算工程与流体仿真", "C"]
date: 2026-07-07
updated: 2026-07-07
confidence: well_sourced
skill_id: "cfd-experiment"
quality_score: 59
tier: C
needs_review: false
source_repo: "csml-rpi/AI-CFD-Scientist"
source_path: "cfd-skills/cfd-experiment/SKILL.md"
---

# cfd-experiment
## 一句话定位
[来源] Run CFD cases. Two modes — sweep (ARIS-style, agent-driven, no FoamAgent handoff) for parameter variants on a known-good baseline; single-case (FoamAgent-driven via scripts/foam_run.py) for fresh case generation that needs RAG. Embeds RunValidityAgent prompts

## 检索线索
- 能力组：建模仿真
- 功能家族：执行实验
- 学科：工程与环境 / 计算工程与流体仿真
- 中文关键词：CFD仿真, 参数扫描, ARIS, FoamAgent, foam_run.py, RAG, RunValidityAgent, 流体力学建模, 工程仿真, 计算流体力学

## 质量信号
| 指标 | 值 |
| --- | --- |
| 质量分 | 59 |
| Tier | C |
| 深评 | 未深评 |
| 来源仓库数 | 1 |
| stars | 31 |
| 待复核 | 否 |

## 获取方式
- 仓库：`csml-rpi/AI-CFD-Scientist`
- 路径：`cfd-skills/cfd-experiment/SKILL.md`

## 图关系
- 可替代：[[skills/cfd-foamagent-runtime]] (0.431)、[[skills/cfd-open-discovery]] (0.369)、[[skills/openfoam-agent]] (0.369)、[[skills/cfd-foamagent]] (0.325)、[[skills/slurm-job-script-generator]] (0.320)、[[skills/cfd-hypothesis]] (0.311)、[[skills/cfd-mesh-independence]] (0.307)、[[skills/simulation-orchestrator]] (0.291)
- 配套：[[skills/cfd-paper-writer]]、[[skills/cfd-mesh-gate]]、[[skills/cfd-code-mod]]、[[skills/cfd-viz]]、[[skills/cfd-mesh-independence]]、[[skills/cfd-research]]、[[skills/cfd-pipeline]]、[[skills/cfd-paper]]
- 相关：[[skills/workflow-engine-mapper]] (0.291)、[[skills/convergence-test]] (0.279)、[[skills/numerical-integration]] (0.277)、[[skills/parameter-optimization]] (0.277)、[[skills/nonlinear-solvers]] (0.277)、[[skills/linear-solvers]] (0.277)、[[skills/simulation-failure-triage]] (0.277)、[[skills/differentiation-schemes]] (0.277)

## 反向链接
- [[skills/cfd-cross-analyze]]（配套）
- [[skills/cfd-open-discovery]]（可替代 (0.369)）
- [[skills/cfd-open-discovery]]（配套）
- [[skills/cfd-mesh-gate]]（配套）
- [[skills/cfd-code-modify]]（配套）
- [[skills/cfd-hypothesis]]（配套）
- [[skills/cfd-hypothesis]]（相关 (0.311)）
- [[skills/cfd-pipeline]]（配套）
- [[skills/cfd-requirements]]（配套）
- [[skills/cfd-code-mod]]（配套）
- [[skills/cfd-foamagent-runtime]]（可替代 (0.431)）
- [[skills/cfd-foamagent-runtime]]（配套）
