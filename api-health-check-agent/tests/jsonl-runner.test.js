import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import test from "node:test";

function healthyInput(requestId, service = "orders") {
  return {
    version: 1,
    request_id: requestId,
    services: [{ name: service, mock: { kind: "healthy", delay_ms: 0 } }],
  };
}

function runCli(lines) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, ["main.js"], {
      cwd: new URL("..", import.meta.url),
      stdio: ["pipe", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk) => (stdout += chunk));
    child.stderr.on("data", (chunk) => (stderr += chunk));
    child.on("error", reject);
    child.on("close", (code) => resolve({ code, stdout, stderr }));
    child.stdin.end(lines.join("\n"));
  });
}

test("emits exactly one JSON object per input line and preserves order", async () => {
  const inputLines = [
    JSON.stringify(healthyInput("first", "orders")),
    "not-json",
    "",
    JSON.stringify(healthyInput("last", "users")),
  ];
  const result = await runCli(inputLines);
  assert.equal(result.code, 0);
  const outputLines = result.stdout.trimEnd().split("\n");
  assert.equal(outputLines.length, inputLines.length);
  const outputs = outputLines.map((line) => JSON.parse(line));
  assert.deepEqual(outputs.map((output) => output.request_id), ["first", null, null, "last"]);
  assert.deepEqual(outputs.map((output) => output.overall_status), [
    "healthy",
    "invalid_input",
    "invalid_input",
    "healthy",
  ]);
  assert.equal(result.stderr, "");
});

test("keeps mock state isolated between JSONL cases", async () => {
  const flaky = {
    version: 1,
    request_id: "flaky",
    services: [{ name: "payments", mock: { kind: "flaky", delay_ms: 0 } }],
  };
  const result = await runCli([JSON.stringify(flaky), JSON.stringify({ ...flaky, request_id: "flaky-2" })]);
  const outputs = result.stdout.trim().split("\n").map((line) => JSON.parse(line));
  assert.equal(outputs.length, 2);
  assert.equal(outputs[0].checks[0].recovered, true);
  assert.equal(outputs[1].checks[0].recovered, true);
  assert.equal(outputs[0].checks[0].attempts.length, 2);
  assert.equal(outputs[1].checks[0].attempts.length, 2);
});

test("rejects an oversized line without crashing", async () => {
  const oversized = `{"padding":"${"x".repeat(1024 * 1024)}"}`;
  const result = await runCli([oversized, JSON.stringify(healthyInput("after-large"))]);
  const outputs = result.stdout.trim().split("\n").map((line) => JSON.parse(line));
  assert.equal(outputs[0].error.code, "LINE_TOO_LARGE");
  assert.equal(outputs[1].request_id, "after-large");
  assert.equal(outputs[1].overall_status, "healthy");
});
