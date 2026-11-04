// Supported single-worker local entrypoint. Never trust incoming forwarding headers.
import http from "node:http";
import https from "node:https";
import { isIP } from "node:net";
import next from "next";
import nextEnv from "@next/env";
import { installSafeLogging, requestLine } from "./server/safe-logging.mjs";
const safeWrite = installSafeLogging();

import { proxyHeaders } from "./server/proxy-headers.mjs";

const demo = process.env.PORTFOLIO_DEMO === "1";
if (demo && !globalThis.portfolioProof) throw new Error("Use the owned portfolio launcher");
const dev = process.argv.includes("--dev");
process.env.NODE_ENV = dev ? "development" : "production";
if (!demo) nextEnv.loadEnvConfig(process.cwd(), dev);
const hostname = "127.0.0.1";
const port = Number(process.env.PORT || 3000);
const target = new URL(process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000");
if (!["http:", "https:"].includes(target.protocol) || target.username || target.password) throw new Error("Invalid backend URL");
const app = next({ dev, hostname, port });
await app.prepare();
const handle = app.getRequestHandler();
http.createServer((req, res) => {
  if (demo) {
    res.setHeader("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; frame-src 'self' blob:; object-src 'none'; base-uri 'self'; form-action 'self'");
    if (req.url === "/__portfolio-proof" && typeof req.headers["x-portfolio-nonce"] === "string") {
      res.end(globalThis.portfolioProof(req.headers["x-portfolio-nonce"]));
      return;
    }
  }
  const started = Date.now();
  res.on("finish", () => safeWrite(requestLine(req.method, req.url, res.statusCode, Date.now() - started)));
  if (req.url?.startsWith("/api/backend/")) {
    const secret = process.env.PROXY_AUTH_SECRET || "";
    if (secret.length < 32 || !isIP(req.socket.remoteAddress || "")) {
      res.writeHead(503, { "content-type": "application/json" });
      res.end(JSON.stringify({ detail: "Configure the shared PROXY_AUTH_SECRET in frontend and backend." }));
      return;
    }
    const headers = proxyHeaders(req.headers, req.socket.remoteAddress, secret, target.host);
    const upstream = (target.protocol === "https:" ? https : http).request({
      hostname: target.hostname, port: target.port, method: req.method,
      path: req.url.slice("/api/backend".length), headers,
    }, (response) => {
      res.writeHead(response.statusCode || 502, response.headers);
      response.pipe(res);
    });
    upstream.on("error", () => { if (!res.headersSent) res.writeHead(502); res.end(); });
    req.on("aborted", () => upstream.destroy());
    res.on("close", () => upstream.destroy());
    req.pipe(upstream);
    return;
  }
  handle(req, res).catch(() => { if (!res.headersSent) res.writeHead(500); res.end(); });
}).listen(port, hostname, () => safeWrite(`Frontend ready on loopback port ${port}\n`));
