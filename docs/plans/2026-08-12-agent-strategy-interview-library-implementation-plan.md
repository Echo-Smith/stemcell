# Agent Strategy Interview Library Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an evidence-calibrated, reusable Agent strategy interview retrospective, standard answer library, and rapid-review card.

**Architecture:** Keep the failed interview as a factual retrospective, separate reusable answers from company-specific details, and maintain a compact rehearsal card derived from the long-form library. Treat existing project evidence as the source of truth and label implemented code, offline validation, and production use separately.

**Tech Stack:** Markdown, local resume evidence ledger, Git version control.

---

### Task 1: Write the interview retrospective

**Files:**
- Create: `resume/feedback/2026-08-12-小红书-Agent策略产品运营-业务面结果复盘.md`

1. Map the interview timeline to evaluated competencies.
2. Separate transcript facts from meeting-assistant interpretations.
3. Identify demonstrated strengths, decisive gaps, and revised conclusions.
4. Record new user-confirmed evidence about the adopted “核查较真” capability.

### Task 2: Build the standard answer library

**Files:**
- Create: `resume/interview/2026-08-12-Agent策略岗位-面试复盘与标准回答库.md`

1. Define one reusable answer framework.
2. Add standard answers for self-introduction, project, ReAct, retrieval, Eval, Badcase, Prompt, Memory, collaboration, and stress questions.
3. Add follow-up branches and prohibited claims.
4. Add technical concept cards with project mappings and boundaries.

### Task 3: Build the rapid-review card

**Files:**
- Create: `resume/interview/2026-08-12-Agent策略岗位-面试前速记卡.md`

1. Compress the hiring thesis into a 75-second introduction.
2. Add ten technical one-liners and three Badcase stories.
3. Add factual boundaries and a 15-minute rehearsal routine.

### Task 4: Update indexes and historical status

**Files:**
- Create: `resume/interview/README.md`
- Modify: `resume/interview/2026-08-10-小红书-Agent策略产品运营-电话沟通准备.md`
- Modify: `resume/README.md`

1. Mark the earlier telephone guide as historical pre-interview preparation.
2. Link the new retrospective, library, and rapid-review card.
3. Add the library to the resume asset index.

### Task 5: Validate and version

1. Search for unsupported “投稿成功率提升”, mature production Eval, and whole-product internal deployment claims.
2. Check project metrics against the evidence ledger.
3. Review Markdown links and headings.
4. Stage only interview-library files and commit them on the current branch.
