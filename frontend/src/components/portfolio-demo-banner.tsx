"use client";

import { useEffect, useRef } from "react";

/** Demo-only observation for reproducible offline browser verification.
 * Records origins/counts, never URLs, tokens, headers or response contents.
 */
export function PortfolioDemoBanner() {
  const banner = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const updateHeight = () => {
      document.documentElement.style.setProperty(
        "--portfolio-demo-height", `${banner.current?.getBoundingClientRect().height ?? 0}px`,
      );
    };
    const resize = new ResizeObserver(updateHeight);
    if (banner.current) resize.observe(banner.current);
    updateHeight();
    const origins = new Set<string>();
    const counts = { resources: 0, blocked: 0 };
    const record = (entries: PerformanceEntry[]) => {
      for (const entry of entries) {
        origins.add(new URL(entry.name, location.href).origin);
        counts.resources++;
      }
      if (banner.current) {
        banner.current.dataset.resourceOrigins = JSON.stringify([...origins].sort());
        banner.current.dataset.resourceCount = String(counts.resources);
      }
    };
    const observer = new PerformanceObserver((list) => record(list.getEntries()));
    observer.observe({ type: "resource", buffered: true });
    const violation = () => {
      counts.blocked++;
      if (banner.current) banner.current.dataset.blockedRequests = String(counts.blocked);
    };
    document.addEventListener("securitypolicyviolation", violation);
    return () => {
      resize.disconnect();
      document.documentElement.style.removeProperty("--portfolio-demo-height");
      observer.disconnect();
      document.removeEventListener("securitypolicyviolation", violation);
    };
  }, []);
  return (
    <div ref={banner} data-testid="portfolio-demo" data-blocked-requests="0"
      role="status" className="sticky top-0 z-50 bg-amber-100 p-3 text-center text-sm text-amber-950">
      Fictional portfolio demo · AI results are deterministic simulations · Email is captured locally
    </div>
  );
}
