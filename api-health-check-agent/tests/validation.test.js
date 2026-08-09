import assert from "node:assert/strict";
import test from "node:test";

import { validateInput } from "../dist/validation.js";

function validInput() {
  return {
    version: 1,
    request_id: "basic-01",
    services: [
      {
        name: "orders",
        mock: { kind: "healthy", delay_ms: 10 },
      },
    ],
  };
}

test("validates and applies policy defaults", () => {
  const result = validateInput(validInput());
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.deepEqual(result.value.policy, {
    timeout_ms: 200,
    overall_timeout_ms: 2000,
    slow_threshold_ms: 100,
    max_concurrency: 4,
    max_attempts: 2,
    alert_threshold_error_rate: 0.5,
  });
});

test("accepts inclusive error-rate alert threshold boundaries", () => {
  for (const threshold of [0, 0.25, 1]) {
    const result = validateInput({
      ...validInput(),
      policy: { alert_threshold_error_rate: threshold },
    });
    assert.equal(result.ok, true, `threshold ${threshold} should be valid`);
    if (result.ok) {
      assert.equal(result.value.policy.alert_threshold_error_rate, threshold);
    }
  }
});

test("rejects invalid error-rate alert thresholds", () => {
  for (const threshold of [-0.01, 1.01, "0.5", Number.NaN, Number.POSITIVE_INFINITY]) {
    const result = validateInput({
      ...validInput(),
      policy: { alert_threshold_error_rate: threshold },
    });
    assert.equal(result.ok, false, `threshold ${String(threshold)} should be invalid`);
    if (!result.ok) {
      assert.equal(result.error.path, "policy.alert_threshold_error_rate");
    }
  }
});

test("rejects an empty service list", () => {
  const input = validInput();
  input.services = [];
  const result = validateInput(input);
  assert.equal(result.ok, false);
  if (result.ok) return;
  assert.equal(result.error.path, "services");
});

test("rejects duplicate service names", () => {
  const input = validInput();
  input.services.push({ name: "orders", mock: { kind: "healthy", delay_ms: 0 } });
  const result = validateInput(input);
  assert.equal(result.ok, false);
  if (result.ok) return;
  assert.equal(result.error.path, "services[1].name");
});

test("rejects a slow threshold at or above the request timeout", () => {
  const result = validateInput({
    ...validInput(),
    policy: { timeout_ms: 100, slow_threshold_ms: 100 },
  });
  assert.equal(result.ok, false);
  if (result.ok) return;
  assert.equal(result.error.path, "policy.slow_threshold_ms");
});

test("requires an HTTP status code only for http_error scenarios", () => {
  const missing = validInput();
  missing.services[0].mock = { kind: "http_error", delay_ms: 0 };
  assert.equal(validateInput(missing).ok, false);

  const extra = validInput();
  extra.services[0].mock = { kind: "healthy", delay_ms: 0, status_code: 500 };
  assert.equal(validateInput(extra).ok, false);
});

test("rejects unknown fields", () => {
  const result = validateInput({ ...validInput(), extra: true });
  assert.equal(result.ok, false);
  if (result.ok) return;
  assert.equal(result.error.path, "extra");
});
