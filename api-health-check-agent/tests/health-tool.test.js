import assert from "node:assert/strict";
import test from "node:test";

import { checkHealth } from "../dist/health-tool.js";
import { MockHealthServer } from "../dist/mock-server.js";

function requestFor(registration, overrides = {}) {
  return {
    service: "orders",
    url: registration.url,
    timeoutMs: 200,
    attempt: 1,
    evidenceId: "check-1:attempt-1",
    signal: new AbortController().signal,
    ...overrides,
  };
}

test("returns typed evidence for a healthy response", async (t) => {
  const server = new MockHealthServer();
  await server.start();
  t.after(() => server.close());
  const registration = server.register({ kind: "healthy", delay_ms: 10 });

  const result = await checkHealth(requestFor(registration));
  assert.equal(result.outcome, "response");
  assert.equal(result.http_status, 200);
  assert.equal(result.reported_status, "healthy");
  assert.equal(result.error_code, null);
  assert.ok(result.latency_ms >= 0);
});

test("does not treat an HTTP error as healthy", async (t) => {
  const server = new MockHealthServer();
  await server.start();
  t.after(() => server.close());
  const registration = server.register({
    kind: "http_error",
    status_code: 500,
    delay_ms: 0,
  });

  const result = await checkHealth(requestFor(registration));
  assert.equal(result.outcome, "response");
  assert.equal(result.http_status, 500);
  assert.equal(result.error_code, "HTTP_500");
});

test("reports malformed JSON as a protocol error", async (t) => {
  const server = new MockHealthServer();
  await server.start();
  t.after(() => server.close());
  const registration = server.register({ kind: "malformed_json", delay_ms: 0 });

  const result = await checkHealth(requestFor(registration));
  assert.equal(result.outcome, "protocol_error");
  assert.equal(result.error_code, "INVALID_JSON");
});

test("aborts a slow request within a bounded duration", async (t) => {
  const server = new MockHealthServer();
  await server.start();
  t.after(() => server.close());
  const registration = server.register({ kind: "healthy", delay_ms: 500 });

  const started = performance.now();
  const result = await checkHealth(requestFor(registration, { timeoutMs: 50 }));
  const duration = performance.now() - started;

  assert.equal(result.outcome, "timeout");
  assert.equal(result.error_code, "CHECK_TIMEOUT");
  assert.ok(duration < 300, `request took ${duration}ms`);
});

test("normalizes connection resets as network evidence", async (t) => {
  const server = new MockHealthServer();
  await server.start();
  t.after(() => server.close());
  const registration = server.register({ kind: "connection_reset", delay_ms: 0 });

  const result = await checkHealth(requestFor(registration));
  assert.equal(result.outcome, "network_error");
  assert.equal(result.error_code, "ECONNRESET");
});
