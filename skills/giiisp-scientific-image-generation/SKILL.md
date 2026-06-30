---
name: giiisp-scientific-image-generation
description: 使用 Giiisp Imagine 科研图像生成接口，把论文段落、图题、实验流程或机制描述整理成作图简报、生成请求、图片结果和检查记录。适用于论文配图、科研流程图、机制通路图、实验示意图和学术汇报图。
---

# Giiisp Scientific Image Generation

## 适用场景

用户要“画一张科研图”“生成论文配图”“把这段方法做成流程图”“按这张图继续改”时使用本 skill。

不要把它用于纯 SVG 手绘、PPT 排版或普通网页插图。这里的主线是图像生成模型。

## 工作流

1. 先写作图简报：图的用途、核心信息、必须出现的标签、画幅比例、风格。
2. 再整理生成提示词：中文标签优先保留中文，科研术语按用户材料原样保留。
3. 把作图简报落成 `figure_spec.json`：必须标签、布局、风格、参考图角色、允许/禁止修改项。
4. 构造 `generate-async` 请求。
5. 保存请求体、响应、图片、轮询记录和检查记录。
6. 根据用户反馈继续改图，不覆盖上一版。
7. 生成或修改后写 `figure_manifest.json`，把任务、图片、检查和人工判断串起来。

## 参考 PaperBanana 的地方

这个 skill 不照搬 PaperBanana 的模型调用栈，但照搬它的工作流结构：

| PaperBanana 做法 | 本 skill 对应实现 |
|---|---|
| `generate_diagram(source_context, caption, ...)` | `prompt` + 作图简报，生成单张科研图 |
| `continue_run(run_id, feedback, ...)` | `--run-kind edit`、`--source-run`、`--reference-image`，每次修改新建 run |
| `metadata.json` / `run_input.json` | 每轮生成或 blocker 都写 `run_input.json`、`metadata.json` 和 `figure_manifest.json` |
| `batch_manifest.yaml` | 多图交付用 `build_figure_package.py` 汇总每张图的 manifest，不用口头一次性塞多张图 |
| `batch_report.json` / checkpoint | 图包目录写 `package_plan.json`、`package_checkpoint.json`、`figure_package.json` |
| `evaluate_diagram` | 当前先用 `check.json` + `manual_review.md`；有参考图时再补结构化对比 |
| 多候选择优 | 多个 run 完成后用 `select_figure_variant.py` 按完成状态、机器检查和人工质量轴选择候选 |

核心原则：每张图都必须有可追溯 run，不只保存最终图片。

## Crafter 启发但不照搬的地方

Crafter 的有效启发是“科研图是结构化语义组件组合，不只是更长 prompt”。本 skill 只吸收轻量契约，不引入 OpenRouter、多 agent、SAM3 或 raster-to-SVG 依赖：

- 用 `figure_spec.json` 作为单张图的结构化事实源，避免多轮 prompt 追加后互相矛盾。
- 用 `reference_role` 明确参考图用途，避免“保留结构”“借用元素”“润色草图”“编辑当前图”混在一起。
- 用固定质量轴复核生成结果：`content_accuracy`、`layout_quality`、`text_readability`、`aesthetic_quality`、`artifact_severity`。
- 需要模型审查时，用 DashScope Qwen 只做生成后语义复核，结果写 `semantic_review.json`，不替代本地机器检查。
- 继续坚持本 skill 的核心优势：Giiisp Imagine 专用、token 不落盘、每轮 run 可审计。

## Figure spec 契约

`figure_spec.json` 是每轮 run 的结构化作图简报，字段包括：

- `figure_kind`：`workflow`、`mechanism schematic`、`method diagram`、`comparison figure` 等。
- `caption` / `communicative_intent`：图题和要传达的科学信息。
- `required_labels` / `forbidden_labels`：必须出现和必须避免的标签。
- `layout_brief`：如“横向四步流程、每步一个卡片、箭头单向连接、留白充足”。
- `style_brief`：如“白底、蓝绿色学术配色、扁平风格、无广告感”。
- `reference_role`：空值或 `preserve_structure`、`use_elements`、`refine_sketch`、`edit_image`。
- `preserve_constraints`、`allowed_changes`、`disallowed_changes`：续改时的保留项、允许变化项和禁止变化项。

可从 JSON 直接构造 dry-run 或真实 run：

```powershell
python scripts/dry_run_scientific_image.py --input-json params.json
python scripts/generate_scientific_image_smoke.py --input-json params.json
```

`params.json` 可以直接放上述字段，也可以放在 `figure_spec` 子对象里。命令行参数优先级高于 JSON 默认值。

## 提示词质量改进建议

上一轮真实生成显示：接口能稳定返回 1024 x 1024 JPEG，主流程中文标签可读；但信息过密时容易出现小字拥挤、英文拼写错误和装饰元素偏多。第二轮收窄提示词后，结构更干净，但图内语义细节减少。因此提示词应优先控制信息层级：

- 主标签控制在 3-6 个短词或短句，逐字列出必须出现的标签。
- 不要要求模型生成密集说明文字；长解释放到图注、PPT 文本或后期排版层。
- 如果必须有英文术语，逐字给出并说明“不要改写、不要拼写变体”；不确定时优先中文。
- 明确版式约束，如“横向四步流程、每步一个卡片、箭头单向连接、留白充足”。
- 明确禁止项，如“小号正文、伪论文截图、随机英文、额外步骤、广告风格、水印”。
- 二次修改时只列允许变化的局部，避免重新生成整张图导致结构漂移。

检查报告必须写出“提示词质量改进建议”：指出本轮是标签问题、结构问题、语义缺失、风格偏差还是文字过密，并给出下一轮可直接复用的修改 prompt。

## 二次修改入口

用户说“按这张图继续改”“保留主体，只改标签/配色/布局/局部元素”时，走二次修改入口：

1. 先确认上一轮图片路径或用户提供的参考图路径。
2. 先声明 `reference_role`：`preserve_structure` 保留结构，`use_elements` 借用元素，`refine_sketch` 把草图润色成成品，`edit_image` 编辑当前图。
3. 把修改要求写进新的 `prompt`，明确“保留上一版的主体结构/构图/画幅”，再列出只允许变动的部分。
4. 通过 `imageBase64` 和 `imageMimeType` 传入参考图；不要覆盖上一轮 run 目录。
5. 新建一轮 run 目录，保存新的 `figure_spec.json`、`request.json`、`response.json`、`poll_history.json`、图片和 `check.json`。
6. 如果没有 token、没有参考图或接口拒绝访问，只写 `blocker.json`，不要伪造图片或检查结果。

二次修改 run 目录规范：

- 所有运行目录放在 `scientific_image_skill_runs/<session_slug>/<run_slug>/`。
- 首次真实生成可用 `real_token_YYYYMMDD/smoke_YYYYMMDD_HHMMSS/`。
- 二次修改必须用新的 `edit_YYYYMMDD_HHMMSS/` 目录，放在当前 session slug 下，或放在 `edit_YYYYMMDD/` session 下。
- 二次修改目录必须写 `source_run.txt`，内容是上一轮 run 目录的绝对路径或相对稳定目录路径。
- 二次修改目录必须保留自己的 `request.json`、`response.json`、`poll_history.json`、`generated_image.*`、`check.json` 和人工检查报告，不复写上一轮文件。
- 如果只做 dry-run，保存或输出的请求仍要能看出 `reference_image_path`、`imageMimeType` 和 `source_run`，但不要写入 token。

二次修改必须保留这些 lineage 字段：

- 父 run：`source_run_id`、`source_run_dir`、`parent_run_input_path`、`parent_metadata_path`、`parent_manifest_path`。
- 父图：`source_image_path`、`source_image_sha256`。
- 用户反馈：`feedback`、`preserve_constraints`、`allowed_changes`、`disallowed_changes`、`new_prompt_delta`。
- 语义继承：`caption`、`communicative_intent`、`figure_kind`、`required_labels`。

dry-run 二次修改示例：

```powershell
python scripts/dry_run_scientific_image.py --prompt "保留上一版四步流程，只把第三步改成模型推断，并统一蓝绿色学术风格" --reference-image "path/to/generated_image.png" --reference-role preserve_structure --allowed-changes 替换第三步标签 统一配色 --disallowed-changes 新增步骤 改变画幅
```

## 接口

| 项 | 内容 |
|---|---|
| 根页 | `http://images.sitianai.com/` |
| 生成 | `POST http://images.sitianai.com/api/generate-async` |
| 任务查询 | `/api/generate-jobs/{job_id}` |
| 鉴权 | 前端读取 `localStorage.giiisp_auth_token`，生成请求使用 `Authorization: Bearer <token>` |

请求体常用字段：

| 字段 | 说明 |
|---|---|
| `prompt` | 完整作图说明 |
| `negativePrompt` | 排除项，如水印、模糊文字、错乱标签 |
| `aspectRatio` | `1:1`、`4:3`、`16:9` 等 |
| `imageSize` | 前端当前使用如 `1K` |
| `numberOfImages` | 默认 1 |
| `responseModalities` | 默认 `["IMAGE","TEXT"]` |
| `outputMimeType` | 默认 `image/png` |
| `referenceImages` | 可选，参考图数组 |
| `imageBase64` / `imageMimeType` | 可选，用于图像编辑或参考图输入 |

## 访问码

真实生图必须测试结果。如果接口返回 `ACCESS_TOKEN_REQUIRED`，记录 blocker，不要伪造图片，并提示用户到 `https://giiisp.com/#/mcp/authenticate` 申请或刷新 Giiisp MCP 认证。

如果用户提供访问码或浏览器会话中已有 token：

- 可以使用 token 调 1 张低风险小样图。
- 不要把 token 写入文件、日志或最终回复。
- 只记录“已使用访问码 token”。
- 命令行测试只从环境变量 `GIIISP_AUTH_TOKEN` 读取 token。
- 无 `GIIISP_AUTH_TOKEN` 或 token 过期时，`blocker.json` 必须包含认证页和用户动作，便于前端直接提示用户处理。

## 结果检查

生成后至少检查：

- 图片文件是否存在。
- 图片文件字节数是否大于 0。
- 图片类型是否为 PNG、JPEG 或 WebP。
- 图片尺寸是否可读取。
- 是否因为缺少 token 或接口返回 `ACCESS_TOKEN_REQUIRED` 被 blocker 阻断。
- 是否符合图题和提示词。
- 必须标签是否缺失或错乱。
- 是否有水印、广告感、模糊文字。

检查结果写入同一轮 run 目录。

机器检查字段至少包括：

| 字段 | 说明 |
|---|---|
| `image_exists` | 图片文件是否存在 |
| `file_size_bytes` | 图片字节数，无法读取时为 `null` |
| `image_type` | `png`、`jpeg`、`webp`、`unknown` 或 `missing` |
| `mime_type` | 推断出的 MIME 类型 |
| `width` / `height` | 可读取尺寸；不可读时为 `null` |
| `has_token_blocker` | 是否存在缺 token 或 `ACCESS_TOKEN_REQUIRED` blocker |
| `blocker_reason` | blocker 原因 |
| `manual_review_required` | 固定为 `true`，用于提醒仍需人工检查语义和标签 |

`check.json` 还会包含：

- `machine_check`：本地可判定的存在性、格式、尺寸、宽高比和像素问题。
- `quality_review_axes`：人工或 VLM 后续复核用的五个质量轴。分数默认为 `null`，不要伪造模型判断。
- `semantic_review`：使用 `--semantic-check` 时生成的待填写语义复核占位。

## DashScope 语义审查

生成图片并通过机器检查后，可以用 DashScope Qwen 做一次视觉语义审查：

```powershell
$env:DASHSCOPE_API_KEY = "<dashscope_api_key>"
python scripts/semantic_review_dashscope.py --run-dir "scientific_image_skill_runs/session_a/smoke_YYYYMMDD_HHMMSS" --model qwen3.7-plus
python scripts/build_figure_manifest.py --run-dir "scientific_image_skill_runs/session_a/smoke_YYYYMMDD_HHMMSS"
```

审查脚本使用 DashScope OpenAI-compatible `chat/completions` 接口，默认模型是 `qwen3.7-plus`，也可通过 `--model` 改成账号可用的 Qwen 视觉模型。访问码只从环境变量 `DASHSCOPE_API_KEY` 读取，不写入 `semantic_review.json`、manifest、package 或最终报告。

`semantic_review.json` 必须保留：

- `provider`、`endpoint`、`model`、`dashscope_status_code`。
- `quality_review_axes`：五个质量轴的 `PASS` / `FAIL` / `UNCERTAIN`、分数和理由。
- `observed_labels`、`missing_required_labels`、`forbidden_labels_seen`。
- `overall_ready_to_ship`、`recommended_next_action`、`next_edit_prompt`。

如果缺少 `DASHSCOPE_API_KEY`、图片不存在、模型不可用或返回无法解析，脚本写 blocked 状态，不伪造语义判断。

人工检查报告建议使用 `templates/check_report_template.md`，字段至少包括：

- run 目录、源 run 目录、图片路径、请求摘要和生成时间。
- 机器检查摘要：存在性、字节数、类型、尺寸、blocker。
- 语义检查：是否符合图题、必须标签是否出现、是否有错字/伪英文/水印/广告感。
- 图像质量：布局、留白、层级、颜色、图标一致性、是否适合论文或汇报。
- 提示词质量改进建议：本轮问题归因、下一轮 prompt、negative prompt、是否需要二次修改参考图。

## Dry-run

无访问码时运行：

```powershell
python scripts/dry_run_scientific_image.py --prompt "画一个四步科研流程图：问题定义、数据整理、模型生成、结果检查"
```

dry-run 只构造请求体，不发起生成。

参考图 dry-run 默认不打印整张图片的 base64，只显示 `<redacted reference image base64>`，并在 `edit_metadata` 里记录图片 MIME、字节数和 SHA-256，避免把大段图片数据写进日志。

## Figure manifest

生成或二次修改后运行：

```powershell
python scripts/build_figure_manifest.py --run-dir "scientific_image_skill_runs/real_token_prompt_refine_20260602/smoke_20260602_162034"
```

`figure_manifest.json` 至少记录：

- `run_id` 和 `run_dir`
- `figure_id`、`source_run`、`feedback`、`lineage`
- `caption`、`intent`、`figure_kind`、`required_labels`、`style_brief`
- `prompt`、`negativePrompt`、画幅、图片大小
- `request.json`、`response.json`、`poll_history.json`、图片、`check.json`、`manual_review.md`、`blocker.json`
- 输出摘要：图片路径、SHA-256、MIME、宽高
- 质量摘要：机器检查、人工检查摘要、是否需要重生成
- 机器检查摘要
- 人工检查摘要

它的作用类似 PaperBanana 的 run metadata/package report：让后续 continue、批量、复核和交付时知道这张图从哪里来、怎么生成、是否合格。

## Figure package

多张图或一个论文图包完成后，汇总所有 `figure_manifest.json`：

```powershell
python scripts/build_figure_package.py --input "scientific_image_skill_runs/real_token_prompt_refine_20260602" --package-dir "scientific_image_skill_runs/packages/paper_demo_20260602" --title "论文图像生成结果包"
```

图包目录会写：

- `package_plan.json`：锁定本次要交付的图、图题、类型、意图和 manifest 路径。
- `package_checkpoint.json`：记录每个 item 的状态、run id、manifest 和错误，便于后续恢复。
- `figure_package.json`：给用户查看的交付清单，统计完成/阻塞数量和每张图的图片路径、caption、错误。

这对应 PaperBanana 的 `orchestration_plan.json`、`orchestration_checkpoint.json` 和 `figure_package.json` 思路。

## Variant selection

如果同一张图生成了多个候选 run，先为每个 run 生成 `figure_manifest.json`，再运行：

```powershell
python scripts/select_figure_variant.py --input "scientific_image_skill_runs/session_a" --out "scientific_image_skill_runs/session_a/variant_selection.json"
```

选择逻辑只使用可审计字段：完成状态、是否有图片、`machine_check` 是否通过、DashScope `semantic_review_summary`、人工填写的 `quality_review_axes` 分数和 blocker。没有人工或模型语义分数时不会伪造语义判断。

## 真实生成 smoke test

有访问码时运行：

```powershell
$env:GIIISP_AUTH_TOKEN = "<token>"
python scripts/generate_scientific_image_smoke.py --prompt "画一个四步科研流程图：问题定义、数据整理、模型生成、结果检查"
```

续改命令示例：

```powershell
python scripts/generate_scientific_image_smoke.py --run-kind edit --source-run "scientific_image_skill_runs/real_token_prompt_refine_20260602/smoke_20260602_162034" --reference-image "scientific_image_skill_runs/real_token_prompt_refine_20260602/smoke_20260602_162034/generated_image.jpg" --prompt "保留四步结构，只把第三步改为证据核验" --feedback "第三步语义不够准确，需要改成证据核验" --required-labels 提出问题 检索论文 证据核验 输出结论
```

脚本会发起 `POST /api/generate-async`，随后轮询 `GET /api/generate-jobs/{job_id}`，并把本轮证据保存到 run 目录：

- `request.json`：生成请求和脱敏后的请求头。
- `response.json`：`generate-async` 原始响应。
- `poll_history.json`：每次任务查询结果。
- `generated_image.*` 或 `image_url.txt`：下载成功的图片，或接口只返回远程地址时的地址记录。
- `check.json`：图片是否存在、字节数、PNG/JPEG/WebP 类型、尺寸、token/blocker 状态和失败原因。
- `semantic_review.json`：可选，DashScope Qwen 对生成图的语义审查。
- `run_input.json`：PaperBanana 式输入契约，记录 prompt、参考图哈希、source run、画幅、大小和 token 策略。
- `metadata.json`：本轮状态摘要，记录 job id、poll 次数、输出路径、机器检查和 blocker。
- `figure_manifest.json`：把请求、响应、图片、检查、人工复核和 source run 串成一份交付/续改索引。
- `blocker.json`：无 `GIIISP_AUTH_TOKEN`、接口返回 `ACCESS_TOKEN_REQUIRED`、无 `job_id`、轮询超时或没有图片时写入。

不要手写或伪造 `response.json`、`poll_history.json`、图片文件或 `check.json`。如果没有 token 或接口拒绝访问，保留 `blocker.json` 即可。
