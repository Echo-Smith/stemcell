# Universal AI Product Resume Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use the active resume, PDF, design, and skill-creator workflows to implement this plan task-by-task.

**Goal:** Replace the legacy generic AI product manager resume with one evidence-backed, cross-platform mother resume and synchronize the improved narrative rules across all skill distributions.

**Architecture:** Keep Markdown as the source of truth, derive a platform-safe TXT and a semantic single-page HTML, then print HTML to PDF and visually verify it. Archive the superseded generic resume before replacing active paths. Update one reusable skill reference and copy the validated change to local, share, and GitHub packages.

**Tech Stack:** Markdown, semantic HTML/CSS, Microsoft Edge headless printing, Poppler PDF QA, Python skill validation, Git/GitHub.

---

### Task 1: Establish a recoverable version boundary

**Files:**
- Archive: `resume/current/莫思意-AI产品经理-定向简历-文字稿.md`
- Archive: `output/html/莫思意-AI产品经理-定向简历.html`
- Archive: `output/pdf/莫思意-AI产品经理-定向简历.pdf`
- Archive: `output/docx/莫思意-AI产品经理-定向简历.docx`

1. Create the dated source and output archive directories.
2. Copy the current source and deliverables into the dated archive.
3. Verify hashes or file sizes before removing the old files from active locations.
4. Create or switch to `codex/universal-ai-pm-resume-20260812`.

### Task 2: Reconstruct the source text from evidence

**Files:**
- Create: `resume/current/莫思意-AI产品经理-通用简历-文字稿.md`
- Read: `resume/evidence/2026-08-12-AI产品用户需求与结果补充.md`
- Read: `resume/evidence/2026-07-31-笔润智谈用户验证与迭代.md`
- Read: `resume/evidence/2026-08-09-季度考核工作事实台账.md`

1. Write the hiring thesis and compact skills index.
2. Rebuild笔润智谈 around user task, product functions, technical rationale, iteration, and user outcome.
3. Rebuild HearHer around interview evidence, user flow, defined risk handling, model evaluation, and external validation.
4. Compress 贝伴 to shipped functionality, error handling, and validation boundary.
5. Preserve the formal content-operations title and attribute team results correctly.
6. Run truth, hiring, interview, and human-voice gates.

### Task 3: Produce the platform plain-text version

**Files:**
- Create: `output/txt/莫思意-AI产品经理-通用简历.txt`

1. Remove Markdown syntax without changing claims.
2. Keep section headings, dates, links, and ASCII-friendly bullets for copy/paste.
3. Check that BOSS, Maimai, Liepin, and Zhaopin readers can scan it without layout dependencies.
4. Compare all material numbers and dates with the Markdown source.

### Task 4: Build the semantic single-page HTML

**Files:**
- Create: `output/html/莫思意-AI产品经理-通用简历.html`
- Reuse: `resume/assets/mosiyi-photo-v2.jpg`

1. Build a semantic A4 document with one reading column and right-aligned metadata.
2. Use a restrained blue and cool-neutral print-safe palette.
3. Keep contact details as text and all portfolio/project links as real anchors.
4. Add print CSS, page-break controls, and stable avatar sizing.
5. Inspect HTML text against Markdown and TXT.

### Task 5: Generate and validate the PDF

**Files:**
- Create: `output/pdf/莫思意-AI产品经理-通用简历.pdf`
- Create temporary renders under: `tmp/pdfs/ai-product-manager-universal/`

1. Print the local HTML with Microsoft Edge headless mode.
2. Check PDF metadata, page count, and selectable text.
3. Render every page to PNG with Poppler.
4. Inspect top hierarchy, avatar, project blocks, links, bottom balance, clipping, and glyphs.
5. Adjust HTML spacing/content only as needed and repeat until clean.

### Task 6: Update active indexes and retire the legacy active version

**Files:**
- Modify: `resume/README.md`
- Modify: `output/README.md`

1. Replace the generic targeted row with the universal mother resume and add TXT.
2. Document the dated archive and current authority.
3. Remove the old generic files from active paths only after archive verification.
4. Run the resume inventory script.

### Task 7: Add the product-clarity gate to the skill

**Files:**
- Modify: `skills/ai-resume-assistant/SKILL.md`
- Modify or create: `skills/ai-resume-assistant/references/project-narrative.md`
- Synchronize: `/Users/marshecho/.codex/skills/ai-resume-assistant/`
- Synchronize: `output/share/ai-resume-assistant/`
- Synchronize: `tmp/github-portfolio-refresh/universal-resume-assistant/skill/universal-resume-assistant/`

1. Add a first-pass product clarity gate: user/task, prior workflow, concrete feature, why AI, and highest outcome.
2. Require technology to appear only in a need-to-feature-to-mechanism-to-validation chain.
3. Treat V1/V2 as optional iteration evidence, not a default project spine.
4. Separate exposure, repeat use, user outcome, and business outcome.
5. Add anti-patterns for vague labels such as “收敛 MVP” and undefined risk levels.
6. Validate every skill package and run privacy scanning for public/share distributions.

### Task 8: Package and publish the skill update

**Files:**
- Create: `output/share/ai-resume-assistant-share-v2.zip`
- Modify GitHub repository files under: `tmp/github-portfolio-refresh/universal-resume-assistant/`

1. Build a clean share ZIP without `.DS_Store`, `__MACOSX`, or personal evidence.
2. Compare the three distributions for required rule parity.
3. Check GitHub CLI authentication and repository status.
4. Commit only the intended public skill files.
5. Push the repository branch and open a draft PR or update the existing intended branch according to repository state.

### Task 9: Final verification and handoff

1. Confirm all active links exist.
2. Confirm the old generic version is recoverable in the dated archive.
3. Confirm Markdown, TXT, HTML, and PDF agree on all material claims.
4. Confirm the PDF is one page and visually clean.
5. Report the active files, archive paths, Git branch/commit/PR, and any remaining evidence limitations.
