import { test } from "node:test";
import assert from "node:assert/strict";
import { proxyHeaders } from "../server/proxy-headers.mjs";
test("proxy overwrites attacker identity and strips forwarding credentials", () => {
 const result = proxyHeaders({ "x-forwarded-for":"attacker", "x-hr-client-ip":"forged", "x-hr-proxy-token":"forged", forwarded:"forged", cookie:"fixture-cookie" }, "::ffff:192.0.2.1", "owned-secret", "127.0.0.1:8000");
 assert.equal(result["x-hr-client-ip"], "192.0.2.1");
 assert.equal(result["x-hr-proxy-token"], "owned-secret");
 assert.equal(result["x-forwarded-for"], undefined);
 assert.equal(result.forwarded, undefined);
 assert.equal(result.cookie, "fixture-cookie");
});

import { requestLine } from "../server/safe-logging.mjs";
test("supported server logs omit tokens and queries on success and errors", () => {
 for (const path of ["/accept-invite/SECRET?cookie=SECRET", "/api/backend/auth/invite/SECRET", "/report/SECRET", "/unknown/SECRET?token=SECRET"]) {
  const line = requestLine("GET", path, 500, 12);
  assert.ok(!line.includes("SECRET"));
  assert.ok(line.includes("status=500 duration_ms=12"));
 }
});
