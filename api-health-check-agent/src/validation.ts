import {
  MOCK_KINDS,
  type MockKind,
  type MockScenario,
  type NormalizedInput,
  type Policy,
  type ServiceSpec,
  type ValidationFailure,
  type ValidationResult,
} from "./contracts.js";

const DEFAULT_POLICY: Policy = {
  timeout_ms: 200,
  overall_timeout_ms: 2000,
  slow_threshold_ms: 100,
  max_concurrency: 4,
  max_attempts: 2,
  alert_threshold_error_rate: 0.5,
};

const INPUT_KEYS = new Set(["version", "request_id", "services", "policy"]);
const SERVICE_KEYS = new Set(["name", "mock"]);
const MOCK_KEYS = new Set(["kind", "delay_ms", "status_code"]);
const POLICY_KEYS = new Set([
  "timeout_ms",
  "overall_timeout_ms",
  "slow_threshold_ms",
  "max_concurrency",
  "max_attempts",
  "alert_threshold_error_rate",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function failure(
  message: string,
  path: string,
  requestId: string | null,
): ValidationResult {
  const error: ValidationFailure = {
    code: "INVALID_INPUT",
    message,
    path,
    requestId,
  };
  return { ok: false, error };
}

function unknownKey(
  value: Record<string, unknown>,
  allowed: Set<string>,
): string | null {
  return Object.keys(value).find((key) => !allowed.has(key)) ?? null;
}

function integerInRange(
  value: unknown,
  min: number,
  max: number,
): value is number {
  return Number.isInteger(value) && Number(value) >= min && Number(value) <= max;
}

function finiteNumberInRange(
  value: unknown,
  min: number,
  max: number,
): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= min && value <= max;
}

function requestIdHint(value: unknown): string | null {
  if (!isRecord(value) || typeof value.request_id !== "string") return null;
  const trimmed = value.request_id.trim();
  return trimmed.length > 0 && trimmed.length <= 128 ? trimmed : null;
}

export function validateInput(value: unknown): ValidationResult {
  const requestId = requestIdHint(value);
  if (!isRecord(value)) {
    return failure("input must be a JSON object", "$", requestId);
  }

  const extraInputKey = unknownKey(value, INPUT_KEYS);
  if (extraInputKey) {
    return failure(`unknown field: ${extraInputKey}`, extraInputKey, requestId);
  }
  if (value.version !== 1) {
    return failure("version must be 1", "version", requestId);
  }
  if (
    typeof value.request_id !== "string" ||
    value.request_id.trim().length === 0 ||
    value.request_id.trim().length > 128
  ) {
    return failure(
      "request_id must be a non-empty string of at most 128 characters",
      "request_id",
      requestId,
    );
  }
  const normalizedRequestId = value.request_id.trim();

  if (!Array.isArray(value.services) || value.services.length < 1 || value.services.length > 20) {
    return failure(
      "services must contain between 1 and 20 items",
      "services",
      normalizedRequestId,
    );
  }

  const services: ServiceSpec[] = [];
  const names = new Set<string>();
  for (let index = 0; index < value.services.length; index += 1) {
    const rawService = value.services[index];
    const basePath = `services[${index}]`;
    if (!isRecord(rawService)) {
      return failure("service must be an object", basePath, normalizedRequestId);
    }
    const extraServiceKey = unknownKey(rawService, SERVICE_KEYS);
    if (extraServiceKey) {
      return failure(
        `unknown field: ${extraServiceKey}`,
        `${basePath}.${extraServiceKey}`,
        normalizedRequestId,
      );
    }
    if (
      typeof rawService.name !== "string" ||
      rawService.name.trim().length === 0 ||
      rawService.name.trim().length > 64 ||
      /[\u0000-\u001f\u007f]/u.test(rawService.name)
    ) {
      return failure(
        "name must be a non-empty string of at most 64 characters without control characters",
        `${basePath}.name`,
        normalizedRequestId,
      );
    }
    const name = rawService.name.trim();
    if (names.has(name)) {
      return failure(
        "service names must be unique",
        `${basePath}.name`,
        normalizedRequestId,
      );
    }
    names.add(name);

    if (!isRecord(rawService.mock)) {
      return failure("mock must be an object", `${basePath}.mock`, normalizedRequestId);
    }
    const rawMock = rawService.mock;
    const extraMockKey = unknownKey(rawMock, MOCK_KEYS);
    if (extraMockKey) {
      return failure(
        `unknown field: ${extraMockKey}`,
        `${basePath}.mock.${extraMockKey}`,
        normalizedRequestId,
      );
    }
    if (
      typeof rawMock.kind !== "string" ||
      !MOCK_KINDS.includes(rawMock.kind as MockKind)
    ) {
      return failure(
        `kind must be one of: ${MOCK_KINDS.join(", ")}`,
        `${basePath}.mock.kind`,
        normalizedRequestId,
      );
    }
    const kind = rawMock.kind as MockKind;
    const delayMs = rawMock.delay_ms ?? 0;
    if (!integerInRange(delayMs, 0, 5000)) {
      return failure(
        "delay_ms must be an integer between 0 and 5000",
        `${basePath}.mock.delay_ms`,
        normalizedRequestId,
      );
    }
    const scenario: MockScenario = { kind, delay_ms: delayMs };
    if (kind === "http_error") {
      if (!integerInRange(rawMock.status_code, 400, 599)) {
        return failure(
          "status_code is required for http_error and must be between 400 and 599",
          `${basePath}.mock.status_code`,
          normalizedRequestId,
        );
      }
      scenario.status_code = rawMock.status_code;
    } else if (rawMock.status_code !== undefined) {
      return failure(
        "status_code is only allowed when kind is http_error",
        `${basePath}.mock.status_code`,
        normalizedRequestId,
      );
    }
    services.push({ name, mock: scenario });
  }

  const rawPolicy = value.policy ?? {};
  if (!isRecord(rawPolicy)) {
    return failure("policy must be an object", "policy", normalizedRequestId);
  }
  const extraPolicyKey = unknownKey(rawPolicy, POLICY_KEYS);
  if (extraPolicyKey) {
    return failure(
      `unknown field: ${extraPolicyKey}`,
      `policy.${extraPolicyKey}`,
      normalizedRequestId,
    );
  }

  const timeoutMs = rawPolicy.timeout_ms ?? DEFAULT_POLICY.timeout_ms;
  const overallTimeoutMs =
    rawPolicy.overall_timeout_ms ?? DEFAULT_POLICY.overall_timeout_ms;
  const slowThresholdMs =
    rawPolicy.slow_threshold_ms ?? DEFAULT_POLICY.slow_threshold_ms;
  const maxConcurrency =
    rawPolicy.max_concurrency ?? DEFAULT_POLICY.max_concurrency;
  const maxAttempts = rawPolicy.max_attempts ?? DEFAULT_POLICY.max_attempts;
  const alertThresholdErrorRate =
    rawPolicy.alert_threshold_error_rate ?? DEFAULT_POLICY.alert_threshold_error_rate;

  if (!integerInRange(timeoutMs, 20, 2000)) {
    return failure(
      "timeout_ms must be an integer between 20 and 2000",
      "policy.timeout_ms",
      normalizedRequestId,
    );
  }
  if (!integerInRange(overallTimeoutMs, 100, 5000)) {
    return failure(
      "overall_timeout_ms must be an integer between 100 and 5000",
      "policy.overall_timeout_ms",
      normalizedRequestId,
    );
  }
  if (overallTimeoutMs < timeoutMs) {
    return failure(
      "overall_timeout_ms must be greater than or equal to timeout_ms",
      "policy.overall_timeout_ms",
      normalizedRequestId,
    );
  }
  if (!integerInRange(slowThresholdMs, 1, timeoutMs - 1)) {
    return failure(
      "slow_threshold_ms must be a positive integer lower than timeout_ms",
      "policy.slow_threshold_ms",
      normalizedRequestId,
    );
  }
  if (!integerInRange(maxConcurrency, 1, 10)) {
    return failure(
      "max_concurrency must be an integer between 1 and 10",
      "policy.max_concurrency",
      normalizedRequestId,
    );
  }
  if (maxAttempts !== 1 && maxAttempts !== 2) {
    return failure(
      "max_attempts must be 1 or 2",
      "policy.max_attempts",
      normalizedRequestId,
    );
  }
  if (!finiteNumberInRange(alertThresholdErrorRate, 0, 1)) {
    return failure(
      "alert_threshold_error_rate must be a finite number between 0 and 1",
      "policy.alert_threshold_error_rate",
      normalizedRequestId,
    );
  }

  return {
    ok: true,
    value: {
      version: 1,
      request_id: normalizedRequestId,
      services,
      policy: {
        timeout_ms: timeoutMs,
        overall_timeout_ms: overallTimeoutMs,
        slow_threshold_ms: slowThresholdMs,
        max_concurrency: maxConcurrency,
        max_attempts: maxAttempts,
        alert_threshold_error_rate: alertThresholdErrorRate,
      },
    },
  };
}
