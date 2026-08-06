---
name: find-science-skills
description: Use when a user asks which research Skill, MCP service, academic workflow, experimental tool, simulation capability, analysis resource, writing aid, or publication resource is available for a scientific task.
---

# Find Science Skill / MCP

把用户需求判断为“资源类型 × 领域 × 研究阶段 × 功能分工”，再调用静态目录筛选器。资源类型可选 `skill`、`mcp` 或 `all`；默认只查找 Skill，明确要求 MCP 时查 MCP，明确要求两者时才同时查找。宿主模型负责理解需求，脚本只做确定性分类过滤，不需要后端服务或 API 密钥。

## 工作流

1. 首次使用或不确定合法分类时，读取分类与资源数量：

```bash
python scripts/filter_science_resources.py --list-dimensions
```

2. 判断用户要找 Skill、MCP，还是两者都可以：

- 用户明确说“技能”“方法”“工作流”时使用 `--resource skill`。
- 用户明确说“MCP”“服务”“可连接工具”时使用 `--resource mcp`。
- 用户明确说“Skill 和 MCP”“两类资源”“都找”时使用 `--resource all`。
- 用户只描述科研任务、没有指定资源类型时使用默认的 `--resource skill`。

3. 先判断领域和阶段，再查看该漏斗中实际存在的功能组：

```bash
python scripts/filter_science_resources.py \
  --domain 生命科学 \
  --stage 分析验证 \
  --list-functions
```

分类固定为：

- **领域**：9 个一级领域和 42 个二级领域，以目录返回值为准。
- **研究阶段**：发现获取、构思设计、执行采集、分析验证、表达发表。
- **功能分工**：检索获取、阅读提取、证据综合、问题构思、研究设计、流程规划、模拟建模、实验执行、数据采集、数据处理、分析推断、领域解释、验证评测、可视化、科研写作、引用管理、投稿评审。

4. 确信主功能后使用严格筛选。多选参数可重复，也可用逗号分隔：

```bash
python scripts/filter_science_resources.py \
  --resource mcp \
  --domain 生命科学 \
  --subdomain 生物信息学 \
  --stage 分析验证 \
  --function 数据处理 \
  --strict-function \
  --json
```

若功能边界仍不确定，去掉 `--strict-function`。脚本会保留同领域、同阶段候选，并把所选功能排在前面。

5. 对候选做语义复核，不把脚本顺序当成相关性排名：

   - 研究对象或数据类型必须直接匹配 `summary` 或 `task`；
   - 请求的动作或产物也必须直接匹配；
   - 两类证据缺一不可；最多推荐 5 项；
   - 没有直接匹配时返回“目录未覆盖”或追问，不得用高分但无关的资源补位。

`--json` 默认保留语义选择所需字段；审计目录时可增加 `--full`。不要为某条查询或某个资源 ID 添加特殊规则。

## 判断规则

- 研究阶段按主要产物判断，功能按主要动作判断；agent、API、工具库和 workflow 只是实现形式。
- 不要选择当前领域和阶段下未返回的功能。需要的动作未出现时，检查相邻的实际功能组或向用户追问。
- `trusted` 优先；`provisional` 需要核对来源；`restricted` 必须明确警示。可信状态和质量分只用于直接匹配候选之间的排序，不证明语义相关。
- MCP 的目录记录只证明身份、科研适配和来源信息，不证明已经安装、可连接、运行可靠、安全或科研结论正确。
- `--resource all` 必须保留每项的 `resource_type`，分别呈现 Skill 路径和 MCP canonical URL，不要把两类资源混成同一种能力。
- 安装命令、传输方式、许可证等字段为空时直接说明“目录未记录”，不要猜测。
- 默认模式仍无结果时，说明领域或阶段没有覆盖，不要推荐跨领域或跨阶段的相似项。

## 回复用户

先说明识别出的资源类型、领域、阶段和功能，再列出最多 5 个直接匹配项。每项至少包含：

- 资源类型（Skill 或 MCP）、名称、匹配证据、主要用途、可信状态和一手来源；
- Skill 补充来源仓库和 `SKILL.md` 路径；
- MCP 补充 canonical URL，并仅在目录有记录时给出传输方式、安装方式和许可证。

没有直接匹配时明确说明缺口。结果较多时按二级领域、数据类型和工具约束继续筛选，但不要修改目录规则。

## 文件

- `data/science_skill_catalog.json`：规范化 Skill 静态目录。
- `data/science_mcp_catalog.json`：从活动科研 MCP Hub 生成的紧凑静态目录。
- `scripts/filter_science_resources.py`：Skill/MCP 统一筛选器，仅依赖 Python 标准库。
- `scripts/build_science_mcp_catalog.py`：从活动 Hub 快照重建 MCP 静态目录。
- `scripts/filter_science_skills.py`：兼容旧调用的 Skill-only 筛选器。
