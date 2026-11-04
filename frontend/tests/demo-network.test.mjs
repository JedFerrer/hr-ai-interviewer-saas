import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";

test("demo guard refuses unowned activation", () => {
  const result = spawnSync(process.execPath, ["--import", new URL("../server/demo-network.mjs", import.meta.url).href, "-e", ""],
    { env: { ...process.env, PORTFOLIO_DEMO: "0" }, encoding: "utf8", timeout: 10000 });
  assert.notEqual(result.status, 0);
});

test("owned Node runtime permits loopback and denies external TCP, DNS and UDP", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "hr-owned-node-"));
  const frontend = path.join(root, "frontend");
  fs.mkdirSync(frontend);
  const token = crypto.randomBytes(32).toString("hex");
  fs.writeFileSync(path.join(root, ".hr-owned.json"), JSON.stringify({ purpose: "portfolio", run_id: "test", token }));
  try {
    const code = `
      import assert from 'node:assert/strict';
      import net from 'node:net';
      import dns from 'node:dns';
      import dgram from 'node:dgram';
      const server = net.createServer(socket => socket.end());
      await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
      await new Promise((resolve, reject) => {
        const client = net.createConnection({host: '127.0.0.1', port: server.address().port});
        client.on('error', reject); client.on('close', resolve);
      });
      await new Promise(resolve => server.close(resolve));
      assert.throws(() => net.createConnection({host: '192.0.2.1', port: 80}), /blocked/);
      assert.throws(() => dns.lookup('example.com', () => {}), /blocked/);
      assert.throws(() => dns.resolve4('example.com', () => {}), /blocked/);
      assert.throws(() => new dns.Resolver().resolve4('example.com', () => {}), /blocked/);
      await assert.rejects(dns.promises.lookup('example.com'), /blocked/);
      assert.throws(() => dgram.createSocket('udp4'), /blocked/);
    `;
    const result = spawnSync(process.execPath, ["--import", new URL("../server/demo-network.mjs", import.meta.url).href, "--input-type=module", "-e", code], {
      cwd: frontend, timeout: 15000, encoding: "utf8",
      env: { ...process.env, PORTFOLIO_DEMO: "1", ENVIRONMENT: "development", HR_OWNED_WORKSPACE: root, HR_DEMO_RUN_ID: "test", HR_OWNED_TOKEN: token },
    });
    assert.equal(result.status, 0, result.stderr);
    fs.writeFileSync(path.join(root, ".hr-owned.json"), '{"token":"private-marker-never-log", broken');
    const tampered = spawnSync(process.execPath, ["--import", new URL("../server/demo-network.mjs", import.meta.url).href, "-e", ""], {
      cwd: frontend, timeout: 10000, encoding: "utf8",
      env: { ...process.env, PORTFOLIO_DEMO: "1", ENVIRONMENT: "development", HR_OWNED_WORKSPACE: root },
    });
    assert.notEqual(tampered.status, 0);
    assert.ok(!tampered.stderr.includes("private-marker-never-log"));
  } finally {
    fs.rmSync(root, { recursive: true });
  }
});
