# API Health Check Agent

A deterministic, evidence-first Agent that calls a local mock health-check API, aggregates service latency and errors, applies bounded recovery, and emits diagnostic advice as JSONL.

The implementation deliberately does not use an LLM. In an offline automatic-review environment, deterministic rules make tool behavior, timeout handling, status decisions, and evidence references reproducible and auditable.

## Architecture

```text
stdin JSONL
   -> runtime validation
   -> bounded-concurrency HealthCheckAgent
      -> typed HealthCheckTool
      -> loopback-only Mock HTTP Server
   -> normalized evidence
   -> deterministic diagnosis policy
   -> stdout JSONL
```

The tool reports facts only: HTTP status, reported business status, latency, outcome, and error code. The diagnosis layer independently converts those facts into health states and recommendations. Every recommendation references evidence IDs from the same output.

## Runtime and dependencies

- Required runtime: Node.js 22.
- Evaluation command: `node main.js`.
- Runtime dependencies: none.
- Development-only dependencies: TypeScript and Node.js type declarations.
- `dist/` is committed intentionally, so evaluation does not run `npm install` or compile TypeScript.

The manifest uses the platform-supported runtime value `"node22"`.

## Run

From the ZIP root:

```bash
node main.js
```

Then send one JSON object per line to stdin. Example:

```bash
printf '%s\n' '{"version":1,"request_id":"demo","services":[{"name":"orders","mock":{"kind":"healthy","delay_ms":10}}]}' | node main.js
```

Run the supplied evaluation inputs:

```bash
node main.js < evaluation/input.jsonl
```

stdout contains JSONL results only. Operational logs go to stderr.

## Test

The tests use only Node.js built-ins at runtime:

```bash
node --test tests/*.test.js
```

Optional development build:

```bash
npm install
npm run build
```

Automatic evaluation does not need these build commands because `dist/` is included.

## Input

```json
{
  "version": 1,
  "request_id": "mixed-01",
  "services": [
    { "name": "orders", "mock": { "kind": "healthy", "delay_ms": 10 } },
    {
      "name": "inventory",
      "mock": { "kind": "http_error", "status_code": 503, "delay_ms": 5 }
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

Mock kinds:

- `healthy`
- `degraded`
- `unhealthy`
- `http_error`
- `malformed_json`
- `connection_reset`
- `flaky`

Timeout is not a fake scenario label. Set `delay_ms` above `timeout_ms` to make the HTTP request actually exceed its deadline.

See [evaluation/io_spec.md](evaluation/io_spec.md) for the complete field contract.

## Status rules

| Evidence | Result |
| --- | --- |
| 2xx + `healthy`, latency within threshold | `healthy` |
| 2xx + `healthy`, latency above slow threshold | `degraded` |
| 2xx + `degraded` | `degraded` |
| 2xx + `unhealthy` | `unhealthy` |
| Non-2xx response | `unhealthy` |
| Timeout, network error, malformed JSON, invalid status | `unhealthy` |
| Retryable failure followed by recovery | `degraded`, `recovered: true` |

Overall status is the worst service status.

After the existing per-service diagnoses are built, the Agent calculates
`unhealthy services / total services`. If at least one service is unhealthy and
the rate is greater than or equal to `alert_threshold_error_rate` (default
`0.5`), it appends a `HIGH_ERROR_RATE` diagnosis. That aggregate diagnosis
includes the actual percentage and decimal rate and references every attempt
from every unhealthy service.

## Timeout and recovery

- Per-attempt timeout is enforced by aborting the actual HTTP request.
- An overall deadline bounds the whole case, including queued checks and retries.
- Concurrency is limited and check output remains in input order.
- Only 502, 503, 504, and selected transient network failures receive one retry.
- Timeouts, 4xx, 500, malformed payloads, and business `unhealthy` responses are not retried.
- A recovered service remains degraded so its initial failure is not hidden.

## Tests included

The suite covers:

- strict input validation and defaults;
- real loopback HTTP mock behavior;
- healthy, degraded, unhealthy, HTTP error, malformed JSON, connection reset, and flaky scenarios;
- real request cancellation for delayed responses;
- conservative retry policy and recovered-as-degraded behavior;
- evidence-backed diagnoses;
- error-rate alert behavior below, at, and above the configured threshold;
- concurrent completion with stable output order;
- malformed and oversized JSONL lines;
- exactly one output object per input line;
- state isolation between consecutive cases.

`evaluation/cases.json` contains twelve review cases with expected criteria.

## Security boundaries

- Binds the Mock Server only to `127.0.0.1` on an ephemeral port.
- Does not accept user-supplied URLs, hostnames, IP addresses, paths, or credentials.
- Does not access external APIs, databases, environment secrets, or customer data.
- Does not write to the filesystem.
- Does not execute shell commands, dynamic code, or user-selected modules.
- Rejects unknown fields and applies upper bounds to services, delays, timeouts, attempts, concurrency, input-line size, and response-body size.
- stdout is reserved for protocol JSON; diagnostics and unexpected internal errors go to stderr.

## Known limitations

- The environment is synthetic and loopback-only; it does not prove production network health.
- HTTPS, certificates, authentication, DNS, service discovery, proxies, and cross-network failure modes are out of scope.
- Latency is one client-observed sample, not an SLA percentile or distributed trace.
- Error rate is calculated from one request's service snapshot; it is not a time-windowed SLO, has no hysteresis, and is not persisted between inputs.
- Diagnostic text is rule-based guidance, not proof of root cause.
- Recovery is limited to one immediate retry; no exponential backoff, jitter, circuit breaker, or distributed retry budget is implemented.
- Mock registrations are in-memory and process-local, not shared across instances.

## Submission structure

The ZIP root directly contains `README.md`, `package.json`, `main.js`, source, precompiled runtime files, tests, and `evaluation/`. It does not contain `node_modules`, caches, logs, secrets, or an extra wrapper directory.
