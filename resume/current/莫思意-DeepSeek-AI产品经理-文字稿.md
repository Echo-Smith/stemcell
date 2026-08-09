# 莫思意｜AI 产品经理（AI 产品 / Agent Harness）

19290865729｜aodomosiyi@foxmail.com｜杭州｜[作品集](https://profile.ericdocmic.top)｜[GitHub](https://github.com/Echo-Smith)

## 个人概述

2024 届新媒体技术本科，现工作于内容生产与创作者协作一线；个人发起并独立构建 AI 内容产品“笔润智谈”，完成用户问题发现、版本规划、产品设计、Agent Harness 实现、Web 交付与反馈迭代。V1 覆盖 200+ 名体验用户，其中 53 名作者完成真实写作任务；V2 截至 2026.07.31 有 14 名用户、近 70 条完整任务样本。实际接入 DeepSeek API，长期使用 Codex、Claude Code、Dify 等 Agent / AI Coding / Workflow 工具推进调研、原型、开发、测试与复盘。

**产品判断：**Agent 的价值不在最大化自主性，而在真实任务中把 Context、Tools、Memory、退出边界与评测组织成可观察、可干预、可持续迭代的运行环境；高置信步骤交给模型，关键决策保留依据、撤销和人工接管。

## 核心能力

- **产品与用户：**用户反馈与定性观察、需求拆解、MVP / 版本规划、PRD、优先级判断、交互原型、上线验收、Badcase 与版本复盘。
- **Agent 产品：**LLM API、Agent Loop、Tool Use、Reasoning / Planning、Prompt / Context Engineering、RAG、Function Calling、Memory、MCP 原型、Multi-Agent、Human-in-the-loop。
- **数据与工程：**用例集与模型评测、Trace / Token / 时延 / 错误分析；Python、SQL / PostgreSQL、Go、TypeScript / React、REST API、WebSocket、Docker、Git，可独立交付 Web / PWA 产品原型。

## 核心项目

### 笔润智谈｜面向真实内容生产的 Chat / Agent 工作台｜2026.03—至今

个人发起并独立完成产品规划、交互设计、Agent 应用链路与 Web 交付｜V1 已进入内部内容生产流程，V2 持续内测  
[V1](https://luminbuddy.ericdocmic.top)｜[V2](https://luminbuddy2.ericdocmic.top)｜[GitHub](https://github.com/Echo-Smith/luminbuddy-writing-agent-v2)

- **从真实任务规划版本：**在作者、编辑与内容运营流程中识别资料核验、表达同质化、个人视角、版本追踪和返工协作问题；先用 V1 验证写作、润色与批量查重，再将 V2 定义为可追踪、可回退、可人工接管的 Agent 编辑部。
- **让反馈进入产品机制：**根据“逻辑更强但格式趋同”的反馈调整写作规范、减少模板化句式；面对标题伦理与个人视角分歧，将意见建模为按用户、来源和范围生效的个性化记忆，避免把一次反馈固化为全局 Prompt。
- **平衡确定性与自主性：**保留固定 Pipeline 保障关键步骤顺序，以 ReAct UnifiedAgent 按上下文选择工具；统一设置取消、全局超时、Token 预算、断连暂停和连续模型失败断路器，并用迭代上限与人工确认超时避免任务失控。
- **设计 Context、Memory 与 Tool 边界：**以工作摘要、会话消息、长期偏好和实体关系网络构成四层记忆，提供 Markdown 与数据库导入 / 导出；实现 MCP 客户端接入与进程内 Server 原型，将外部工具和内置能力注册进统一 ToolRegistry。
- **编排 Agent 协作与人工决策：**将研究、写作、审校三类 Agent 组织为版本化协作流，以数据库 Lease 防止重复执行，按信源、信息缺口、稿件结构与审校严重度动态路由；低质量任务有限重试后进入人工 Decision，支持批准、退回和接管。
- **用数据验证与复盘：**接入 DeepSeek API 处理生成、审校和记忆抽取，以用例、Badcase、Trace、Token、时延、错误与人工介入记录复盘链路。V1 覆盖 200+ 名体验用户，其中 53 名作者完成真实任务；V2 有 14 名用户、近 70 条完整任务样本。重构并发查重与失败兜底后完成 30 余次实际任务，单次处理 50 余人 × 每人 30 条文本，5 分钟内全部返回。

### HearHer 听见妈妈｜多模态体验、模型评测与安全边界｜2026.06—2026.07

腾讯音乐 AI Hackathon 两人团队｜负责产品规划、AI 能力设计、模型评测与 PWA 交付  
[项目介绍](https://hearher.me)｜[黑客松项目页](https://ideas.qq.com/work/detail/nBwZmb2DYJ1Ly3FqYh)｜[GitHub](https://github.com/Echo-Smith/HearHer-PWA)

- 面向妈妈群体的情绪与音乐需求，设计“状态输入—安全判断—受控推荐—真实播放—反馈沉淀”流程；由 LLM 负责语义理解和陪伴表达，以安全硬门槛、受控曲库与规则降级约束输出范围。
- 使用 177 条音频与 30 条产品用例对比 4 款 ASR、4 款 LLM 的识别、指令遵循和产品表现，完成 700+ 次调用；项目从 200+ 份提案中入围 14 项决赛作品。

### 贝伴｜AI 订阅管理助手

[在线体验](https://subbuddy.ericdocmic.top)｜设计 Function Calling 协议处理订阅增删改查与支出查询；视觉模型提取支付截图字段，并对删除、金额修改和低置信结果保留人工确认，形成“模型建议—用户确认—系统执行”的安全交互。

## 工作经历

### 杭州都市快报研学文化传播有限公司｜内容运营｜2024.11—至今

- 负责小红书、今日头条、微博等 40 万粉级官方账号的选题、生产、分发和复盘，协调 30+ 本地 KOL / KOC，参与约 150 人素人号矩阵管理；持续从作者、编辑和运营反馈中识别内容约束与协作问题。
- 使用飞书智能表格搭建话题获取、分类与数据看板，年度汇总 75 个话题、累计阅读量约 46.3 亿；使用 Python 清洗多平台数据，支持选题判断和阶段复盘。
- 参与内部 SaaS 上线前验收，围绕业务流程、数据字段和交互体验提交 6 项分级问题，整理复现路径、关键字段与截图，协助开发团队在半小时内定位关键问题并完成核心功能验证。

## 教育背景

**齐鲁工业大学｜新媒体技术（工科·计算机大类）｜本科｜2020.09—2024.06**  
相关课程：机器学习与模式识别、人工智能与深度学习、智能媒体传播、移动软件开发  
证书：大学英语六级 425 分、普通话水平测试二级甲等
