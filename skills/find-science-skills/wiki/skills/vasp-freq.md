---
title: "vasp-freq"
type: skill
tags: ["建模仿真", "计算材料", "C"]
date: 2026-07-07
updated: 2026-07-07
confidence: well_sourced
skill_id: "vasp-freq"
quality_score: 64
tier: C
needs_review: false
source_repo: "Hello-QM/catgo-LRG"
source_path: "server/catgo/workflow/skills/vasp/freq/SKILL.md"
---

# vasp-freq
## 一句话定位
[来源] VASP vibrational frequency calculation. Compute ZPE and thermodynamic corrections. Handles frozen atoms for slab systems with multiple freeze modes.

## 检索线索
- 能力组：建模仿真
- 功能家族：执行实验
- 学科：材料科学 / 计算材料
- 中文关键词：VASP, 振动频率计算, 零点能, ZPE, 热力学修正, slab模型, 冻结原子, 材料模拟

## 质量信号
| 指标 | 值 |
| --- | --- |
| 质量分 | 64 |
| Tier | C |
| 深评 | 未深评 |
| 来源仓库数 | 1 |
| stars | 152 |
| 待复核 | 否 |

## 获取方式
- 仓库：`Hello-QM/catgo-LRG`
- 路径：`server/catgo/workflow/skills/vasp/freq/SKILL.md`

## 图关系
- 可替代：[[skills/gibbs-free-energy]] (0.458)、[[skills/cp2k-geo-opt]] (0.456)、[[skills/numerical-integration]] (0.446)、[[skills/numerical-stability]] (0.446)、[[skills/linear-solvers]] (0.446)、[[skills/mesh-generation]] (0.446)、[[skills/md-analysis-planner]] (0.446)、[[skills/time-stepping]] (0.446)
- 配套：[[skills/convergence-test]]、[[skills/quantum-espresso]]、[[skills/dftbplus]]、[[skills/cohp-analysis]]、[[skills/nrr-overpotential]]、[[skills/lammps-deepmd]]、[[skills/cp2k-geo-opt]]、[[skills/reacnetgenerator]]
- 下一步：[[skills/cohp-analysis]] (0.198)、[[skills/hpc-calculix]] (0.178)、[[skills/bader-charge-analysis]] (0.176)、[[skills/dos-analysis]] (0.153)
- 相关：[[skills/performance-profiling]] (0.446)、[[skills/parameter-optimization]] (0.446)、[[skills/simulation-validator]] (0.446)、[[skills/nonlinear-solvers]] (0.446)、[[skills/convergence-study]] (0.446)、[[skills/differentiation-schemes]] (0.446)、[[skills/simulation-failure-triage]] (0.446)、[[skills/fair-simulation-packager]] (0.446)

## 反向链接
- [[skills/chem-thermochemistry]]（可替代 (0.206)）
- [[skills/cp2k-geo-opt]]（可替代 (0.456)）
- [[skills/cp2k-geo-opt]]（配套）
- [[skills/lammps-deepmd]]（配套）
- [[skills/nrr-overpotential]]（配套）
