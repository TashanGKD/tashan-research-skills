---
name: experiment-design
description: 把"想验证什么"变成统计上站得住、可复现、可解释的完整实验工作流。当用户要设计实验/研究方案、选择设计类型、做随机化与区组、估算样本量与功效、制定分析计划与预注册，或在采集后执行组间/配对比较、ANOVA、非参数检验、卡方、相关分析、效应量与置信区间、多重比较校正并形成可报告结论时使用。机器学习 baseline 与组学专业管线不在本技能范围。
license: MIT
---

# 实验设计与统计分析 Experiment Design

设计决定了数据能回答什么问题——**混杂或伪重复的设计，事后再高级的分析也救不回来**。本技能把采集前的
Fisher 三原则、设计类型、随机化/区组、样本量与功效、预注册，与采集后按计划执行的验证性统计分析连成一条完整工作流。
跨学科通用：湿实验、临床、社科实证和计算实验都适用。

> 本技能整合了实验设计与统计功效分析的通行方法（Fisher 随机化/重复/区组原则、
> 经典 DOE 与响应面设计、Cohen 效应量与 a-priori 功效分析），并将样本量、随机化、
> DOE 布局等确定性计算下沉为可复现脚本。

## 脚本（确定性工具）

- `scripts/power.py` — 样本量/功效计算（依赖 statsmodels，见 `requirements.txt`）
- `scripts/randomization.py` — seeded 随机化方案：simple/block/stratified/cluster（仅标准库）
- `scripts/doe_designs.py` — DOE 矩阵：全析因/两水平析因/拉丁超立方，运行顺序随机化（仅标准库）
- `scripts/run_stat_tests.py` — 采集后验证性统计：描述统计、前提检查、检验、效应量、置信区间与多重校正
- `templates/preregistration.md` — 采集前预注册 / 分析计划模板（对应工作流第 7 步）
- `templates/analysis_report.md` — 验证性统计报告模板
- `tests/regression.py` — 设计/功效/随机化/DOE 回归测试
- `tests/statistical_regression.py` — 采集后统计计算与 scipy/statsmodels 对拍测试

## 何时使用

- "帮我设计一个验证 X 的实验/研究方案""这些样本/被试怎么分组"
- "该用什么设计——对照？随机？区组？析因？交叉？整群？"
- "样本量要多大 / 帮我算功效 / effect size 怎么定"
- "怎么避免混杂 / 批次效应 / 伪重复"
- "规划机器学习消融实验 / 基准对比 / 实验矩阵"
- "定一份采集前的统计分析计划 / 预注册"
- "两组/多组差异显著吗"、"处理前后有变化吗"
- "帮我跑 t 检验 / ANOVA / 卡方 / 相关分析"
- "这批 p 值怎么做多重比较校正，结果怎么写进论文"

## Fisher 三原则（每个好设计的地基）

- **随机化 Randomization**：随机分配处理，让已知/未知混杂在期望上均衡——这是把"比较"变成"因果"的关键。
- **重复 Replication**：在**正确的层级**上独立重复，才能估计变异。最常见致命错误是**伪重复**：
  3 只小鼠各测 100 个细胞，对施加在小鼠上的处理而言 n=3（小鼠），不是 n=300（细胞）。
- **区组/局部控制 Blocking**：把相似单元按批次/日期/site 分组、组内随机化，把这部分噪声从误差项里移走。

## 工作流（设计 → 采集 → 验证分析）

1. **陈述问题、单元、响应**：什么被随机化？测什么？真正独立重复在哪个层级？——这决定一切。
2. **列出干扰因素**（批次、日期、site、操作者、板位），逐一计划区组/分层/随机化。
3. **选设计类型**（用下面的决策树）。
4. **在正确层级定重复数**，并用样本量/功效模块算 n。
5. **生成随机化/DOE 布局**（用 `scripts/randomization.py`、`scripts/doe_designs.py`，seeded 可归档复现）。
6. **随机化运行/处理顺序**与板位/批次位置，防时间漂移与边缘效应。
7. **锁定分析计划并预注册**，让分析是验证性的而非事后自由发挥（用 `templates/preregistration.md`）。
8. **采集后先做数据概况与前提检查**：报告各组 n、缺失、描述统计、正态性与方差齐性；检验必须匹配区组/分层/整群/嵌套结构。
9. **按锁定计划执行检验**：一次计算 p 值、效应量和 95% CI；前提不满足时按决策树换方法并披露理由。
10. **校正并写结论**：同一检验族全部进入多重比较校正；非显著结果照报，探索性分析单列，明确结论边界。

## 采集后验证性统计

核心纪律是**按预注册或采集前锁定的计划执行**。没有预先计划时，先确认主要结局、比较组和方法，并在报告中标明"计划为事后确定"。

- 两独立组连续结局：近似正态用 Welch t，偏态/序数/小样本用 Mann–Whitney。
- 同一对象前后测量：本脚本支持配对 t；偏态时应改用 Wilcoxon 等专门工具并在报告中注明，不得硬套配对 t。
- 三组及以上：前提满足用 ANOVA，不满足用 Kruskal–Wallis。
- 分类变量：卡方；2×2 且期望频数小时查看 Fisher 精确检验。
- 连续变量关系：线性用 Pearson，单调或有离群值用 Spearman；相关不表示因果。

```powershell
python scripts/run_stat_tests.py describe --csv data.csv --value strength --group process
python scripts/run_stat_tests.py ttest --csv data.csv --value strength --group process
python scripts/run_stat_tests.py anova --csv data.csv --value yield --group temperature --posthoc
python scripts/run_stat_tests.py correct --pvalues 0.012,0.034,0.20,0.41 --method holm
```

输出包含统计量、p 值、效应量、95% CI、前提检查和 `interpretation_boundary`。报告时永远同时给出效应量与 CI；显著不等于重要，非显著不等于无差异。

## 设计类型决策树

```
你要学到什么？
├─ 比较少数预设条件 (A vs B vs C)？
│   ├─ 单元独立，有已知干扰因素(日/批/site)？ → 完全随机 或 随机区组设计
│   ├─ 每个单元可依次接受所有条件(可洗脱)？   → 交叉/重复测量设计(功效高，防残留效应)
│   └─ 只能随机化群体而非个体(学校/诊所)？    → 整群随机设计(在群体层级分析，防伪重复)
├─ 筛选很多因素(5+)找出关键的少数？          → 部分析因 / Plackett-Burman 筛选设计
├─ 量化少数因素的主效应+交互作用？            → 全 2^k 析因设计
├─ 找到使响应最优的设置(有曲率)？             → 响应面设计: 中心复合 / Box-Behnken
└─ 在连续空间探索仿真/计算模型？              → 空间填充设计: 拉丁超立方
```

选定后用脚本生成可复现布局（seeded、运行顺序随机化、可导出 CSV）：

```bash
python scripts/randomization.py block --n 60 --arms treatment,control --seed 42
python scripts/randomization.py stratified --strata siteA:30,siteB:30 --arms drug,placebo --ratio 2,1 --seed 42
python scripts/doe_designs.py full2 --factor temp:20,60 --factor conc:1,10 --factor pH:6,8 --seed 42
python scripts/doe_designs.py lhs --factor temp:20,60 --factor conc:1,10 --n 8 --seed 42
```

## 样本量与统计功效（可直接执行）

功效分析四参数——效应量、显著性 α、功效(1-β)、样本量 N——固定其三求第四。默认 α=0.05、power=0.80。
**只做 a priori（采集前）功效分析；事后功效分析是循环论证、无意义的。**

本技能附带脚本 `scripts/power.py`（封装 statsmodels），直接算：

```bash
python scripts/power.py ttest --effect 0.5 --alpha 0.05 --power 0.80      # 两样本 t 检验每组 N
python scripts/power.py anova --effect 0.25 --alpha 0.05 --power 0.80 --k 4
python scripts/power.py power --test ttest --effect 0.5 --n 50            # 反解：给定 N 的功效
```

效应量参考（不要默认套"medium"，应基于文献/预实验/最小实际意义效应 SESOI）：

| 检验 | 小 | 中 | 大 |
|---|---|---|---|
| Cohen's d (t) | 0.2 | 0.5 | 0.8 |
| Cohen's f (ANOVA) | 0.10 | 0.25 | 0.40 |
| r (相关) | 0.1 | 0.3 | 0.5 |

报告模板：`基于[文献/预实验/meta]的预期效应 [d/f=X]，α=.05，power=.80，[检验]所需样本量为[N]；
考虑约[X]%脱落，实际招募[最终N]。`

## 计算/机器学习实验（消融与基准）

- **单变量隔离**：每次消融只改一个因素，其余(seed/data split/epochs/硬件)固定并记录。
- **实验矩阵**：因素少(≤3)用全析因；因素多先跑单因素消融再组合优胜者；太贵用拉丁方抽代表组合。
- **资源估算**：总运行数=各因素水平数之积；GPU 小时=运行数×单次时长；超预算就提示优先级。
- **采集前定分析**：主/次指标、显著性检验(配对 t / bootstrap CI)、失败运行处理、可视化。

## 毁掉研究的结构性错误（分析救不回，只能靠设计）

1. **伪重复**：把同一单元的重复测量当独立重复。
2. **干扰因素混杂**：处理组周一跑、对照组周二跑 → 处理与"日期"混杂。
3. **随机化缺失/破坏**：便利分配让混杂溜进来。
4. **无恰当对照**：缺并行对照/载体对照/盲法，分不清处理效应与时间/安慰剂/操作效应。
5. **批次效应误当生物学**：组学里尤甚，跨批次随机/区组处理，别让批次与条件对齐。
6. **板边缘/位置效应**：别把对照全放第一列。
7. **部分析因忽略混叠**：低分辨率设计把主效应与交互混叠，先看 alias 结构再下结论。
8. **无曲率却做优化**：两水平析因测不出曲面最优，用响应面。

## 质量红线

- **样本量必须有依据**：效应量来自文献/预实验/SESOI，不拍脑袋。
- **显式标注偏倚与可行性/伦理限制**。
- **默认建议预注册**，降低事后自由度。
- **不做 p-hacking**：不因为不显著就换检验、删数据或切亚组；跑过的检验全部报告。
- **不徒手估计数值**：统计量由 `run_stat_tests.py` 计算，并保留前提检查和解释边界。

## 与其它技能的边界

- 把想法拆成数据任务/输入输出/baseline（偏 ML 工程）→「数据处理(baseline)」。
- 组学专业管线（scanpy/Seurat/DESeq）、混合效应模型、因果推断超出当前确定性脚本范围时，明确说明并改用专门工具。
- 生成研究假设/机制线索 →「假设生成」（本技能承接其后"如何验证"）。
