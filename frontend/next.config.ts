import type { NextConfig } from "next";

// API forwarding is handled by server.mjs, which has access to the real socket
// peer and overwrites untrusted forwarding headers. Use npm run dev/start.
const nextConfig: NextConfig = { logging: false, poweredByHeader: false };
export default nextConfig;
