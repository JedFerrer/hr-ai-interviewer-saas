export function proxyHeaders(incoming, peer, secret, host) {
  const headers = { ...incoming };
  for (const key of Object.keys(headers)) {
    if (key.startsWith("x-forwarded-") || key.startsWith("x-hr-") || ["forwarded", "connection", "upgrade", "proxy-authorization", "proxy-connection"].includes(key)) delete headers[key];
  }
  headers.host = host;
  headers["x-hr-client-ip"] = peer.startsWith("::ffff:") ? peer.slice(7) : peer;
  headers["x-hr-proxy-token"] = secret;
  return headers;
}
