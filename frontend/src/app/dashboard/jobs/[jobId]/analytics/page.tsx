"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { use } from "react";
import Link from "next/link";
import { ArrowLeft, BarChart3, Loader2 } from "lucide-react";

import { analytics as analyticsApi } from "@/lib/api";
import type {
  AnalyticsFunnel,
  AnalyticsHistogramBucket,
  AnalyticsWindow,
  JobAnalytics,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const WINDOW_OPTIONS: { value: AnalyticsWindow; label: string }[] = [
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "90d", label: "90 days" },
  { value: "all", label: "All time" },
];

const FUNNEL_STAGES: { key: keyof AnalyticsFunnel; label: string }[] = [
  { key: "applied", label: "Applied" },
  { key: "under_review", label: "Under review" },
  { key: "invited", label: "Invited" },
  { key: "started", label: "Started" },
  { key: "completed", label: "Completed" },
  { key: "shortlisted", label: "Shortlisted" },
];

// Friendly labels + accent classes for ScreeningOutcome.decision values.
// Anything else (e.g. legacy/unknown rows) falls back to neutral styling.
const DECISION_LABELS: Record<string, { label: string; tone: string }> = {
  auto_invite: { label: "Auto-invite", tone: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400" },
  review: { label: "Review", tone: "bg-amber-500/15 text-amber-600 dark:text-amber-400" },
  reject: { label: "Reject", tone: "bg-rose-500/15 text-rose-600 dark:text-rose-400" },
  error: { label: "Error", tone: "bg-muted text-muted-foreground" },
};

export default function JobAnalyticsPage({
  params,
}: {
  // Next 15 passes route params as a Promise; React.use() unwraps it.
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = use(params);
  const [windowSel, setWindowSel] = useState<AnalyticsWindow>("30d");
  const [data, setData] = useState<JobAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (w: AnalyticsWindow) => {
      setIsLoading(true);
      setError(null);
      try {
        setData(await analyticsApi.job(jobId, w));
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setIsLoading(false);
      }
    },
    [jobId],
  );

  useEffect(() => {
    let active = true;
    analyticsApi.job(jobId, windowSel).then(
      (result) => { if (active) { setData(result); setError(null); } },
      (err: unknown) => { if (active) setError(err instanceof Error ? err.message : "Failed to load"); },
    ).finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [jobId, windowSel]);

  if (isLoading && !data) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24">
        <p className="text-sm text-destructive">{error}</p>
        <Button variant="outline" onClick={() => load(windowSel)}>
          Retry
        </Button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <Link
            href={`/dashboard/jobs/${jobId}`}
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" />
            Back to job
          </Link>
          <h2 className="text-2xl font-bold tracking-tight mt-1">
            {data.job_title}
          </h2>
          <p className="text-muted-foreground text-sm">
            Analytics for the last {windowSuffix(data.window)}.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {isLoading && (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          )}
          <div className="inline-flex rounded-md border bg-card p-0.5">
            {WINDOW_OPTIONS.map((opt) => {
              const active = opt.value === windowSel;
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => { if (opt.value !== windowSel) { setIsLoading(true); setWindowSel(opt.value); } }}
                  className={`rounded-sm px-3 py-1 text-xs transition-colors ${
                    active
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent"
                  }`}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <SummaryCard
          title="Completion rate"
          value={formatPercent(data.completion_rate)}
        />
        <SummaryCard
          title="Avg score"
          value={data.avg_score != null ? data.avg_score.toFixed(1) : "—"}
        />
        <SummaryCard
          title="Avg cost / interview"
          value={formatUsd(data.avg_cost)}
        />
        <SummaryCard
          title="Total applications"
          value={data.funnel.applied.toString()}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <FunnelCard funnel={data.funnel} />
        <HistogramCard buckets={data.score_histogram} />
      </div>

      <DecisionBreakdownCard decisions={data.decision_breakdown} />
    </div>
  );
}

// --- subcomponents -----------------------------------------------------------

function SummaryCard({
  title,
  value,
}: {
  title: string;
  value: string;
}) {
  return (
    <Card>
      <CardHeader className="pb-1.5">
        <CardTitle className="text-xs font-medium text-muted-foreground">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold">{value}</div>
      </CardContent>
    </Card>
  );
}

function FunnelCard({ funnel }: { funnel: AnalyticsFunnel }) {
  const max = useMemo(
    () => Math.max(1, ...FUNNEL_STAGES.map((s) => funnel[s.key])),
    [funnel],
  );
  // Conversion vs the previous stage. Mirrors the dashboard funnel
  // exactly so percentages are comparable across views.
  const conversions: Record<string, number | null> = {
    invited: ratio(funnel.invited, funnel.applied),
    started: ratio(funnel.started, funnel.invited),
    completed: ratio(funnel.completed, funnel.started),
    shortlisted: ratio(funnel.shortlisted, funnel.completed),
  };
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Pipeline funnel</CardTitle>
        <CardDescription>
          Stage-by-stage counts. Percentages show conversion from the previous
          stage.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-2.5">
          {FUNNEL_STAGES.map((stage) => {
            const value = funnel[stage.key];
            const conv = conversions[stage.key as string] ?? null;
            const widthPct = (value / max) * 100;
            return (
              <div key={stage.key}>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="font-medium">{stage.label}</span>
                  <span className="text-muted-foreground">
                    {value}
                    {conv != null && (
                      <span className="ml-2 text-muted-foreground/70">
                        ({(conv * 100).toFixed(0)}%)
                      </span>
                    )}
                  </span>
                </div>
                <div className="h-2 rounded bg-muted overflow-hidden">
                  <div
                    className="h-full bg-primary/70 transition-all"
                    style={{ width: `${widthPct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
        {funnel.rejected > 0 && (
          <p className="mt-4 text-xs text-muted-foreground">
            {funnel.rejected} candidate
            {funnel.rejected === 1 ? "" : "s"} rejected.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function HistogramCard({ buckets }: { buckets: AnalyticsHistogramBucket[] }) {
  const max = useMemo(
    () => Math.max(1, ...buckets.map((b) => b.count)),
    [buckets],
  );
  const total = buckets.reduce((sum, b) => sum + b.count, 0);
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-muted-foreground" />
          Score distribution
        </CardTitle>
        <CardDescription>
          Overall interview score (0–10) across {total} completed interview
          {total === 1 ? "" : "s"}.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {total === 0 ? (
          <p className="text-sm text-muted-foreground italic">
            No completed interviews in this window yet.
          </p>
        ) : (
          // Bars rendered as flexbox columns so we don't pull in any
          // chart lib. Heights are percentages of the tallest bar; the
          // empty bars still show a hairline so the x-axis reads.
          <div className="flex items-end gap-1.5 h-32">
            {buckets.map((b) => {
              const pct = (b.count / max) * 100;
              return (
                <div
                  key={b.label}
                  className="flex-1 flex flex-col items-center justify-end gap-1"
                >
                  <span className="text-[10px] tabular-nums text-muted-foreground">
                    {b.count > 0 ? b.count : ""}
                  </span>
                  <div
                    className="w-full bg-primary/70 rounded-sm transition-all"
                    style={{ height: `${Math.max(2, pct)}%` }}
                    aria-label={`${b.count} candidates scored ${b.label}`}
                  />
                  <span className="text-[10px] text-muted-foreground">
                    {b.label}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function DecisionBreakdownCard({
  decisions,
}: {
  decisions: Record<string, number>;
}) {
  const entries = Object.entries(decisions).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((s, [, n]) => s + n, 0);
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Pre-screen decisions</CardTitle>
        <CardDescription>
          AI screening verdict for {total} prediction{total === 1 ? "" : "s"} in
          this window.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {entries.length === 0 ? (
          <p className="text-sm text-muted-foreground italic">
            No screening decisions recorded yet.
          </p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {entries.map(([decision, count]) => {
              const meta = DECISION_LABELS[decision] ?? {
                label: decision,
                tone: "bg-muted text-muted-foreground",
              };
              return (
                <li key={decision}>
                  <span
                    className={`inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-medium ${meta.tone}`}
                  >
                    {meta.label}: {count}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

// --- formatters --------------------------------------------------------------

function formatPercent(v: number | null): string {
  if (v == null) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

function formatUsd(v: number | null): string {
  if (v == null) return "—";
  return `$${v.toFixed(4)}`;
}

function ratio(num: number, den: number): number | null {
  if (!den) return null;
  return num / den;
}

function windowSuffix(w: AnalyticsWindow): string {
  switch (w) {
    case "7d":
      return "7 days";
    case "30d":
      return "30 days";
    case "90d":
      return "90 days";
    case "all":
      return "all time";
  }
}
