---
title: "mamba-architecture"
type: skill
tags: ["建模仿真", "实验仪器与自动化", "C"]
date: 2026-07-07
updated: 2026-07-07
confidence: well_sourced
skill_id: "mamba-architecture"
quality_score: 53
tier: C
needs_review: false
source_repo: "Orchestra-Research/AI-Research-SKILLs"
source_path: "01-model-architecture/mamba/SKILL.md"
---

# mamba-architecture
## 一句话定位
[来源] State-space model with O(n) complexity vs Transformers' O(n²). 5× faster inference, million-token sequences, no KV cache. Selective SSM with hardware-aware design. Mamba-1 (d_state=16) and Mamba-2 (d_state=128, multi-head). Models 130M-2.8B on HuggingFace.

## 检索线索
- 能力组：建模仿真
- 功能家族：执行实验
- 学科：工程与环境 / 实验仪器与自动化
- 中文关键词：Mamba架构, 状态空间模型, SSM, Selective SSM, 硬件感知设计, Mamba-1, Mamba-2, HuggingFace, 工程建模, 环境建模

## 质量信号
| 指标 | 值 |
| --- | --- |
| 质量分 | 53 |
| Tier | C |
| 深评 | 未深评 |
| 来源仓库数 | 1 |
| stars | 10390 |
| 待复核 | 否 |

## 获取方式
- 仓库：`Orchestra-Research/AI-Research-SKILLs`
- 路径：`01-model-architecture/mamba/SKILL.md`

## 图关系
- 可替代：[[skills/rwkv-architecture]] (0.201)、[[skills/model-pruning]] (0.199)、[[skills/gptq]] (0.184)
- 配套：[[skills/nemo-curator]]、[[skills/deepspeed]]、[[skills/ray-data]]、[[skills/crewai-multi-agent]]、[[skills/training-llms-megatron]]、[[skills/evaluating-code-models]]、[[skills/ray-train]]、[[skills/huggingface-accelerate]]
- 下一步：[[skills/labarchive-integration]] (0.194)、[[skills/tooluniverse-dataset-discovery]] (0.139)
- 相关：[[skills/ur5e-arm]] (0.310)、[[skills/search-papers]] (0.300)、[[skills/usb-camera]] (0.298)、[[skills/lab-automation-test-pylabrobot-script]] (0.281)、[[skills/research-advisor]] (0.269)、[[skills/verify-citations]] (0.252)、[[skills/opentrons-protocol-gen]] (0.237)、[[skills/benchling-integration]] (0.233)

## 反向链接
- [[skills/opentrons-protocol-api]]（相关 (0.218)）
- [[skills/opentrons-protocol-gen]]（相关 (0.237)）
- [[skills/benchling-integration]]（相关 (0.233)）
- [[skills/model-pruning]]（可替代 (0.199)）
- [[skills/moe-training]]（相关 (0.194)）
- [[skills/rwkv-architecture]]（可替代 (0.201)）
- [[skills/gptq]]（可替代 (0.184)）
- [[skills/ur5e-arm]]（相关 (0.310)）
- [[skills/usb-camera]]（相关 (0.298)）
- [[skills/lab-automation-test-pylabrobot-script]]（相关 (0.281)）
