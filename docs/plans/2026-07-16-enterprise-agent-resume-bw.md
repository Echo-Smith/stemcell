# 企业 AI Agent 黑白简历 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 生成一份面向企业内部 AI Agent / Workflow 岗位的黑白单页简历，并更新笔润智谈真实用户、投稿、录用和 Badcase 数据。

**Architecture:** Markdown 保存完整可编辑文案；独立 ReportLab 生成器实现 A4 黑白排版、高清头像与可点击项目链接；Poppler 和 pypdf 负责视觉与结构验证。旧版本不覆盖。

**Tech Stack:** Markdown, Python, ReportLab, pypdf, Poppler

---

### Task 1: 核对证据与表达边界

**Files:**
- Read: `/Users/marshecho/WorkBuddy/20260413090446/笔润智谈-PRD-V1.0.docx`
- Read: `/Users/marshecho/Codex/luminbuddy/writing-agent-v2/tests/reports/benchmark_report_20260716_010530.json`

1. 仅采用 PRD 中与已上线 V1 一致的工作流事实。
2. 计算同期投稿和录用数据：60/25 对比 30/7。
3. 不写“检测率 100%”或“一次生成全部解决”。

### Task 2: 创建定向文案

**Files:**
- Create: `career/莫思意-AI产品经理-企业Agent定向版.md`

1. 使用 JD 原话描述任务拆解、知识检索、异常兜底、效果评估和 Badcase。
2. 将笔润智谈置于第一项目，保留 Dify、贝伴和 HearHer 的互补证据。
3. 更新 CET-4、个人主页和 GitHub。

### Task 3: 创建黑白 PDF

**Files:**
- Create: `career/generate_enterprise_agent_resume_bw.py`
- Create: `output/pdf/莫思意-AI产品经理-企业Agent定向版.pdf`

1. 使用纯黑、深灰、浅灰三级颜色和细线分隔。
2. 使用高清头像 `/Users/marshecho/Desktop/莫思意 - AI产品经理简历（系统级AI个性化方向）_files/个人头像.jpg`。
3. 添加个人主页、GitHub和项目链接注释。

### Task 4: 验证

**Files:**
- Create: `tmp/pdfs/enterprise-agent-resume-bw/page-1.png`

1. 确认单页 A4、无内容溢出。
2. 渲染并检查头像清晰度、字号、换行、层级与留白。
3. 使用 pypdf 检查核心数据、CET-4和链接注释。
