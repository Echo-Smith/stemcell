# JSONL Input and Output Specification

## Transport

The command declared in `manifest.json` is started once. The evaluator writes one JSON value per line to stdin, in case order. The program writes exactly one compact JSON object per input line to stdout, in the same order.

- Encoding: UTF-8.
- Framing: newline-delimited JSON (JSONL).
- Maximum input line: 1 MiB.
- Operational logs and unexpected stack traces: stderr only.
- Blank or malformed lines still receive one structured `invalid_input` output.
- The process continues after case-level validation or health-check failures.

## Input object

```json
{
  "version": 1,
  "request_id": "mixed-01",
  "services": [
    {
      "name": "orders",
      "mock": {
        "kind": "healthy",
        "delay_ms": 20
      }
    }
  ],
  "policy": {
    "timeout_ms": 200,
    "overall_timeout_ms": 2000,
    "slow_threshold_ms": 100,
    "max_concurrency": 4,
    "max_attempts": 2,
    "alert_threshold_error_rate": 0.5
  }
}
```

### Top-level fields

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `version` | integer | yes | Protocol version; must be `1`. |
| `request_id` | string | yes | Non-empty correlation ID, at most 128 characters. |
| `services` | array | yes | Between 1 and 20 service scenarios. Service names must be unique. |
| `policy` | object | no | Bounded execution policy; omitted fields use defaults. |

Unknown fields are rejected so contract mistakes do not silently change behavior.

### Service and mock fields

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `name` | string | yes | Service identifier, 1-64 characters, no control characters. |
| `mock.kind` | enum | yes | One of `healthy`, `degraded`, `unhealthy`, `http_error`, `malformed_json`, `connection_reset`, `flaky`. |
| `mock.delay_ms` | integer | no | Server delay from 0-5000 ms; default `0`. A delay above the client timeout creates a real timeout. |
| `mock.status_code` | integer | conditional | Required only for `http_error`; must be 400-599. |

`flaky` returns HTTP 503 on its first request and healthy on the second. `connection_reset` closes the socket without a response. Inputs cannot provide hostnames or URLs; the program generates loopback-only URLs.

### Policy fields

| Field | Default | Bounds | Meaning |
| --- | ---: | --- | --- |
| `timeout_ms` | 200 | 20-2000 | Per-attempt request deadline. |
| `overall_timeout_ms` | 2000 | 100-5000 and not below `timeout_ms` | Deadline for the entire input case. |
| `slow_threshold_ms` | 100 | positive and below `timeout_ms` | A successful response above this value is degraded. |
| `max_concurrency` | 4 | 1-10 | Maximum simultaneous service checks. |
| `max_attempts` | 2 | 1-2 | Maximum attempts per service. |
| `alert_threshold_error_rate` | 0.5 | 0-1 inclusive | Append `HIGH_ERROR_RATE` when at least one service is unhealthy and the unhealthy-service ratio meets or exceeds this value. |

Only HTTP 502/503/504 and selected transient connection failures are retried. Timeouts, 4xx, 500, malformed responses, and business `unhealthy` results are not retried.

## Successful output object

```json
{
  "version": 1,
  "request_id": "mixed-01",
  "overall_status": "unhealthy",
  "summary": {
    "total": 2,
    "healthy": 1,
    "degraded": 0,
    "unhealthy": 1,
    "duration_ms": 19
  },
  "checks": [
    {
      "service": "inventory",
      "status": "unhealthy",
      "recovered": false,
      "attempts": [
        {
          "evidence_id": "check-2:attempt-1",
          "service": "inventory",
          "attempt": 1,
          "latency_ms": 7,
          "http_status": 503,
          "reported_status": "unhealthy",
          "outcome": "response",
          "error_code": "HTTP_503"
        }
      ]
    }
  ],
  "diagnoses": [
    {
      "severity": "critical",
      "service": "inventory",
      "code": "UPSTREAM_UNAVAILABLE",
      "evidence_refs": ["check-2:attempt-1"],
      "recommendation": "inventory returned HTTP 503, status unhealthy, 7 ms; inspect instance state, upstream dependencies, and recent deployments."
    }
  ]
}
```

### Output semantics

- `overall_status`: worst service status using `healthy < degraded < unhealthy`.
- `summary`: service counts plus observed wall-clock duration for the case.
- `checks`: one per input service, always in input order.
- `recovered`: true only when an earlier retryable failure is followed by a non-unhealthy result; recovered services remain degraded.
- `attempts`: immutable evidence for every attempted HTTP call.
- `evidence_id`: stable reference used by diagnoses.
- `latency_ms`: client-observed monotonic duration; it is expected to vary slightly.
- `http_status`: null when no HTTP response was received.
- `reported_status`: parsed health payload status or null.
- `outcome`: `response`, `timeout`, `network_error`, or `protocol_error`.
- `error_code`: stable machine-readable error or null.
- `diagnoses`: evidence-backed recommendations. Every recommendation includes real observed facts and one or more `evidence_refs`.
- `HIGH_ERROR_RATE`: an additional aggregate diagnosis appended after existing service diagnoses when the unhealthy-service ratio reaches the configured threshold. It cites every attempt from every unhealthy service and states the actual error rate as both a percentage and decimal.

## Invalid input output

```json
{
  "version": 1,
  "request_id": "invalid-01",
  "overall_status": "invalid_input",
  "summary": null,
  "checks": [],
  "diagnoses": [],
  "error": {
    "code": "INVALID_INPUT",
    "message": "services must contain between 1 and 20 items",
    "path": "services"
  }
}
```

Unexpected implementation failures use `overall_status: internal_error`, a generic stdout message, and a sanitized stderr log. Case-level HTTP and protocol failures are normal successful outputs with unhealthy checks, not internal errors.

## Reasonableness criteria

Timing fields are not compared for exact equality. A reasonable output must satisfy all of the following:

1. Timeout cases return within a bounded period well below the mock delay and are never healthy.
2. Non-2xx responses, business `unhealthy`, network errors, and invalid health payloads are never healthy.
3. Slow but otherwise healthy responses are degraded when measured latency exceeds the configured threshold.
4. A retry recovery remains degraded with `recovered: true` and retains both attempts.
5. Every diagnosis references evidence IDs that exist in the same output and mentions actual observed status, latency, or error facts.
6. Check order equals service input order regardless of completion order.
7. Output line count equals input line count and every stdout line parses independently as JSON.
8. `HIGH_ERROR_RATE` is absent below the threshold and present at or above it when at least one service is unhealthy; it does not replace existing diagnosis codes.
9. A `HIGH_ERROR_RATE` diagnosis states the actual rate and references all attempts belonging to all unhealthy services.
