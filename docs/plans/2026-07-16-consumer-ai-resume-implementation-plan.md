# C端 AI 产品经理定向简历 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 生成一份面向 C 端、跨平台和模型评测岗位的独立单页简历。

**Architecture:** 使用 Markdown 维护可编辑文案，使用 ReportLab 生成稳定的 A4 PDF，并为项目官网、GitHub 和 iOS Demo 添加可点击链接。最终通过 Poppler 渲染和 pypdf 文本/链接检查验证。

**Tech Stack:** Markdown, Python, ReportLab, Poppler, pypdf

---

### Task 1: 创建定向简历文案

**Files:**
- Create: `career/莫思意-AI产品经理-C端AI定向版.md`

1. 将个人定位改为 C 端 AI、移动端和模型评测。
2. 按 HearHer、贝伴、笔润智谈排序项目。
3. 加入 CET-4，不加入 CareerTrace 和虚构出海经历。

### Task 2: 创建 PDF 生成器

**Files:**
- Create: `career/generate_consumer_ai_resume.py`
- Create: `output/pdf/莫思意-AI产品经理-C端AI定向版.pdf`

1. 复用现有简历的字体、间距和单页布局。
2. 添加官网、GitHub、iOS Demo 的 PDF 链接注释。
3. 执行生成器，确保内容不溢出。

### Task 3: 验证输出

**Files:**
- Create: `tmp/pdfs/consumer-ai-resume/page-1.png`

1. 使用 `pdfinfo` 确认 A4 单页。
2. 使用 `pdftoppm` 渲染并目视检查裁切、重叠、乱码与层级。
3. 使用 pypdf 检查 CET-4、核心指标、GitHub 和 Appetize 链接。
