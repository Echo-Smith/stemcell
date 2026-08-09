# API Health Check Agent Error-Rate Alert Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the existing Agent with an optional `alert_threshold_error_rate` policy and an evidence-backed aggregate `HIGH_ERROR_RATE` diagnosis without changing existing health, timeout, retry, or service-diagnosis behavior.

**Architecture:** Add the field to the normalized `Policy` contract and strict runtime validator with a default of `0.5`. Keep all existing per-service diagnosis code untouched, then append one aggregate diagnosis when at least one service is unhealthy and `unhealthy / total >= threshold`; reference every attempt belonging to every unhealthy service.

**Tech Stack:** Existing Node.js 22-compatible ESM, TypeScript source, precompiled JavaScript, `node:test`, local Mock HTTP server, and JSONL evaluation protocol.

---

### Task 1: Capture the change with failing tests

**Files:**
- Modify: `api-health-check-agent/tests/validation.test.js`
- Modify: `api-health-check-agent/tests/diagnosis-policy.test.js`
- Modify: `api-health-check-agent/tests/health-agent.test.js`

**Steps:**
1. Assert omitted policy produces `alert_threshold_error_rate: 0.5`.
2. Assert values `0`, `0.25`, and `1` are accepted; negative, above-one, string, NaN-equivalent, and non-finite values are rejected.
3. Assert one unhealthy service out of three does not alert at `0.5`.
4. Assert one unhealthy service out of two alerts at exactly `0.5`.
5. Assert two unhealthy services out of three alert above the threshold, include `66.67%`, and cite every unhealthy attempt.
6. Assert existing service diagnosis codes remain present and ordered before the aggregate diagnosis.
7. Run the focused tests and record the expected failures before implementation.

### Task 2: Extend the typed and runtime policy contract

**Files:**
- Modify: `api-health-check-agent/src/contracts.ts`
- Modify: `api-health-check-agent/src/validation.ts`

**Steps:**
1. Add `alert_threshold_error_rate: number` to `Policy`.
2. Add the key to the strict policy allowlist.
3. Apply default `0.5` when omitted.
4. Accept only finite numbers in the inclusive range `[0, 1]`.
5. Preserve the meaning and defaults of every existing policy field.

### Task 3: Append the aggregate diagnosis

**Files:**
- Modify: `api-health-check-agent/src/diagnosis-policy.ts`

**Steps:**
1. Leave existing service diagnosis and `NO_ACTION_REQUIRED` generation unchanged.
2. Count checks whose final `status` is `unhealthy`.
3. Calculate `errorRate = unhealthyCount / checks.length`.
4. When `unhealthyCount > 0` and the rate meets or exceeds the configured threshold, append one `HIGH_ERROR_RATE` diagnosis.
5. Set `service: null`, severity `critical`, and include unhealthy count, total count, actual percentage, decimal rate, and configured threshold in the recommendation.
6. Reference every attempt from every unhealthy service, preserving check and attempt order.

### Task 4: Update evaluation and documentation

**Files:**
- Modify: `api-health-check-agent/README.md`
- Modify: `api-health-check-agent/SUBMISSION.md`
- Modify: `api-health-check-agent/evaluation/io_spec.md`
- Modify: `api-health-check-agent/evaluation/cases.json`
- Modify: `api-health-check-agent/evaluation/input.jsonl`
- Create: `api-health-check-agent/ITERATION_NOTES.md`

**Steps:**
1. Document the new field, default, inclusive bounds, calculation, append-only behavior, and zero-unhealthy guard.
2. Add below-threshold and exact-threshold evaluation cases while preserving all ten existing cases.
3. Update existing mixed-error criteria to expect the extra aggregate diagnosis under the default threshold.
4. Record model/tool use, iterations, tradeoffs, initial weaknesses, targeted changes, before/after comparison, regression evidence, and remaining risks.

### Task 5: Compile, regress, and package

**Files:**
- Modify: `api-health-check-agent/dist/*`
- Create: `output/api-health-check-agent-error-rate.zip`

**Steps:**
1. Install development dependencies only for compilation, then rebuild committed JavaScript.
2. Run all original and new tests on Node.js 22.
3. Run every evaluation input and validate line count, JSON parsing, expected alert presence, and evidence references.
4. Extract the archive into a read-only directory and repeat tests and evaluation without `node_modules`.
5. Verify ZIP root structure, mandatory evaluation files, size below 10 MB, archive integrity, and absence of secrets or personal data.
