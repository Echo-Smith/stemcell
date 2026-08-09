# API Health Check Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build, test, document, and package a deterministic API health-check Agent that calls an in-process local HTTP mock, enforces bounded timeouts, and emits evidence-backed JSONL diagnoses.

**Architecture:** A JSONL runner validates each input and passes it to a bounded-concurrency Agent. The Agent registers structured scenarios with a loopback-only Mock HTTP server, invokes a typed HTTP tool with per-attempt and overall cancellation, normalizes evidence, applies a conservative retry policy, and produces deterministic diagnoses that reference evidence IDs.

**Tech Stack:** Node.js 22-compatible ESM, TypeScript source, precompiled JavaScript deployment artifacts, Node built-in `http`, `readline`, `node:test`, and `assert`; no runtime dependencies.

---

### Task 1: Project skeleton and contracts

**Files:**
- Create: `api-health-check-agent/package.json`
- Create: `api-health-check-agent/tsconfig.json`
- Create: `api-health-check-agent/main.js`
- Create: `api-health-check-agent/src/contracts.ts`
- Test: `api-health-check-agent/tests/validation.test.js`

**Steps:**
1. Create the package metadata with ESM enabled and scripts for build, test, and evaluation smoke tests.
2. Write a failing validation test for a valid request, an empty service list, duplicate names, and invalid policy bounds.
3. Define discriminated unions for mock scenarios, policy, evidence, checks, diagnoses, valid output, and invalid-input output.
4. Run `node --test tests/validation.test.js`; expect failure until validation exists.

### Task 2: Runtime input validation

**Files:**
- Create: `api-health-check-agent/src/validation.ts`
- Test: `api-health-check-agent/tests/validation.test.js`

**Steps:**
1. Implement strict object, string, integer, enum, uniqueness, and cross-field validation without third-party libraries.
2. Apply defaults: timeout 200 ms, overall timeout 2000 ms, slow threshold 100 ms, concurrency 4, attempts 2.
3. Enforce 1-20 services, timeout 20-2000 ms, overall timeout 100-5000 ms, concurrency 1-10, attempts 1-2, response size 64 KiB, and slow threshold below timeout.
4. Return structured validation failures with stable code, path, and safe message.
5. Run validation tests and expect all to pass.

### Task 3: Local Mock HTTP server

**Files:**
- Create: `api-health-check-agent/src/mock-server.ts`
- Test: `api-health-check-agent/tests/mock-server.test.js`

**Steps:**
1. Write failing tests for healthy, degraded, unhealthy, HTTP error, malformed JSON, connection reset, flaky recovery, and delayed responses.
2. Bind only to `127.0.0.1` using port 0.
3. Register request-scoped opaque tokens instead of accepting arbitrary URLs.
4. Track flaky attempts per registration and clear request-scoped state after each case.
5. Ensure server startup and shutdown are awaitable and emit no stdout logs.
6. Run the mock-server tests and expect all to pass.

### Task 4: HTTP health-check tool

**Files:**
- Create: `api-health-check-agent/src/health-tool.ts`
- Test: `api-health-check-agent/tests/health-tool.test.js`

**Steps:**
1. Write failing tests for 2xx response parsing, non-2xx evidence, timeout cancellation, oversized bodies, malformed JSON, and connection reset.
2. Wrap `node:http.request` in a Promise and pass an `AbortSignal` into the request.
3. Measure latency with a monotonic clock.
4. Limit response bodies to 64 KiB and never follow redirects.
5. Convert expected request, network, timeout, and protocol failures into `HealthCheckEvidence`; do not throw them to the Agent.
6. Run tool tests and assert timeout completion is bounded with a tolerant wall-clock upper limit.

### Task 5: Agent orchestration and retry

**Files:**
- Create: `api-health-check-agent/src/health-agent.ts`
- Test: `api-health-check-agent/tests/health-agent.test.js`

**Steps:**
1. Write failing tests for bounded concurrency, input-order preservation, mixed status aggregation, timeout handling, non-retryable errors, retryable 503, and recovered-as-degraded behavior.
2. Implement a small worker-pool mapper with a maximum of 1-10 workers.
3. Create one overall deadline and per-attempt cancellation.
4. Retry only 502, 503, 504, and selected transient connection errors, never exceeding two attempts or the remaining deadline.
5. Keep all attempts in evidence and mark a recovered service as `degraded` with `recovered: true`.
6. Clear Mock registrations in a `finally` block.

### Task 6: Diagnosis policy

**Files:**
- Create: `api-health-check-agent/src/diagnosis-policy.ts`
- Test: `api-health-check-agent/tests/diagnosis-policy.test.js`

**Steps:**
1. Write failing tests that every recommendation references real evidence IDs and actual status, latency, or error facts.
2. Implement the status matrix from the approved design.
3. Produce service-specific codes and recommendations without claiming confirmed root cause.
4. Produce one `NO_ACTION_REQUIRED` diagnosis for an all-healthy result, citing all evidence and the observed maximum latency.
5. Run diagnosis tests and expect all to pass.

### Task 7: JSONL runner

**Files:**
- Create: `api-health-check-agent/src/jsonl-runner.ts`
- Modify: `api-health-check-agent/main.js`
- Test: `api-health-check-agent/tests/jsonl-runner.test.js`

**Steps:**
1. Write failing subprocess tests for multiple lines, blank input, malformed JSON, line-count equality, ordering, and stdout purity.
2. Read stdin line by line with a 1 MiB line limit.
3. Process lines sequentially so output order and state isolation remain explicit.
4. Emit exactly one compact JSON object per input line to stdout; write operational failures only to stderr.
5. Start the Mock server before reading and close it on EOF or process signals.
6. Run runner tests and expect all to pass.

### Task 8: Evaluation bundle and README

**Files:**
- Create: `api-health-check-agent/README.md`
- Create: `api-health-check-agent/evaluation/manifest.json`
- Create: `api-health-check-agent/evaluation/cases.json`
- Create: `api-health-check-agent/evaluation/io_spec.md`
- Create: `api-health-check-agent/evaluation/input.jsonl`

**Steps:**
1. Document architecture, commands, tool contract, status rules, retries, safety boundaries, and known limitations.
2. Set manifest version 1, runtime `node22`, and command `["node", "main.js"]`.
3. Add ten cases covering healthy, mixed 503, business unhealthy, slow, timeout, malformed response, reset, flaky recovery, concurrency order, and invalid input.
4. Explain every input/output field and the reasonableness criteria for variable timing and advice text.
5. Generate a JSONL smoke-test input from the case inputs without adding runtime dependencies.

### Task 9: Compile, verify, and package

**Files:**
- Create: `api-health-check-agent/dist/*.js`
- Create: `output/api-health-check-agent.zip`

**Steps:**
1. Compile TypeScript to committed ESM JavaScript.
2. Run `node --test`; expect zero failures.
3. Run `node main.js < evaluation/input.jsonl`; parse every stdout line as JSON and compare line counts.
4. Run the manifest command from a clean temporary extraction under a read-only directory.
5. Create a ZIP whose root directly contains README, package metadata, entrypoint, source, dist, tests, and evaluation.
6. Exclude node_modules, caches, logs, secrets, editor files, and outer directory wrappers.
7. Verify ZIP is below 10 MB and all three mandatory evaluation files parse or open successfully.

### Task 10: Submission handoff

**Files:**
- Create: `api-health-check-agent/SUBMISSION.md`

**Steps:**
1. Summarize the architecture choice and why Node.js 22 fits concurrent health checks.
2. Provide evaluator and developer run commands.
3. List safety boundaries and known limitations.
4. Link the final project directory and ZIP in the handoff.
