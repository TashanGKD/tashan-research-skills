---
title: "awq-quantization"
type: skill
tags: ["建模仿真", "大模型与智能体", "C"]
date: 2026-07-07
updated: 2026-07-07
confidence: well_sourced
skill_id: "awq-quantization"
quality_score: 54
tier: C
needs_review: false
source_repo: "Orchestra-Research/AI-Research-SKILLs"
source_path: "10-optimization/awq/SKILL.md"
---

# awq-quantization
## 一句话定位
[来源] Activation-aware weight quantization for 4-bit LLM compression with 3x speedup and minimal accuracy loss. Use when deploying large models (7B-70B) on limited GPU memory, when you need faster inference than GPTQ with better accuracy preservation, or for instruc

## 检索线索
- 能力组：建模仿真
- 功能家族：执行实验
- 学科：AI与计算机 / 大模型与智能体
- 中文关键词：AWQ量化, 激活感知权重量化, 4位大语言模型压缩, LLM推理加速, GPU内存受限部署, 7B-70B大模型量化, 权重量化, 推理速度优化, 精度保持量化, 大语言模型压缩

## 质量信号
| 指标 | 值 |
| --- | --- |
| 质量分 | 54 |
| Tier | C |
| 深评 | 未深评 |
| 来源仓库数 | 1 |
| stars | 10390 |
| 待复核 | 否 |

## 获取方式
- 仓库：`Orchestra-Research/AI-Research-SKILLs`
- 路径：`10-optimization/awq/SKILL.md`

## 图关系
- 可替代：[[skills/gptq]] (0.633)、[[skills/quantizing-models-bitsandbytes]] (0.423)、[[skills/model-pruning]] (0.403)、[[skills/peft-fine-tuning]] (0.398)、[[skills/slime-rl-training]] (0.183)、[[skills/distributed-llm-pretraining-torchtitan]] (0.180)、[[skills/training-llms-megatron]] (0.175)、[[skills/pytorch-fsdp2]] (0.160)
- 配套：[[skills/nemo-curator]]、[[skills/deepspeed]]、[[skills/ray-data]]、[[skills/crewai-multi-agent]]、[[skills/training-llms-megatron]]、[[skills/evaluating-code-models]]、[[skills/ray-train]]、[[skills/huggingface-accelerate]]
- 下一步：[[skills/experiment-provenance]] (0.127)
- 相关：[[skills/conversation-memory]] (0.222)、[[skills/simpo-training]] (0.216)、[[skills/crewai-multi-agent]] (0.216)、[[skills/optimizing-attention-flash]] (0.216)、[[skills/skill]] (0.209)、[[skills/auto-review-loop-llm]] (0.194)、[[skills/langsmith-observability]] (0.179)、[[skills/evaluating-cosmos-policy]] (0.168)

## 反向链接
- [[skills/training-llms-megatron]]（可替代 (0.175)）
- [[skills/conversation-memory]]（相关 (0.222)）
- [[skills/model-pruning]]（可替代 (0.403)）
- [[skills/distributed-llm-pretraining-torchtitan]]（可替代 (0.180)）
- [[skills/simpo-training]]（相关 (0.216)）
- [[skills/slime-rl-training]]（可替代 (0.183)）
- [[skills/peft-fine-tuning]]（可替代 (0.398)）
- [[skills/pytorch-fsdp2]]（可替代 (0.160)）
- [[skills/quantizing-models-bitsandbytes]]（可替代 (0.423)）
- [[skills/optimizing-attention-flash]]（相关 (0.216)）
- [[skills/gptq]]（可替代 (0.633)）
