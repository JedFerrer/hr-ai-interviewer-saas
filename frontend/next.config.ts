import type { NextConfig } from "next";

// Backend URL the rewrite proxies to. Default works for local dev where
// FastAPI runs on :8001. In production set BACKEND_INTERNAL_URL to the
// internal service hostname (Kamal/Docker network), NOT a public URL.
const BACKEND_URL =
  process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8001";

const nextConfig: NextConfig = {
  // Proxy `/api/backend/*` to FastAPI so the browser only ever talks to
  // its own origin. This makes HttpOnly + SameSite=Lax cookies "just work"
  // and removes all CORS preflight friction in the browser.
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${BACKEND_URL}/:path*`,
      },
    ];
  },
};

export default nextConfig;
