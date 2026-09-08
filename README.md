# Stemcell — Test Only

> **本项目仅作为一个 test / 实验原型。** 用于测试多视角生成、方案对比和模型评审流程，不作为生产工具或自动决策依据。测试通过只说明对应的软件行为符合预期，不证明模型生成的方案正确，也不证明这套方法优于简单提示词。

把一个功能需求变成三条可比较的实现路线，并测量这套流程是否优于简单提示词。

默认路线是**最快验证、最低维护成本、支持长期扩展**。输出交付范围、舍弃项、步骤、工作量估计及依据、风险、代价和适用条件。模型核对是辅助意见，分数不代表成功率；有硬约束冲突、证据不足或评审失败的候选不会进入推荐集合。

目前没有经过真实用户偏好和执行结果验证。

## 测试情况（2026-09-08）

| 检查 | 结果 | 能说明什么 |
|---|---|---|
| 自动化测试 | Python 3.12 下 47 项通过 | 覆盖约束传递、评分失败、配置、调用预算、匿名材料和 CLI 等行为 |
| 静态与构建检查 | Ruff、格式检查、wheel / 源码包构建通过 | 代码检查和打包可用；不代表生成质量 |
| 十案例离线测试 | 10 个模拟需求 × 3 个方法，30 组完成，170 次模拟调用 | 验证协议和流程；没有真实模型 token 或质量结论 |
| 真实接口试跑 | 1 个模拟需求 × 3 个方法，共生成 9 个候选，17 次真实调用 | 三组均返回有效结构；输入仍是模拟需求，不是真实用户效果实验 |
| 人工盲评与落地效果 | 尚未完成 | 不能宣称节省决策时间、提高采纳率或改善实际结果 |

真实接口试跑中，生成和评审使用同一个 `DeepSeek-V4-Flash` 模型，并发设置为 1。下表含各方法的生成和共同评审，不含单独提炼底座的 557 token / 74.647 秒：

| 方法 | 调用数 | 输入 + 输出 token | 耗时 |
|---|---|---|---|
| 一次提示 | 4 | 5,611 | 182.103 秒 |
| 普通采样 | 6 | 6,786 | 197.635 秒 |
| Stemcell | 6 | 8,249 | 210.991 秒 |

这个单案例中 Stemcell 多用了约 **47% token**，尚未证明额外开销带来了更好的方案。正式试跑总计 21,203 token，不含连接探测和排障调用；没有单价信息，因此不估算费用。结果不能推广为模型或方法的一般性能差异。

**已知漏检：** 一个候选声称 `git checkout -b ...` 恢复历史版本不会影响原笔记，模型裁判判为通过；在临时仓库复现后，工作文件实际改变了。引用存在并不等于步骤安全或正确。反例、重现脚本和记录均保留，不能把“模型未发现冲突”理解为已实测通过。

详细内容：[实验结论](docs/experiments/2026-09-08-initial-findings.md) · [真实调用报告](docs/experiments/artifacts/live-pilot/REPORT.md) · [方案输出示例](docs/experiments/artifacts/live-pilot/stemcell-comparison.md) · [离线报告](docs/experiments/artifacts/offline/REPORT.md) · [漏检重现脚本](docs/experiments/reproduce_git_restore.py)。

## 快速开始

Python 3.10+，建议使用独立虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

# 无需密钥：仅验证软件协议和输出流程，内容是模拟占位
stemcell run --offline --input examples/decision_input.md

# 使用已有 .env，不复制密钥到本项目
stemcell run --env-file /absolute/path/to/.env \
  --input examples/decision_input.md \
  --format markdown --output comparison.md
```

默认读取当前目录的 `config.example.yaml`，也可 `--config /absolute/path/config.yaml`。环境变量 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL` 提供生成接口。`.env` 只读取这三个变量及 `JUDGE_API_KEY`、`JUDGE_BASE_URL`、`JUDGE_MODEL`，不执行内容、不加载其他服务密钥、不支持变量插值或多行值。显式指定的文件覆盖同名进程环境变量。

若需要独立评审接口，将配置中的 `judge.enabled` 设为 `true` 并设置对应 JUDGE 变量。未启用时，`llm.quality_model` 仍可在同一接口上选择不同裁判模型；留空使用生成模型。`llm.reset_model` 留空也使用生成模型。不同接口的模型名不能直接互换。

部分兼容接口不支持 `temperature` 或要求不同的输出上限参数：可设 `temperature: null`，以及 `token_parameter: max_completion_tokens`。工具不强制启用供应商专有的 JSON 模式；会验证返回的 JSON 和字段，拒绝被截断或格式错误的回答。SDK 自动重试已关闭。

## 一次运行

```bash
stemcell run --input input.md --strategy stemcell
stemcell run --input input.md --strategy single_prompt
stemcell run --input input.md --strategy sampling
stemcell run --input input.md --strategy stemcell_no_reset

stemcell run --input input.md --format json --output result.json
stemcell run --input input.md --perspectives conservative,engineering,risk --count 3
stemcell list-perspectives
```

| 方法 | 生成时看到的材料 | 生成调用数（N 个候选） |
|---|---|---|
| `single_prompt` | 原始需求；一次输出 N 条路线及比较推荐 | 1 |
| `sampling` | 原始需求；N 次普通独立采样 | N |
| `stemcell` | 带出处的结构化底座；不同路线倾向 | N |
| `stemcell_no_reset` | 原始需求；保留路线倾向 | N |

**共同评审额外消耗调用。** 单次 `run` 先提炼一次任务底座；所有方法的每个成功、去除完全重复后的候选再评审一次。默认 N=3 时，一次提示方法最多 5 次，其他方法最多 7 次。因此“一次提示”指生成基线，不代表整个附带评审的运行只有一次调用。

默认展示全部成功路线的对比，按条件选择，不显示冠军。`--top` 仅限制 JSON 中保留的辅助分数排序集合，不减少调用，也不隐藏其他路线。`--count` 超过内置视角数量时会重复采样并给出提示，不能保证更多实质不同的路线。

文本/Markdown 的 `--output` 现在保存 Markdown；JSON 导出请明确指定 `--format json`。这是相对 v0.1 的行为变更。遇到不完整结果会保留可用输出，并以退出码 2 提示；退出码 0 只表示所需结构完整，不表示所有方案可行。

## 约束与错误处理

任务底座保留完整原文、事实、偏好、未知项，以及每项明确硬约束的原文连续引用。独立列出的约束/红线必须进入核对清单；出处缺失或不在原文中会使提炼失败。

裁判读取相同原文和底座、相同候选字段，不读取内部视角标签。每项硬约束需要 `pass`、`fail` 或 `unknown` 及理由：

- `reviewed`：模型给出了可找到原文的证据，未指出冲突。仍需真实验证证据语义和实际实现。
- `violates`：模型发现硬约束冲突。其他维度再高也不进入推荐集合。
- `needs_verification`：证据不足，或裁判发现底座可能遗漏了原文约束。
- `unassessed`：调用、JSON 或字段验证失败，无默认分数。
- 生成失败直接排除；仅去除内容完全重复的候选，不声称已测量语义多样性。

程序能核对引用是否存在，不能证明引用足以支持结论，也不能保证模型提炼出了原文中的全部硬约束。原文检查、未知状态和人工复核用于暴露这些限制。

## 十案例对照

`examples/benchmark_cases.json` 是十个**模拟需求**，覆盖导出、反馈、导入、搜索、更新说明、预约、图片处理、任务队列、收藏整理和功能开关。它们不是用户项目记录。

```bash
# 离线冒烟：170 次模拟调用，没有真实 token/费用
stemcell benchmark --offline --cases examples/benchmark_cases.json \
  --output output/offline-check

# 先用一个案例核对接口、格式与用量；输出目录必须尚不存在
stemcell benchmark --env-file /absolute/path/to/.env \
  --cases examples/benchmark_cases.json --limit 1 --max-calls 17 \
  --output output/live-pilot

# 全部十案例：最多 170 次逻辑调用
stemcell benchmark --env-file /absolute/path/to/.env \
  --cases examples/benchmark_cases.json --max-calls 170 \
  --output output/live-ten

# 增加不使用摘要生成的消融组：十案例最多 230 次调用
stemcell benchmark --env-file /absolute/path/to/.env \
  --cases examples/benchmark_cases.json --include-no-reset --max-calls 230 \
  --output output/ablation
```

每个案例只提炼一次共同底座并单独记录开销；同一个底座复用于三个方法的评审，只有 Stemcell 生成阶段会使用它。方法执行顺序和盲评组别按 seed 随机，`--seed` 可复现映射。调用失败、重复候选可能使实际调用次数少于上限。

生成阶段对每个候选使用相同输出上限；一次提示的总上限为该值乘 N。但输入长度、模型行为、供应商截断和实际输出仍可能不同，因此相同配置不等于相同成本。先比较真实用量，再设计相近成本实验，不能从默认组间差异直接推出编排的独立收益。

实验目录包含：

```text
REPORT.md                 工程完成情况与实际调用/token 汇总
blind/                    匿名需求和候选材料（先看这里）
ratings.csv               空白人工记录表
private/mapping.json      每个案例的字母与方法对应关系
private/summary.json      全部运行结果、设置、用量与源文本哈希
private/*-source.json     实验需求及带出处的底座
private/*-<strategy>.json  每个方法的完整结果
```

`private` 目录在创建时限制为当前用户访问；本地报告和盲评包仍可能包含输入原文，请按输入的分享范围使用。每个方法结束即保存检查点；当前没有自动续跑，重跑应使用新的目录，以免把不同配置结果混在一起。

## 真实需求与人工盲评

准备 JSON 数组，每条必须声明 `kind` 和 `source`，可直接提供 `input`，也可用相对清单目录的 `input_file`：

```json
[
  {
    "id": "my-feature-01",
    "title": "真实功能需求标题",
    "kind": "real",
    "source": "需求记录日期与出处",
    "input_file": "requirements/feature-01.md"
  }
]
```

先阅读 `blind/`，不要查看映射、成本或模型分数。字母每个案例独立随机；材料风格仍可能泄露生成方式，不能保证完全盲法。盲评包保留原始候选，不展示评分结果；单次提示的内部推荐也不提前展示，避免锚定。

在 `ratings.csv` 填写组别选择、平局 `tie` 或都不选 `neither`、总阅读秒数、按组记录的约束遗漏/实质路线数/修改量，实际采用后补充 `adopted_bundle`。

```bash
stemcell report --experiment output/live-ten
```

未填写时，报告明确显示“尚无人工偏好”；离线占位输出不允许生成偏好效果结论。阅读时间是同时比较全部方法的总时间，不能解释成某个方法节省了多少时间。要测量时间节省，需要另做独立、随机分配的任务实验。

## 开销与可复现性

- 每条调用记录阶段、接口角色、模型、耗时和返回 token；失败保留异常类型，不输出供应商错误正文或密钥。
- 用量未返回或未知时是 `null`，不是 0。JSON/字段验证失败可能发生在成功返回后，需同时看候选/评审状态。
- 只有提供同币种、对应 `provider/model` 的单价才估算费用；未提供就显示未知。估算不包括缓存折扣等账单细节。
- `max_calls` 是进程内逻辑调用上限。它不是 token 或金额硬上限；供应商可能对失败请求计费。基准运行在开始前检查所需最大调用数是否足够。
- `max_input_chars` 限制原文字符数，`max_tokens` 限制每个候选的最大输出。不要将字符上限等同于模型上下文窗口。

开发检查：

```bash
pytest -q
ruff check stemcell tests
ruff format --check stemcell tests
```

实现文档见 `docs/plans/`。SDK 接口核对来源：[OpenAI Python 官方文档](https://github.com/openai/openai-python)，通过 Context7 获取。项目沿用 MIT 协议。

批量调用遇到限流、鉴权或权限拒绝时，在保存当前结果后停止，不继续请求其他案例；不完整案例不纳入偏好统计。单案例在提炼阶段失败时，JSON 输出仍保存错误类型和已尝试调用的用量；Markdown 输出失败记录到同名 `.error.json` 附件。评审可通过 `quality.max_concurrent` 控制并发。
