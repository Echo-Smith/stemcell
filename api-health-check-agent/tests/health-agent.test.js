import assert from "node:assert/strict";
import test from "node:test";

import { runHealthCheckAgent } from "../dist/health-agent.js";
import { MockHealthServer } from "../dist/mock-server.js";
import { validateInput } from "../dist/validation.js";

function normalize(input) {
  const result = validateInput(input);
  assert.equal(result.ok, true, result.ok ? "" : result.error.message);
  if (!result.ok) throw new Error(result.error.message);
  return result.value;
}

function inputWith(services, policy = {}) {
  return normalize({
    version: 1,
    request_id: "agent-test",
    services,
    policy: {
      timeout_ms: 200,
      overall_timeout_ms: 1000,
      slow_threshold_ms: 100,
      max_concurrency: 4,
      max_attempts: 2,
      ...policy,
    },
  });
}

async function withServer(run) {
  const server = new MockHealthServer();
  await server.start();
  try {
    return await run(server);
  } finally {
    await server.close();
  }
}

test("aggregates mixed results and preserves input order", async () => {
  const output = await withServer((server) =>
    runHealthCheckAgent(
      inputWith([
        { name: "slow-orders", mock: { kind: "healthy", delay_ms: 60 } },
        { name: "inventory", mock: { kind: "http_error", status_code: 503, delay_ms: 5 } },
        { name: "users", mock: { kind: "healthy", delay_ms: 10 } },
      ]),
      server,
    ),
  );

  assert.deepEqual(output.checks.map((check) => check.service), [
    "slow-orders",
    "inventory",
    "users",
  ]);
  assert.equal(output.overall_status, "unhealthy");
  assert.equal(output.summary.healthy, 2);
  assert.equal(output.summary.unhealthy, 1);
  assert.equal(output.checks[1].attempts.length, 2);
  assert.deepEqual(output.diagnoses.map((diagnosis) => diagnosis.code), [
    "UPSTREAM_UNAVAILABLE",
  ]);
});

test("adds aggregate alert without replacing existing service diagnoses", async () => {
  const output = await withServer((server) =>
    runHealthCheckAgent(
      inputWith([
        { name: "orders", mock: { kind: "healthy", delay_ms: 0 } },
        { name: "inventory", mock: { kind: "http_error", status_code: 503, delay_ms: 0 } },
      ]),
      server,
    ),
  );

  assert.deepEqual(output.diagnoses.map((diagnosis) => diagnosis.code), [
    "UPSTREAM_UNAVAILABLE",
    "HIGH_ERROR_RATE",
  ]);
  assert.match(output.diagnoses[1].recommendation, /50\.00%/u);
});

test("marks a flaky service as recovered but degraded", async () => {
  const output = await withServer((server) =>
    runHealthCheckAgent(
      inputWith([{ name: "payments", mock: { kind: "flaky", delay_ms: 0 } }]),
      server,
    ),
  );

  assert.equal(output.overall_status, "degraded");
  assert.equal(output.checks[0].recovered, true);
  assert.equal(output.checks[0].status, "degraded");
  assert.equal(output.checks[0].attempts.length, 2);
  assert.equal(output.diagnoses[0].code, "RECOVERED_TRANSIENT_FAILURE");
  assert.deepEqual(output.diagnoses[0].evidence_refs, [
    "check-1:attempt-1",
    "check-1:attempt-2",
  ]);
});

test("does not retry a business unhealthy response", async () => {
  const output = await withServer((server) =>
    runHealthCheckAgent(
      inputWith([{ name: "catalog", mock: { kind: "unhealthy", delay_ms: 0 } }]),
      server,
    ),
  );

  assert.equal(output.checks[0].status, "unhealthy");
  assert.equal(output.checks[0].attempts.length, 1);
  assert.equal(output.diagnoses[0].code, "SERVICE_REPORTED_UNHEALTHY");
});

test("classifies a successful but slow response as degraded", async () => {
  const output = await withServer((server) =>
    runHealthCheckAgent(
      inputWith(
        [{ name: "search", mock: { kind: "healthy", delay_ms: 80 } }],
        { timeout_ms: 200, slow_threshold_ms: 40 },
      ),
      server,
    ),
  );

  assert.equal(output.overall_status, "degraded");
  assert.equal(output.diagnoses[0].code, "SLOW_HEALTH_RESPONSE");
  assert.match(output.diagnoses[0].recommendation, /40 ms slow threshold/u);
});

test("returns a timeout result without waiting for the mock delay", async () => {
  const started = performance.now();
  const output = await withServer((server) =>
    runHealthCheckAgent(
      inputWith(
        [{ name: "reports", mock: { kind: "healthy", delay_ms: 500 } }],
        { timeout_ms: 50, slow_threshold_ms: 25 },
      ),
      server,
    ),
  );
  const elapsed = performance.now() - started;

  assert.equal(output.overall_status, "unhealthy");
  assert.equal(output.checks[0].attempts[0].outcome, "timeout");
  assert.ok(elapsed < 300, `agent took ${elapsed}ms`);
});

test("all-healthy output contains an evidence-backed no-action diagnosis", async () => {
  const output = await withServer((server) =>
    runHealthCheckAgent(
      inputWith([
        { name: "orders", mock: { kind: "healthy", delay_ms: 1 } },
        { name: "users", mock: { kind: "healthy", delay_ms: 2 } },
      ]),
      server,
    ),
  );

  assert.equal(output.overall_status, "healthy");
  assert.equal(output.diagnoses[0].code, "NO_ACTION_REQUIRED");
  assert.deepEqual(output.diagnoses[0].evidence_refs, [
    "check-1:attempt-1",
    "check-2:attempt-1",
  ]);
});
