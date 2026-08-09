import { once } from "node:events";
import { createInterface } from "node:readline";
import { stdin, stdout, stderr } from "node:process";
import type { Readable, Writable } from "node:stream";

import type { ErrorOutput, RunnerOutput, ValidationFailure } from "./contracts.js";
import { runHealthCheckAgent } from "./health-agent.js";
import { MockHealthServer } from "./mock-server.js";
import { validateInput } from "./validation.js";

const MAX_LINE_BYTES = 1024 * 1024;

interface RunnerOptions {
  input?: Readable;
  output?: Writable;
  error?: Writable;
  installSignalHandlers?: boolean;
}

function errorOutput(
  requestId: string | null,
  status: "invalid_input" | "internal_error",
  code: ErrorOutput["error"]["code"],
  message: string,
  path: string,
): ErrorOutput {
  return {
    version: 1,
    request_id: requestId,
    overall_status: status,
    summary: null,
    checks: [],
    diagnoses: [],
    error: { code, message, path },
  };
}

function invalidOutput(error: ValidationFailure): ErrorOutput {
  return errorOutput(
    error.requestId,
    "invalid_input",
    "INVALID_INPUT",
    error.message,
    error.path,
  );
}

async function writeJsonLine(output: Writable, value: RunnerOutput): Promise<void> {
  const serialized = `${JSON.stringify(value)}\n`;
  if (!output.write(serialized)) await once(output, "drain");
}

function safeErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "unknown internal error";
}

export async function processLine(
  line: string,
  mockServer: MockHealthServer,
  errorStream: Writable = stderr,
): Promise<RunnerOutput> {
  if (Buffer.byteLength(line, "utf8") > MAX_LINE_BYTES) {
    return errorOutput(
      null,
      "invalid_input",
      "LINE_TOO_LARGE",
      "input line exceeds the 1 MiB limit",
      "$",
    );
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(line);
  } catch {
    return errorOutput(null, "invalid_input", "INVALID_INPUT", "line must be valid JSON", "$");
  }

  const validation = validateInput(parsed);
  if (!validation.ok) return invalidOutput(validation.error);

  try {
    return await runHealthCheckAgent(validation.value, mockServer);
  } catch (error) {
    errorStream.write(
      `[internal_error] request_id=${validation.value.request_id} message=${safeErrorMessage(error)}\n`,
    );
    return errorOutput(
      validation.value.request_id,
      "internal_error",
      "INTERNAL_ERROR",
      "the request could not be completed because of an internal error",
      "$",
    );
  }
}

export async function runCli(options: RunnerOptions = {}): Promise<void> {
  const input = options.input ?? stdin;
  const output = options.output ?? stdout;
  const errorStream = options.error ?? stderr;
  const installSignalHandlers = options.installSignalHandlers ?? true;
  const mockServer = new MockHealthServer();
  await mockServer.start();

  const lines = createInterface({ input, crlfDelay: Infinity, terminal: false });
  const onSignal = (): void => lines.close();
  if (installSignalHandlers) {
    process.once("SIGINT", onSignal);
    process.once("SIGTERM", onSignal);
  }

  try {
    for await (const line of lines) {
      const result = await processLine(line, mockServer, errorStream);
      await writeJsonLine(output, result);
    }
  } finally {
    if (installSignalHandlers) {
      process.off("SIGINT", onSignal);
      process.off("SIGTERM", onSignal);
    }
    lines.close();
    await mockServer.close();
  }
}
