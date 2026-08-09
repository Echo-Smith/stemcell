import type {
  AgentOutput,
  HealthCheckEvidence,
  NormalizedInput,
  ServiceCheck,
  ServiceSpec,
} from "./contracts.js";
import {
  buildDiagnoses,
  classifyEvidence,
  isRetryableEvidence,
  overallStatus,
} from "./diagnosis-policy.js";
import { checkHealth } from "./health-tool.js";
import { MockHealthServer } from "./mock-server.js";

type ToolFunction = typeof checkHealth;

async function mapWithConcurrency<T, R>(
  items: readonly T[],
  concurrency: number,
  worker: (item: T, index: number) => Promise<R>,
): Promise<R[]> {
  const results = new Array<R>(items.length);
  let cursor = 0;

  async function runWorker(): Promise<void> {
    while (true) {
      const index = cursor;
      cursor += 1;
      if (index >= items.length) return;
      const item = items[index];
      if (item === undefined) return;
      results[index] = await worker(item, index);
    }
  }

  const workers = Array.from(
    { length: Math.min(concurrency, items.length) },
    () => runWorker(),
  );
  await Promise.all(workers);
  return results;
}

function recoveredSuccessfully(attempts: readonly HealthCheckEvidence[], slowThresholdMs: number): boolean {
  if (attempts.length < 2) return false;
  const last = attempts.at(-1);
  return last ? classifyEvidence(last, slowThresholdMs) !== "unhealthy" : false;
}

export async function runHealthCheckAgent(
  input: NormalizedInput,
  mockServer: MockHealthServer,
  tool: ToolFunction = checkHealth,
): Promise<AgentOutput> {
  const started = performance.now();
  const registrations = input.services.map((service) => mockServer.register(service.mock));
  const tokens = registrations.map((registration) => registration.token);
  const overallController = new AbortController();
  const overallTimer = setTimeout(
    () => overallController.abort(new Error("overall timeout")),
    input.policy.overall_timeout_ms,
  );

  async function checkService(service: ServiceSpec, index: number): Promise<ServiceCheck> {
    const registration = registrations[index];
    if (!registration) throw new Error(`missing mock registration at index ${index}`);
    const attempts: HealthCheckEvidence[] = [];

    for (let attempt = 1; attempt <= input.policy.max_attempts; attempt += 1) {
      const evidence = await tool({
        service: service.name,
        url: registration.url,
        timeoutMs: input.policy.timeout_ms,
        attempt,
        evidenceId: `check-${index + 1}:attempt-${attempt}`,
        signal: overallController.signal,
      });
      attempts.push(evidence);
      if (
        attempt >= input.policy.max_attempts ||
        overallController.signal.aborted ||
        !isRetryableEvidence(evidence)
      ) {
        break;
      }
    }

    const finalEvidence = attempts.at(-1);
    if (!finalEvidence) throw new Error(`no evidence produced for ${service.name}`);
    const recovered = recoveredSuccessfully(attempts, input.policy.slow_threshold_ms);
    const classified = classifyEvidence(finalEvidence, input.policy.slow_threshold_ms);
    return {
      service: service.name,
      status: recovered ? "degraded" : classified,
      recovered,
      attempts,
    };
  }

  try {
    const checks = await mapWithConcurrency(
      input.services,
      input.policy.max_concurrency,
      checkService,
    );
    const status = overallStatus(checks);
    const summary = {
      total: checks.length,
      healthy: checks.filter((check) => check.status === "healthy").length,
      degraded: checks.filter((check) => check.status === "degraded").length,
      unhealthy: checks.filter((check) => check.status === "unhealthy").length,
      duration_ms: Math.max(0, Math.round(performance.now() - started)),
    };
    return {
      version: 1,
      request_id: input.request_id,
      overall_status: status,
      summary,
      checks,
      diagnoses: buildDiagnoses(checks, input.policy),
    };
  } finally {
    clearTimeout(overallTimer);
    mockServer.clear(tokens);
  }
}
