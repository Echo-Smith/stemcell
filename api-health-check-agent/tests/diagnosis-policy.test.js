import assert from "node:assert/strict";
import test from "node:test";

import { buildDiagnoses } from "../dist/diagnosis-policy.js";

const policy = {
  timeout_ms: 200,
  overall_timeout_ms: 2000,
  slow_threshold_ms: 100,
  max_concurrency: 4,
  max_attempts: 2,
  alert_threshold_error_rate: 0.5,
};

test("HTTP diagnosis cites the actual evidence and status", () => {
  const diagnoses = buildDiagnoses(
    [
      {
        service: "inventory",
        status: "unhealthy",
        recovered: false,
        attempts: [
          {
            evidence_id: "check-1:attempt-1",
            service: "inventory",
            attempt: 1,
            latency_ms: 12,
            http_status: 503,
            reported_status: "unhealthy",
            outcome: "response",
            error_code: "HTTP_503",
          },
        ],
      },
    ],
    policy,
  );

  assert.deepEqual(diagnoses[0].evidence_refs, ["check-1:attempt-1"]);
  assert.match(diagnoses[0].recommendation, /inventory/u);
  assert.match(diagnoses[0].recommendation, /HTTP 503/u);
  assert.match(diagnoses[0].recommendation, /12 ms/u);
});

test("timeout diagnosis cites the measured result and configured budget", () => {
  const diagnoses = buildDiagnoses(
    [
      {
        service: "reports",
        status: "unhealthy",
        recovered: false,
        attempts: [
          {
            evidence_id: "check-1:attempt-1",
            service: "reports",
            attempt: 1,
            latency_ms: 201,
            http_status: null,
            reported_status: null,
            outcome: "timeout",
            error_code: "CHECK_TIMEOUT",
          },
        ],
      },
    ],
    policy,
  );

  assert.deepEqual(diagnoses[0].evidence_refs, ["check-1:attempt-1"]);
  assert.match(diagnoses[0].recommendation, /201 ms/u);
  assert.match(diagnoses[0].recommendation, /200 ms check budget/u);
});

function check(service, index, status, attempts = 1) {
  return {
    service,
    status,
    recovered: false,
    attempts: Array.from({ length: attempts }, (_, attemptIndex) => ({
      evidence_id: `check-${index}:attempt-${attemptIndex + 1}`,
      service,
      attempt: attemptIndex + 1,
      latency_ms: 10 + attemptIndex,
      http_status: status === "unhealthy" ? 503 : 200,
      reported_status: status === "unhealthy" ? "unhealthy" : "healthy",
      outcome: "response",
      error_code: status === "unhealthy" ? "HTTP_503" : null,
    })),
  };
}

test("does not add HIGH_ERROR_RATE below the configured threshold", () => {
  const diagnoses = buildDiagnoses(
    [check("orders", 1, "unhealthy"), check("users", 2, "healthy"), check("search", 3, "healthy")],
    policy,
  );
  assert.equal(diagnoses.some((diagnosis) => diagnosis.code === "HIGH_ERROR_RATE"), false);
  assert.equal(diagnoses[0].code, "UPSTREAM_UNAVAILABLE");
});

test("appends HIGH_ERROR_RATE when the error rate exactly meets the threshold", () => {
  const diagnoses = buildDiagnoses(
    [check("orders", 1, "unhealthy", 2), check("users", 2, "healthy")],
    policy,
  );
  assert.deepEqual(diagnoses.map((diagnosis) => diagnosis.code), [
    "UPSTREAM_UNAVAILABLE",
    "HIGH_ERROR_RATE",
  ]);
  const aggregate = diagnoses[1];
  assert.deepEqual(aggregate.evidence_refs, ["check-1:attempt-1", "check-1:attempt-2"]);
  assert.match(aggregate.recommendation, /50\.00%/u);
  assert.match(aggregate.recommendation, /0\.5000/u);
});

test("HIGH_ERROR_RATE cites every unhealthy attempt and the actual rate", () => {
  const diagnoses = buildDiagnoses(
    [
      check("orders", 1, "unhealthy", 2),
      check("billing", 2, "unhealthy", 1),
      check("users", 3, "healthy"),
    ],
    policy,
  );
  const aggregate = diagnoses.at(-1);
  assert.equal(aggregate.code, "HIGH_ERROR_RATE");
  assert.deepEqual(aggregate.evidence_refs, [
    "check-1:attempt-1",
    "check-1:attempt-2",
    "check-2:attempt-1",
  ]);
  assert.match(aggregate.recommendation, /2 of 3/u);
  assert.match(aggregate.recommendation, /66\.67%/u);
  assert.match(aggregate.recommendation, /0\.6667/u);
});

test("threshold zero does not create a high-error alert when no service is unhealthy", () => {
  const diagnoses = buildDiagnoses(
    [check("orders", 1, "healthy"), check("users", 2, "healthy")],
    { ...policy, alert_threshold_error_rate: 0 },
  );
  assert.deepEqual(diagnoses.map((diagnosis) => diagnosis.code), ["NO_ACTION_REQUIRED"]);
});
