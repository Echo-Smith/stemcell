export const MOCK_KINDS = [
  "healthy",
  "degraded",
  "unhealthy",
  "http_error",
  "malformed_json",
  "connection_reset",
  "flaky",
] as const;

export type MockKind = (typeof MOCK_KINDS)[number];
export type ServiceStatus = "healthy" | "degraded" | "unhealthy";
export type OverallStatus = ServiceStatus | "invalid_input" | "internal_error";
export type ToolOutcome =
  | "response"
  | "timeout"
  | "network_error"
  | "protocol_error";

export interface MockScenario {
  kind: MockKind;
  delay_ms: number;
  status_code?: number;
}

export interface ServiceSpec {
  name: string;
  mock: MockScenario;
}

export interface Policy {
  timeout_ms: number;
  overall_timeout_ms: number;
  slow_threshold_ms: number;
  max_concurrency: number;
  max_attempts: 1 | 2;
  alert_threshold_error_rate: number;
}

export interface NormalizedInput {
  version: 1;
  request_id: string;
  services: ServiceSpec[];
  policy: Policy;
}

export interface ValidationFailure {
  code: "INVALID_INPUT";
  message: string;
  path: string;
  requestId: string | null;
}

export type ValidationResult =
  | { ok: true; value: NormalizedInput }
  | { ok: false; error: ValidationFailure };

export interface HealthCheckRequest {
  service: string;
  url: URL;
  timeoutMs: number;
  attempt: number;
  evidenceId: string;
  signal: AbortSignal;
}

export interface HealthCheckEvidence {
  evidence_id: string;
  service: string;
  attempt: number;
  latency_ms: number;
  http_status: number | null;
  reported_status: ServiceStatus | null;
  outcome: ToolOutcome;
  error_code: string | null;
}

export interface ServiceCheck {
  service: string;
  status: ServiceStatus;
  recovered: boolean;
  attempts: HealthCheckEvidence[];
}

export interface Diagnosis {
  severity: "info" | "warning" | "critical";
  service: string | null;
  code: string;
  evidence_refs: string[];
  recommendation: string;
}

export interface Summary {
  total: number;
  healthy: number;
  degraded: number;
  unhealthy: number;
  duration_ms: number;
}

export interface AgentOutput {
  version: 1;
  request_id: string;
  overall_status: ServiceStatus;
  summary: Summary;
  checks: ServiceCheck[];
  diagnoses: Diagnosis[];
}

export interface ErrorOutput {
  version: 1;
  request_id: string | null;
  overall_status: "invalid_input" | "internal_error";
  summary: null;
  checks: [];
  diagnoses: [];
  error: {
    code: "INVALID_INPUT" | "INTERNAL_ERROR" | "LINE_TOO_LARGE";
    message: string;
    path: string;
  };
}

export type RunnerOutput = AgentOutput | ErrorOutput;

export interface MockRegistration {
  token: string;
  url: URL;
}
