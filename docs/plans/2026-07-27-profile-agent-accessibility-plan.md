# Mosey 作品集 Agent 无障碍适配方案

日期：2026-07-27
范围：`mosiyi-portfolio`（https://profile.ericdocmic.top）。文末附 `ericdocmic-main-site`（https://ericdocmic.top）的低成本参考项。

## 1. 背景与目标

作品集已经完成为「人类用户」的无障碍适配：页脚有无障碍面板（高对比度、放大文字、链接下划线、减少动效），App.tsx 中有 41 处 ARIA 标注，图片均有 alt 文本，支持中英双语与深浅色模式。这部分覆盖了 WCAG 意义上的访问者。

但 2026 年的网站出现了第二类「访问者」——AI Agent。它们以三种方式到访：

1. **检索型 Agent**（ChatGPT、Perplexity、Claude 等的联网功能）：替用户读站、总结、转述。它们中的大多数不执行或只部分执行 JavaScript。
2. **操作型 Agent**（浏览器自动化 Agent）：读取页面的无障碍树（Accessibility Tree）来理解和操作页面。
3. **索引型爬虫**（GPTBot、ClaudeBot、PerplexityBot 等）：定期抓取，沉淀进模型或索引。

「Agent 无障碍」的目标：让 AI Agent 能够**发现 → 读懂 → 准确转述 → 在明确边界内使用**这个作品集，同时不削弱对简历等私人内容的保护。

## 2. 现状盘点（Agent 视角的体检结果）

| 项目 | 现状 | Agent 视角的问题 |
| --- | --- | --- |
| 渲染方式 | Vite + React 纯客户端渲染（CSR），`index.html` 只有一个 `<div id="root">` | 不执行 JS 的 Agent 在所有路由都看到**空白页面**，这是最严重的缺口 |
| 路由回退 | `create-spa-route-fallbacks.mjs` 把 `dist/index.html` 原样复制到 `/overview`、`/projects` 等目录 | 回退文件同样是没有内容的空壳，只对人类浏览器有意义 |
| robots.txt | 不存在 | 无法向 AI 爬虫声明抓取策略，也丢失了指向 sitemap/llms.txt 的入口 |
| sitemap.xml | 不存在 | 爬虫只能靠猜测发现 5 个前端路由 |
| llms.txt / llms-full.txt | 不存在 | 缺少给 LLM 的「高精地图」，Agent 只能靠空壳 HTML 瞎猜 |
| 结构化数据 | 有 OG / Twitter Card，无 JSON-LD | AI 搜索引擎无法获得 Person / ProfilePage 级别的实体认知 |
| 语义 HTML / ARIA | 良好（41 处 aria 标注、语义化标签、alt 文本） | 这是**已完成的资产**：操作型 Agent 读的正是无障碍树，人类无障碍投入直接复用 |
| 对话接口 | 已嵌入 Dify 作品集助手 | 对 Agent 不可见，也未在任何机器可读入口中声明 |
| 简历边界 | 前端访问码 + JS 动态写入 `robots: noindex`；PDF 直链实际公开 | JS 写入的 noindex 对不执行 JS 的爬虫**无效**；PDF 在 public 目录可被直链抓取 |
| 仓库卫生 | `deploy/resume-access-control.md` 明文记录访问码 | 若仓库（或部署包外泄）被公开，访问码即失效 |

## 3. 现有标准调研（截至 2026-07）

「Agent 无障碍」目前没有单一权威标准，但已形成一套分层的事实标准组合：

### 3.1 llms.txt / llms-full.txt（提案标准，生态增长中）

由 Answer.AI 联合创始人 Jeremy Howard 提出。在网站根目录放置 Markdown 文件：`/llms.txt` 是人工编排的站点导航（一句话简介 + 分区链接列表），`/llms-full.txt` 把核心内容全文内联，让 LLM 一次抓取吞下全部。它解决的是 LLM 的三个硬伤：上下文窗口有限、HTML 噪音大、训练数据滞后。Mintlify、Anthropic 文档站等已采用，ChatGPT、Claude、Perplexity 一类的 Agent 在理解站点时会优先寻找它。定位类比：robots.txt 管「能不能抓」，sitemap.xml 管「有哪些页」，llms.txt 管「哪些内容真正重要」。

### 3.2 robots.txt（RFC 9309）+ AI 爬虫 UA

成熟标准。2026 年需要显式面对的 AI 爬虫包括：GPTBot、ChatGPT-User、OAI-SearchBot（OpenAI）、ClaudeBot、anthropic-ai（Anthropic）、PerplexityBot（Perplexity）、Google-Extended（Gemini 训练）、Applebot-Extended、Bytespider（字节）、CCBot（Common Crawl）。robots.txt 是君子协定，不能替代服务端硬保护（简历 PDF 即为例证）。

### 3.3 Schema.org JSON-LD（成熟标准）

Google、Microsoft、Apple、OpenAI 共同维护。以 `<script type="application/ld+json">` 注入，与 DOM 解耦。对本站合适的类型：`ProfilePage` + `Person`（主页）、`ItemList`（项目列表）、`BreadcrumbList`（路由层级）、`WebSite`。这是 AI 搜索从「文本理解」走向「实体认知」的锚点，也是防止 AI 张冠李戴的信任来源。

### 3.4 WebMCP（W3C 孵化早期，跟踪试点）

Google Chrome 与 Microsoft Edge 团队在 W3C WebML Community Group 推动的浏览器标准草案，Chrome 146+ 提供实验版本。核心 API 是 `navigator.modelContext.registerTool()`：网站把自己的功能声明为结构化工具（名称 + 参数 schema + 执行逻辑），Agent 不再需要截图猜按钮，而是直接调用。它与 MCP Server 互补：WebMCP 管「用户在场时的页面操控」，MCP 管「后端无头任务」。目前处于 Early Preview，适合小步试点而非全面投入。

### 3.5 其他相关动向

操作型 Agent 的事实接口是**无障碍树快照**（agent-browser 等方案直接消费 Accessibility Tree），这印证了已有 ARIA 投入的价值。服务端方向还有 MCP Server、Microsoft NLWeb（自然语言站点接口），对个人静态站而言偏重，列为远期可选。Cloudflare 等厂商在推动「Markdown 内容协商」（对 Agent 直接返回 .md 版本），可作为 P2 观望项。

## 4. 分层适配方案

按 Agent 的使用链路分四层，逐层递进：

### L0 可被发现（爬虫与入口层）

新增 `public/robots.txt`：允许主流 AI 爬虫抓取公开内容，`Disallow: /resume/`，并声明 sitemap 与 llms.txt 位置。新增 `public/sitemap.xml`：列出 `/overview`、`/projects`、`/experience`、`/design` 四条公开路由（`/resume` 刻意不收录）。保留现有 OG / Twitter Card。

### L1 可被理解（内容与语义层）

新增 `public/llms.txt` 与 `public/llms-full.txt`，内容覆盖：站点定位、作者身份（Mosey，AI 产品经理）、五个项目故事的核心信息（问题、动作、验证数据）、经历摘要、联系方式与简历获取方式说明。在 `index.html` 注入 JSON-LD（`ProfilePage` + `Person` + `ItemList`）。**修复空壳路由问题**：让每个路由的实体 HTML 在没有 JS 时也包含该页核心文字（预渲染或静态快照），这是 L1 里工程量最大但收益最高的一项。

### L2 可被操作（交互层）

把 ARIA 维护纳入回归测试，保证无障碍树持续是操作型 Agent 的高质量接口。以 WebMCP 做小规模试点：注册只读工具如 `list_projects`、`get_project_detail`、`request_contact`，全部幂等、无副作用。把 Dify 助手作为「对话式 agent 接口」在 llms.txt 中显式声明。

### L3 边界与治理（安全层）

Agent 可读的范围必须严格等于「人类公开访客可见的范围」。具体措施：在 Nginx 层对 `/resume/` 与简历 PDF 加 `X-Robots-Tag: noindex, nofollow` 响应头（替代不可靠的 JS 注入）；按 `deploy/resume-access-control.md` 的推荐实施 PDF 硬保护（Basic Auth 或签名链接）；llms 系列文件、JSON-LD、sitemap 中一律不出现访问码、私人联系方式与简历细节；将访问码从仓库文档中移除并轮换。

## 5. 落地清单与验收标准

### P0（约半天，纯增量、零风险）

| # | 动作 | 产出物 | 验收标准 |
| --- | --- | --- | --- |
| 1 | 新增 robots.txt | `public/robots.txt` | 允许 GPTBot/ClaudeBot/PerplexityBot 等；`Disallow: /resume/`；含 Sitemap 行 |
| 2 | 新增 sitemap.xml | `public/sitemap.xml` | 4 条公开路由，lastmod 准确，通过 XML 校验 |
| 3 | 新增 llms.txt | `public/llms.txt` | 符合 llms.txt 格式（H1 标题 + 引用块简介 + H2 分区链接），通过在线校验器 |
| 4 | 注入 JSON-LD | `index.html` | ProfilePage+Person+ItemList，通过 Rich Results Test 与 validator.schema.org |
| 5 | Nginx 响应头 | 1Panel 站点配置 | `curl -I` 简历 PDF 与 `/resume/` 返回 `X-Robots-Tag: noindex, nofollow` |
| 6 | 仓库卫生 | `deploy/resume-access-control.md` | 访问码从文档移除并轮换为新码 |

### P1（1–2 天，建立自动化与真实内容）

| # | 动作 | 产出物 | 验收标准 |
| --- | --- | --- | --- |
| 7 | 生成脚本 | `scripts/generate-agent-files.mjs` | 从 `src/content.ts` 单一数据源自动生成 llms.txt、llms-full.txt、sitemap.xml；接入 `npm run build`，内容改动能自动同步 |
| 8 | 路由预渲染 | 升级 `create-spa-route-fallbacks.mjs`（或引入 Vite 预渲染方案） | `curl -s https://profile.ericdocmic.top/projects/` 在无 JS 下返回包含项目标题与正文的 HTML；五条路由全覆盖；人类访问体验与构建体积无明显退化 |
| 9 | PDF 硬保护 | Nginx Basic Auth 或签名链接方案 | 无凭证直接访问 PDF 返回 401/403；作品集内解锁流程不受影响 |

### P2（跟踪与小步试点）

| # | 动作 | 说明 |
| --- | --- | --- |
| 10 | WebMCP 试点 | Chrome flag 环境下注册 2–3 个只读工具；写好能力检测（`if ("modelContext" in navigator)`），不支持的浏览器静默跳过 |
| 11 | 对话接口声明 | 在 llms.txt 中说明本站提供 Dify 问答助手及其能力边界 |
| 12 | 远期评估 | Markdown 内容协商（.md 镜像）、MCP Server、NLWeb；每季度回看一次标准演进 |

## 6. 验证方案

功能验证：用 `curl -s`（不执行 JS）抓取各路由确认正文存在；用 GPTBot、ClaudeBot UA 模拟抓取确认 robots 策略符合预期；llms.txt 通过在线校验；JSON-LD 通过 Rich Results Test。

端到端 Agent 测试（每次大改后跑一次）：在 ChatGPT / Perplexity / Claude 中提问「莫思意是谁，做过哪些 AI 产品项目」，检查回答的准确性与引用来源；用浏览器 Agent 完成「打开作品集，找到笔润智谈项目并总结其验证数据」的任务，观察是否顺畅。

回归验证：跑 axe-core 与键盘走查，确保 agent 适配的改动（尤其是预渲染 HTML）没有破坏已有的人类无障碍能力。隐私核查：全文检索 llms 系列文件与 JSON-LD，确认不含访问码、未公开联系方式与简历细节。

## 7. 对这份 profile 的其他想法

`src/content.ts` 作为单一数据源是这个项目最被低估的优势：llms.txt、sitemap、JSON-LD、甚至预渲染内容都可以从它自动生成，改一处内容、处处同步，永远不会漂移——P1 的第 7 项就是把这个优势固化下来。

双语内容对 Agent 同样是资产：llms-full.txt 建议中英双语都收录，英文世界 Agent 的转述质量会明显受益。Dify 作品集助手其实已经是一个「agent 接口」，值得在 llms.txt 里显式声明，让来访的 Agent 知道有这条对话通道。

两个需要尽快处理的风险：一是 `deploy/resume-access-control.md` 里明文写着访问码，一旦仓库公开或被分享，前端访问页形同虚设；二是 `/resume/` 的 noindex 目前靠 JS 写入，不执行 JS 的爬虫根本看不到这条指令，简历 PDF 又是公开直链——也就是说「避免搜索收录」这层意图对机器访问者基本失效，必须下沉到 Nginx 响应头。

## 8. 附：ericdocmic.top 主站的低成本参考

主站是单页静态 HTML，天然对 Agent 可读，无需预渲染。可选的低成本动作：放一个极简 `llms.txt`（三五行说明「这是 eric 的开发日记，持续更新」）和 `robots.txt`。优先级低，做完作品集 P0 后顺手即可。
