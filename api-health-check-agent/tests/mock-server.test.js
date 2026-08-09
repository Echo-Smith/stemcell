import assert from "node:assert/strict";
import { request as httpRequest } from "node:http";
import test from "node:test";

import { MockHealthServer } from "../dist/mock-server.js";

function get(url) {
  return new Promise((resolve, reject) => {
    const request = httpRequest(url, { method: "GET" }, (response) => {
      const chunks = [];
      response.on("data", (chunk) => chunks.push(Buffer.from(chunk)));
      response.on("end", () => {
        resolve({
          status: response.statusCode,
          body: Buffer.concat(chunks).toString("utf8"),
        });
      });
    });
    request.on("error", reject);
    request.end();
  });
}

test("serves registered health scenarios over loopback HTTP", async (t) => {
  const server = new MockHealthServer();
  await server.start();
  t.after(() => server.close());

  const healthy = server.register({ kind: "healthy", delay_ms: 0 });
  const degraded = server.register({ kind: "degraded", delay_ms: 0 });
  const error = server.register({ kind: "http_error", delay_ms: 0, status_code: 503 });

  assert.deepEqual(await get(healthy.url), {
    status: 200,
    body: '{"status":"healthy"}',
  });
  assert.deepEqual(await get(degraded.url), {
    status: 200,
    body: '{"status":"degraded"}',
  });
  assert.equal((await get(error.url)).status, 503);
});

test("flaky scenario fails once and then recovers", async (t) => {
  const server = new MockHealthServer();
  await server.start();
  t.after(() => server.close());
  const registration = server.register({ kind: "flaky", delay_ms: 0 });

  assert.equal((await get(registration.url)).status, 503);
  assert.deepEqual(await get(registration.url), {
    status: 200,
    body: '{"status":"healthy"}',
  });
});

test("connection_reset destroys the socket", async (t) => {
  const server = new MockHealthServer();
  await server.start();
  t.after(() => server.close());
  const registration = server.register({ kind: "connection_reset", delay_ms: 0 });

  await assert.rejects(() => get(registration.url), /socket hang up|ECONNRESET/u);
});
