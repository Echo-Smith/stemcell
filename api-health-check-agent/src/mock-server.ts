import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";
import type { AddressInfo } from "node:net";

import type { MockRegistration, MockScenario } from "./contracts.js";

interface ScenarioState {
  scenario: MockScenario;
  calls: number;
}

export class MockHealthServer {
  private server: Server | null = null;
  private readonly scenarios = new Map<string, ScenarioState>();
  private tokenCounter = 0;
  private port: number | null = null;

  async start(): Promise<void> {
    if (this.server) return;
    const server = createServer((request, response) => this.handle(request, response));
    await new Promise<void>((resolve, reject) => {
      const onError = (error: Error): void => reject(error);
      server.once("error", onError);
      server.listen(0, "127.0.0.1", () => {
        server.off("error", onError);
        resolve();
      });
    });
    const address = server.address() as AddressInfo | null;
    if (!address) {
      server.close();
      throw new Error("Mock server did not expose a listening address");
    }
    this.server = server;
    this.port = address.port;
  }

  register(scenario: MockScenario): MockRegistration {
    if (!this.server || this.port === null) {
      throw new Error("Mock server must be started before registering scenarios");
    }
    this.tokenCounter += 1;
    const token = `scenario-${this.tokenCounter}`;
    this.scenarios.set(token, {
      scenario: { ...scenario },
      calls: 0,
    });
    return {
      token,
      url: new URL(`http://127.0.0.1:${this.port}/health/${token}`),
    };
  }

  clear(tokens: readonly string[]): void {
    for (const token of tokens) this.scenarios.delete(token);
  }

  async close(): Promise<void> {
    const server = this.server;
    this.server = null;
    this.port = null;
    this.scenarios.clear();
    if (!server) return;
    await new Promise<void>((resolve, reject) => {
      server.close((error) => (error ? reject(error) : resolve()));
    });
  }

  private handle(request: IncomingMessage, response: ServerResponse): void {
    if (request.method !== "GET" || !request.url) {
      this.sendJson(response, 405, { status: "unhealthy", error: "method_not_allowed" });
      return;
    }

    const url = new URL(request.url, "http://127.0.0.1");
    const match = /^\/health\/([^/]+)$/u.exec(url.pathname);
    const state = match?.[1] ? this.scenarios.get(match[1]) : undefined;
    if (!state) {
      this.sendJson(response, 404, { status: "unhealthy", error: "unknown_scenario" });
      return;
    }

    state.calls += 1;
    const timer = setTimeout(() => {
      if (response.destroyed) return;
      this.respondForScenario(request, response, state);
    }, state.scenario.delay_ms);
    response.once("close", () => clearTimeout(timer));
  }

  private respondForScenario(
    request: IncomingMessage,
    response: ServerResponse,
    state: ScenarioState,
  ): void {
    const { scenario, calls } = state;
    switch (scenario.kind) {
      case "healthy":
        this.sendJson(response, 200, { status: "healthy" });
        return;
      case "degraded":
        this.sendJson(response, 200, { status: "degraded" });
        return;
      case "unhealthy":
        this.sendJson(response, 200, { status: "unhealthy" });
        return;
      case "http_error":
        this.sendJson(response, scenario.status_code ?? 500, {
          status: "unhealthy",
          error: `simulated_http_${scenario.status_code ?? 500}`,
        });
        return;
      case "malformed_json":
        response.writeHead(200, { "content-type": "application/json" });
        response.end('{"status":');
        return;
      case "connection_reset":
        request.socket.destroy();
        return;
      case "flaky":
        if (calls === 1) {
          this.sendJson(response, 503, {
            status: "unhealthy",
            error: "simulated_transient_failure",
          });
        } else {
          this.sendJson(response, 200, { status: "healthy" });
        }
        return;
    }
  }

  private sendJson(response: ServerResponse, statusCode: number, body: unknown): void {
    const payload = JSON.stringify(body);
    response.writeHead(statusCode, {
      "content-type": "application/json; charset=utf-8",
      "content-length": Buffer.byteLength(payload),
      connection: "close",
    });
    response.end(payload);
  }
}
