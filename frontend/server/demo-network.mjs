// Imported only by the owned launcher. Reject external connections before DNS.
import net from "node:net";
import dns from "node:dns";
import dgram from "node:dgram";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { syncBuiltinESMExports } from "node:module";
if (process.env.PORTFOLIO_DEMO !== "1") throw new Error("Owned demo activation required");
const root = fs.realpathSync(process.env.HR_OWNED_WORKSPACE || "");
let marker;
try {
  marker = JSON.parse(fs.readFileSync(path.join(root, ".hr-owned.json"), "utf8"));
} catch {
  throw new Error("Invalid demo ownership record");
}
if (marker.purpose !== "portfolio" || marker.run_id !== process.env.HR_DEMO_RUN_ID ||
    !marker.token || marker.token !== process.env.HR_OWNED_TOKEN ||
    process.cwd() !== path.join(root, "frontend") || process.env.ENVIRONMENT !== "development") {
  throw new Error("Invalid demo ownership");
}
const local = (host) => host === "127.0.0.1" || host === "::1";
const connect = net.Socket.prototype.connect;
net.Socket.prototype.connect = function (...args) {
  const normalized = Array.isArray(args[0]) ? args[0] : args;
  const options = typeof normalized[0] === "object" ? normalized[0] : { host: typeof normalized[1] === "string" ? normalized[1] : "localhost" };
  if (options.path || !local(options.host || "localhost")) throw new Error("Demo outbound network blocked");
  return connect.apply(this, args);
};
const lookup = dns.lookup;
dns.lookup = function (host, ...args) {
  if (!local(host)) throw new Error("Demo external DNS blocked");
  return lookup.call(this, host, ...args);
};
dgram.createSocket = () => { throw new Error("Demo UDP blocked"); };
const denyDns = () => { throw new Error("Demo external DNS blocked"); };
for (const object of [dns, dns.promises, dns.Resolver.prototype, dns.promises.Resolver.prototype]) {
  for (const name of Object.getOwnPropertyNames(object)) {
    if (name.startsWith("resolve") || name === "reverse" || name === "lookupService") object[name] = denyDns;
  }
}
const asyncLookup = dns.promises.lookup;
dns.promises.lookup = async (host, ...args) => {
  if (!local(host)) throw new Error("Demo external DNS blocked");
  return asyncLookup(host, ...args);
};
syncBuiltinESMExports();
// Challenge is private server state, never passed into browser bundles.
globalThis.portfolioProof = (nonce) => crypto.createHmac("sha256", marker.token).update(nonce).digest("hex");
