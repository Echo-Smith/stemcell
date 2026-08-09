import { request as httpRequest } from "node:http";

import type {
  HealthCheckEvidence,
  HealthCheckRequest,
  ServiceStatus,
} from "./contracts.js";

const MAX_RESPONSE_BYTES = 64 * 1024;
const VALID_REPORTED_STATUSES = new Set<ServiceStatus>([
  "healthy",
  "degraded",
  "unhealthy",
]);

function elapsedMs(start: number): number {
  return Math.max(0, Math.round(performance.now() - start));
}

function networkCode(error: unknown): string {
  if (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    typeof error.code === "string"
  ) {
    return error.code;
  }
  return "NETWORK_ERROR";
}

export function checkHealth(input: HealthCheckRequest): Promise<HealthCheckEvidence> {
  const start = performance.now();
  if (input.signal.aborted) {
    return Promise.resolve({
      evidence_id: input.evidenceId,
      service: input.service,
      attempt: input.attempt,
      latency_ms: 0,
      http_status: null,
      reported_status: null,
      outcome: "timeout",
      error_code: "OVERALL_TIMEOUT",
    });
  }

  return new Promise<HealthCheckEvidence>((resolve) => {
    const controller = new AbortController();
    let timedOut = false;
    let overallAborted = false;
    let settled = false;

    const finish = (evidence: HealthCheckEvidence): void => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      input.signal.removeEventListener("abort", onOverallAbort);
      resolve(evidence);
    };

    const baseEvidence = (): Pick<
      HealthCheckEvidence,
      "evidence_id" | "service" | "attempt" | "latency_ms"
    > => ({
      evidence_id: input.evidenceId,
      service: input.service,
      attempt: input.attempt,
      latency_ms: elapsedMs(start),
    });

    const onOverallAbort = (): void => {
      overallAborted = true;
      controller.abort(new Error("overall timeout"));
    };
    input.signal.addEventListener("abort", onOverallAbort, { once: true });

    const timer = setTimeout(() => {
      timedOut = true;
      controller.abort(new Error("request timeout"));
    }, input.timeoutMs);

    const request = httpRequest(
      input.url,
      {
        method: "GET",
        headers: { accept: "application/json", connection: "close" },
        signal: controller.signal,
      },
      (response) => {
        const statusCode = response.statusCode ?? null;
        const chunks: Buffer[] = [];
        let size = 0;

        response.on("data", (chunk: Buffer | string) => {
          if (settled) return;
          const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
          size += buffer.length;
          if (size > MAX_RESPONSE_BYTES) {
            response.destroy();
            finish({
              ...baseEvidence(),
              http_status: statusCode,
              reported_status: null,
              outcome: "protocol_error",
              error_code: "RESPONSE_TOO_LARGE",
            });
            return;
          }
          chunks.push(buffer);
        });

        response.once("aborted", () => {
          finish({
            ...baseEvidence(),
            http_status: statusCode,
            reported_status: null,
            outcome: "network_error",
            error_code: "ECONNRESET",
          });
        });

        response.once("end", () => {
          if (settled) return;
          const rawBody = Buffer.concat(chunks).toString("utf8");
          let parsed: unknown;
          try {
            parsed = JSON.parse(rawBody);
          } catch {
            if (statusCode !== null && (statusCode < 200 || statusCode >= 300)) {
              finish({
                ...baseEvidence(),
                http_status: statusCode,
                reported_status: null,
                outcome: "response",
                error_code: `HTTP_${statusCode}`,
              });
            } else {
              finish({
                ...baseEvidence(),
                http_status: statusCode,
                reported_status: null,
                outcome: "protocol_error",
                error_code: "INVALID_JSON",
              });
            }
            return;
          }

          let reportedStatus: ServiceStatus | null = null;
          if (
            typeof parsed === "object" &&
            parsed !== null &&
            "status" in parsed &&
            typeof parsed.status === "string" &&
            VALID_REPORTED_STATUSES.has(parsed.status as ServiceStatus)
          ) {
            reportedStatus = parsed.status as ServiceStatus;
          }

          if (statusCode === null) {
            finish({
              ...baseEvidence(),
              http_status: null,
              reported_status: reportedStatus,
              outcome: "protocol_error",
              error_code: "MISSING_HTTP_STATUS",
            });
          } else if (statusCode < 200 || statusCode >= 300) {
            finish({
              ...baseEvidence(),
              http_status: statusCode,
              reported_status: reportedStatus,
              outcome: "response",
              error_code: `HTTP_${statusCode}`,
            });
          } else if (reportedStatus === null) {
            finish({
              ...baseEvidence(),
              http_status: statusCode,
              reported_status: null,
              outcome: "protocol_error",
              error_code: "INVALID_STATUS",
            });
          } else {
            finish({
              ...baseEvidence(),
              http_status: statusCode,
              reported_status: reportedStatus,
              outcome: "response",
              error_code: null,
            });
          }
        });
      },
    );

    request.once("error", (error) => {
      if (timedOut || overallAborted) {
        finish({
          ...baseEvidence(),
          http_status: null,
          reported_status: null,
          outcome: "timeout",
          error_code: overallAborted ? "OVERALL_TIMEOUT" : "CHECK_TIMEOUT",
        });
      } else {
        finish({
          ...baseEvidence(),
          http_status: null,
          reported_status: null,
          outcome: "network_error",
          error_code: networkCode(error),
        });
      }
    });

    request.end();
  });
}
