---
title: "drug-mmpbsa-gbsa"
type: skill
tags: ["建模仿真", "药物发现", "C"]
date: 2026-07-07
updated: 2026-07-07
confidence: well_sourced
skill_id: "drug-mmpbsa-gbsa"
quality_score: 64
tier: C
needs_review: false
source_repo: "learningmatter-mit/AtomisticSkills"
source_path: ".agents/skills/drug-mmpbsa-gbsa/SKILL.md"
---

# drug-mmpbsa-gbsa
## 一句话定位
[来源] Compute single-trajectory MM-GBSA and / or MM-PBSA binding free energy estimates from a protein-ligand MD trajectory. Two backends: a fast OpenMM GBn2 path (no extra dependencies) and an AmberTools MMPBSA.py path that supports both GB (multiple igb models) and Poisson-Boltzmann PB on the same trajec

## 检索线索
- 能力组：建模仿真
- 功能家族：执行实验
- 学科：化学与药物 / 药物发现
- 中文关键词：MM-GBSA, MM-PBSA, 结合自由能, 分子动力学轨迹, OpenMM, AmberTools, MMPBSA.py, GBn2, igb模型, 泊松-玻尔兹曼, PB, 药物设计

## 质量信号
| 指标 | 值 |
| --- | --- |
| 质量分 | 64 |
| Tier | C |
| 深评 | 未深评 |
| 来源仓库数 | 1 |
| stars | 126 |
| 待复核 | 否 |

## 获取方式
- 仓库：`learningmatter-mit/AtomisticSkills`
- 路径：`.agents/skills/drug-mmpbsa-gbsa/SKILL.md`

## 图关系
- 可替代：[[skills/drug-admet-prediction]] (0.298)、[[skills/drug-complex-system-builder]] (0.284)、[[skills/drug-protein-ligand-md]] (0.215)、[[skills/foldseek-structural-search]] (0.210)、[[skills/diffdock]] (0.186)、[[skills/comparative-network-toxicology-shared-mechanism-reference-grounded]] (0.185)、[[skills/chem-thermochemistry]] (0.184)、[[skills/drug-pose-validation]] (0.166)
- 配套：[[skills/chem-dft-orca-advanced-calculation]]、[[skills/chem-nmr-analysis]]、[[skills/chem-spectrum-matcher]]、[[skills/chem-db-qmof]]、[[skills/drug-protein-ligand-md]]、[[skills/chem-solution-md]]、[[skills/chem-dft-orca-singlepoint]]、[[skills/drug-binding-site-definition]]
- 下一步：[[skills/tooluniverse-cell-line-profiling]] (0.137)
- 相关：[[skills/medicare-drug-stats]] (0.328)、[[skills/agentd-drug-discovery]] (0.282)、[[skills/drug-interaction-checker]] (0.279)、[[skills/pediatric-drug-dosing]] (0.255)、[[skills/fda-drug-information]] (0.247)、[[skills/bids]] (0.237)、[[skills/binding-characterization]] (0.227)、[[skills/tooluniverse-drug-synergy]] (0.209)

## 反向链接
- [[skills/bio-admet-prediction]]（相关 (0.204)）
- [[skills/drug-admet-prediction]]（可替代 (0.298)）
- [[skills/drug-binding-site-definition]]（可替代 (0.161)）
- [[skills/drug-complex-system-builder]]（可替代 (0.284)）
- [[skills/drug-pose-validation]]（可替代 (0.166)）
- [[skills/drug-interaction-checker]]（相关 (0.279)）
- [[skills/medicare-drug-stats]]（相关 (0.328)）
- [[skills/pediatric-drug-dosing]]（相关 (0.255)）
- [[skills/cross-disease-shared-biomarker-network-research-planner]]（相关 (0.182)）
- [[skills/bio-atac-seq-footprinting]]（相关 (0.186)）
- [[skills/binding-characterization]]（相关 (0.227)）
- [[skills/tooluniverse-drug-synergy]]（相关 (0.209)）
