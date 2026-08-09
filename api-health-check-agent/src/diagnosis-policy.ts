import type {
  Diagnosis,
  HealthCheckEvidence,
  Policy,
  ServiceCheck,
  ServiceStatus,
} from "./contracts.js";

export function classifyEvidence(
  evidence: HealthCheckEvidence,
  slowThresholdMs: number,
): ServiceStatus {
  if (evidence.outcome !== "response") return "unhealthy";
  if (
    evidence.http_status === null ||
    evidence.http_status < 200 ||
    evidence.http_status >= 300
  ) {
    return "unhealthy";
  }
  if (evidence.reported_status === "unhealthy" || evidence.reported_status === null) {
    return "unhealthy";
  }
  if (
    evidence.reported_status === "degraded" ||
    evidence.latency_ms > slowThresholdMs
  ) {
    return "degraded";
  }
  return "healthy";
}

export function isRetryableEvidence(evidence: HealthCheckEvidence): boolean {
  if (
    evidence.outcome === "response" &&
    evidence.http_status !== null &&
    [502, 503, 504].includes(evidence.http_status)
  ) {
    return true;
  }
  return (
    evidence.outcome === "network_error" &&
    ["ECONNRESET", "EPIPE", "EAI_AGAIN"].includes(evidence.error_code ?? "")
  );
}

export function overallStatus(checks: readonly ServiceCheck[]): ServiceStatus {
  if (checks.some((check) => check.status === "unhealthy")) return "unhealthy";
  if (checks.some((check) => check.status === "degraded")) return "degraded";
  return "healthy";
}

function lastEvidence(check: ServiceCheck): HealthCheckEvidence {
  const evidence = check.attempts.at(-1);
  if (!evidence) throw new Error(`missing evidence for service ${check.service}`);
  return evidence;
}

function evidenceFact(evidence: HealthCheckEvidence): string {
  if (evidence.outcome === "timeout") {
    return `${evidence.error_code ?? "TIMEOUT"} after ${evidence.latency_ms} ms`;
  }
  if (evidence.outcome === "network_error") {
    return `${evidence.error_code ?? "NETWORK_ERROR"} after ${evidence.latency_ms} ms`;
  }
  if (evidence.outcome === "protocol_error") {
    return `${evidence.error_code ?? "PROTOCOL_ERROR"} after ${evidence.latency_ms} ms`;
  }
  return `HTTP ${evidence.http_status ?? "unknown"}, status ${evidence.reported_status ?? "unknown"}, ${evidence.latency_ms} ms`;
}

function diagnoseUnhealthy(check: ServiceCheck, policy: Policy): Diagnosis {
  const evidence = lastEvidence(check);
  const refs = check.attempts.map((attempt) => attempt.evidence_id);

  if (evidence.outcome === "timeout") {
    return {
      severity: "critical",
      service: check.service,
      code: evidence.error_code === "OVERALL_TIMEOUT" ? "OVERALL_TIMEOUT" : "CHECK_TIMEOUT",
      evidence_refs: refs,
      recommendation: `${check.service} ${evidenceFact(evidence)}; the ${policy.timeout_ms} ms check budget was not met. Inspect saturation, dependency latency, and recent deployments before increasing the timeout.`,
    };
  }
  if (evidence.outcome === "network_error") {
    return {
      severity: "critical",
      service: check.service,
      code: "NETWORK_FAILURE",
      evidence_refs: refs,
      recommendation: `${check.service} failed with ${evidenceFact(evidence)}; inspect the instance listener, connection path, and restart history.`,
    };
  }
  if (evidence.outcome === "protocol_error") {
    return {
      severity: "critical",
      service: check.service,
      code: "INVALID_HEALTH_RESPONSE",
      evidence_refs: refs,
      recommendation: `${check.service} returned ${evidenceFact(evidence)}; verify that its health endpoint emits valid JSON with a supported status field.`,
    };
  }
  if (evidence.http_status !== null && (evidence.http_status < 200 || evidence.http_status >= 300)) {
    const unavailable = [502, 503, 504].includes(evidence.http_status);
    return {
      severity: "critical",
      service: check.service,
      code: unavailable ? "UPSTREAM_UNAVAILABLE" : "HTTP_ERROR",
      evidence_refs: refs,
      recommendation: `${check.service} returned ${evidenceFact(evidence)}; inspect instance state, upstream dependencies, and recent deployments.`,
    };
  }
  return {
    severity: "critical",
    service: check.service,
    code: "SERVICE_REPORTED_UNHEALTHY",
    evidence_refs: refs,
    recommendation: `${check.service} returned ${evidenceFact(evidence)}; inspect the service-specific health details and its critical dependencies.`,
  };
}

function diagnoseDegraded(check: ServiceCheck, policy: Policy): Diagnosis {
  const evidence = lastEvidence(check);
  const refs = check.attempts.map((attempt) => attempt.evidence_id);
  if (check.recovered) {
    const first = check.attempts[0];
    if (!first) throw new Error(`missing first attempt for service ${check.service}`);
    return {
      severity: "warning",
      service: check.service,
      code: "RECOVERED_TRANSIENT_FAILURE",
      evidence_refs: refs,
      recommendation: `${check.service} first returned ${evidenceFact(first)} and recovered with ${evidenceFact(evidence)}; keep it degraded while checking transient dependency or instance instability.`,
    };
  }
  if (evidence.reported_status === "healthy" && evidence.latency_ms > policy.slow_threshold_ms) {
    return {
      severity: "warning",
      service: check.service,
      code: "SLOW_HEALTH_RESPONSE",
      evidence_refs: refs,
      recommendation: `${check.service} returned healthy in ${evidence.latency_ms} ms, above the ${policy.slow_threshold_ms} ms slow threshold; inspect load and dependency latency.`,
    };
  }
  return {
    severity: "warning",
    service: check.service,
    code: "SERVICE_REPORTED_DEGRADED",
    evidence_refs: refs,
    recommendation: `${check.service} returned ${evidenceFact(evidence)}; inspect the service's degraded-mode reason and capacity signals.`,
  };
}

export function buildDiagnoses(
  checks: readonly ServiceCheck[],
  policy: Policy,
): Diagnosis[] {
  const diagnoses: Diagnosis[] = [];
  for (const check of checks) {
    if (check.status === "unhealthy") {
      diagnoses.push(diagnoseUnhealthy(check, policy));
    } else if (check.status === "degraded") {
      diagnoses.push(diagnoseDegraded(check, policy));
    }
  }

  if (diagnoses.length === 0) {
    const evidence = checks.map((check) => lastEvidence(check));
    const maxLatency = Math.max(...evidence.map((item) => item.latency_ms));
    diagnoses.push({
      severity: "info",
      service: null,
      code: "NO_ACTION_REQUIRED",
      evidence_refs: evidence.map((item) => item.evidence_id),
      recommendation: `All ${checks.length} services returned healthy; the maximum observed latency was ${maxLatency} ms, within the ${policy.slow_threshold_ms} ms slow threshold.`,
    });
  }

  const unhealthyChecks = checks.filter((check) => check.status === "unhealthy");
  const errorRate = unhealthyChecks.length / checks.length;
  if (
    unhealthyChecks.length > 0 &&
    errorRate >= policy.alert_threshold_error_rate
  ) {
    const evidenceRefs = unhealthyChecks.flatMap((check) =>
      check.attempts.map((attempt) => attempt.evidence_id),
    );
    diagnoses.push({
      severity: "critical",
      service: null,
      code: "HIGH_ERROR_RATE",
      evidence_refs: evidenceRefs,
      recommendation: `${unhealthyChecks.length} of ${checks.length} services are unhealthy, an actual error rate of ${(errorRate * 100).toFixed(2)}% (${errorRate.toFixed(4)}), meeting or exceeding the configured ${(policy.alert_threshold_error_rate * 100).toFixed(2)}% (${policy.alert_threshold_error_rate.toFixed(4)}) alert threshold. Prioritize shared dependencies, infrastructure health, and recent cross-service changes.`,
    });
  }
  return diagnoses;
}
