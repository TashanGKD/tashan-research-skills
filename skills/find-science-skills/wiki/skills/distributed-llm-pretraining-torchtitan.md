---
title: "distributed-llm-pretraining-torchtitan"
type: skill
tags: ["建模仿真", "大模型与智能体", "C"]
date: 2026-07-07
updated: 2026-07-07
confidence: well_sourced
skill_id: "distributed-llm-pretraining-torchtitan"
quality_score: 53
tier: C
needs_review: false
source_repo: "Orchestra-Research/AI-Research-SKILLs"
source_path: "01-model-architecture/torchtitan/SKILL.md"
---

# distributed-llm-pretraining-torchtitan
## 一句话定位
[来源] Provides PyTorch-native distributed LLM pretraining using torchtitan with 4D parallelism (FSDP2, TP, PP, CP). Use when pretraining Llama 3.1, DeepSeek V3, or custom models at scale from 8 to 512+ GPUs with Float8, torch.compile, and distributed checkpointing.

## 检索线索
- 能力组：建模仿真
- 功能家族：执行实验
- 学科：AI与计算机 / 大模型与智能体
- 中文关键词：分布式大语言模型预训练, torchtitan, PyTorch, FSDP2, 张量并行, 流水线并行, 上下文并行, Float8, torch.compile, 分布式检查点, Llama 3.1, DeepSeek V3

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
- 路径：`01-model-architecture/torchtitan/SKILL.md`

## 图关系
- 可替代：[[skills/pytorch-fsdp2]] (0.311)、[[skills/verl-rl-training]] (0.272)、[[skills/slime-rl-training]] (0.265)、[[skills/model-pruning]] (0.218)、[[skills/meta-apply]] (0.188)、[[skills/awq-quantization]] (0.180)
- 配套：[[skills/nemo-curator]]、[[skills/deepspeed]]、[[skills/ray-data]]、[[skills/crewai-multi-agent]]、[[skills/training-llms-megatron]]、[[skills/evaluating-code-models]]、[[skills/ray-train]]、[[skills/huggingface-accelerate]]
- 下一步：[[skills/experiment-provenance]] (0.135)
- 相关：[[skills/skill]] (0.239)、[[skills/auto-review-loop-llm]] (0.233)、[[skills/dask]] (0.195)、[[skills/langsmith-observability]] (0.185)、[[skills/research-add-fields]] (0.180)、[[skills/huggingface-accelerate]] (0.169)、[[skills/research-add-items]] (0.168)、[[skills/torchforge-rl-training]] (0.166)

## 反向链接
- [[skills/dask]]（相关 (0.195)）
- [[skills/huggingface-accelerate]]（相关 (0.169)）
- [[skills/model-pruning]]（可替代 (0.218)）
- [[skills/auto-review-loop-llm]]（相关 (0.233)）
- [[skills/meta-apply]]（可替代 (0.188)）
- [[skills/slime-rl-training]]（可替代 (0.265)）
- [[skills/verl-rl-training]]（可替代 (0.272)）
- [[skills/awq-quantization]]（可替代 (0.180)）
- [[skills/pytorch-fsdp2]]（可替代 (0.311)）
- [[skills/torchforge-rl-training]]（相关 (0.166)）
