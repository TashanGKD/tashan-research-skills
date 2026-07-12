---
name: find-science-skills
description: Use when a user asks which research, academic, experimental, simulation, analysis, writing, or publication skill is available for a scientific task.
---

# Find Science Skills

把用户需求判断为“领域 × 研究阶段 × 功能分工”，再调用静态目录筛选器。宿主模型负责理解需求；脚本执行确定性漏斗：领域和阶段是硬边界，功能默认作为排序偏好，避免复合任务因功能判断偏差而漏掉正确技能。

## 工作流

1. 首次使用或不确定合法分类时，读取分类目录：

```bash
python scripts/filter_science_skills.py --list-dimensions
```

2. 先判断领域和阶段，再查看该漏斗中实际存在的功能组：

```bash
python scripts/filter_science_skills.py \
  --domain 生命科学 \
  --stage 分析验证 \
  --list-functions
```

3. 只从返回的实际功能组中选择。结合用户需求和代表技能判断主功能与合理的次功能：

- **领域**：研究对象所属领域；必要时再选二级领域。
- **研究阶段**：发现获取、构思设计、执行采集、分析验证、表达发表。
- **功能分工**：检索获取、阅读提取、证据综合、问题构思、研究设计、流程规划、模拟建模、实验执行、数据采集、数据处理、分析推断、领域解释、验证评测、可视化、科研写作、引用管理、投稿评审。

4. 确信主/次功能后使用严格筛选，避免候选过多。多选参数可重复，也可用逗号分隔：

```bash
python scripts/filter_science_skills.py \
  --domain 生命科学 \
  --stage 分析验证 \
  --function 数据处理 \
  --strict-function \
  --json
```

若功能边界仍不确定，去掉 `--strict-function`。脚本会保留同领域、同阶段候选，并把所选功能排在前面：

```bash
python scripts/filter_science_skills.py \
  --domain 生命科学 \
  --stage 分析验证 \
  --function 数据处理 \
  --json
```

大组可增加二级领域：

```bash
python scripts/filter_science_skills.py \
  --domain 生命科学 \
  --subdomain 生物信息学 \
  --stage 分析验证 \
  --function 数据处理 \
  --json
```

5. 对候选做语义复核，不把脚本顺序当成相关性排名：

   - 研究对象或数据类型必须直接匹配 `summary` 或 `task`；
   - 请求的动作或产物也必须直接匹配；
   - 两类证据缺一不可；最多推荐 5 个；
   - 没有直接匹配时返回“目录未覆盖”或追问，不得用高质量但无关的技能补位。

   `--json` 默认保留语义选择所需字段；审计目录时可增加 `--full`。不要为某条查询或某个 skill ID 添加特殊规则。

6. 需要进一步筛查候选质量时，可显式加载 CriticAgent 评分旁车：

```bash
python scripts/filter_science_skills.py \
  --domain 生命科学 \
  --stage 分析验证 \
  --function 数据处理 \
  --critic-scorecard data/science_skill_critic_scores.json \
  --min-source-review-score 80 \
  --critic-require-full-source \
  --critic-require-package-pass \
  --json
```

   额外证据默认不参与检索和排序。`model_source_review_score` 只表示模型对完整源码的内容评审，不是安装推荐；`metadata_only` 记录的该字段为 `null`，状态为 `unverified`。`static_validation_status`、`behavior_evaluation` 和 `trigger_evaluation` 分层保存，只有三层都通过时 `install_recommendation` 才可能为 `recommend_install`。

## 判断规则

- 不确定时选择多个合法功能。默认由领域和阶段限定候选，功能只决定优先顺序。
- 不要选择当前领域和阶段下未返回的功能；需要的动作若未出现，检查相邻的实际功能组或向用户追问。
- 研究阶段按主要产物判断，不按工具名称判断。
- 功能按主要动作判断；agent、API、工具库和 workflow 只是实现形式。
- `trusted` 优先；`provisional` 需要核对来源；`restricted` 必须明确警示。可信度和质量分只用于直接匹配候选之间的排序，不证明语义相关。
- 模型源码评审分只用于用户显式要求的二次筛选；它不能代表安装推荐，不能把语义不相关的技能提升为候选，也不能覆盖 `restricted` 警告。
- 默认模式仍无结果时，说明领域或阶段没有覆盖，向用户追问；不要推荐跨领域或跨阶段的相似项。

## 回复用户

先说明识别出的领域、阶段和功能，再列出最多 5 个直接匹配技能。每项至少包含：技能名、匹配证据、主要用途、可信状态、来源仓库和 `SKILL.md` 路径。没有直接匹配时明确说明缺口。结果较多时按二级领域、数据类型和工具约束继续筛选，但不要修改目录规则。

## 文件

- `data/science_skill_catalog.json`：规范化静态目录，字段为 `domain`、`subdomain`、`stage`、`function`。
- `scripts/filter_science_skills.py`：确定性三维筛选器，仅依赖 Python 标准库。
- `data/science_skill_critic_scores.json`：可选 CriticAgent 分层证据旁车，区分源码评审、静态检查、行为测试、触发测试和安装建议。
- `scripts/score_science_skills.py`：可恢复源码评审器；密钥只从 `ARK_API_KEY` 读取，不写入评分文件。
- `scripts/finalize_critic_scores.py`：把模型评审结果确定性迁移为不可混淆的 v2 分层证据。
- `scripts/apply_critic_evaluation.py`：校验源码哈希和静态状态后写入行为/触发证据；未运行正式 CriticAgent 内核的复核不会升级为安装推荐。
- `data/critic_evaluations/`：逐技能保存可追溯的行为与触发测试报告。
