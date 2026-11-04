export function requestLine(method, url, status, milliseconds) {
  const path = (url || "").split("?", 1)[0];
  const prefix = ["/api/backend/", "/accept-invite/", "/interview/", "/report/", "/dashboard/", "/_next/"].find((value) => path.startsWith(value));
  const route = prefix ? `${prefix}[redacted]` : ["/", "/login", "/signup", "/dashboard"].includes(path) ? path : "[unmatched]";
  return `${method} ${route} status=${status} duration_ms=${milliseconds}\n`;
}

export function installSafeLogging() {
  const write = process.stdout.write.bind(process.stdout);
  // Next/provider errors can embed a request URL or props. Runtime diagnostics
  // are limited to our request/status/timing records; build checks remain verbose.
  for (const stream of [process.stdout, process.stderr]) {
    stream.write = (_chunk, encoding, callback) => {
      const done = typeof encoding === "function" ? encoding : callback;
      if (done) done();
      return true;
    };
  }
  process.on("uncaughtException", () => { write("Frontend fatal error; run the build/checks for diagnostics.\n"); process.exit(1); });
  process.on("unhandledRejection", () => { write("Frontend rejected operation; no request content logged.\n"); });
  return write;
}
