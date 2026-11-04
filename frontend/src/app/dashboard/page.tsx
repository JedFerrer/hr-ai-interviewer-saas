"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowRight,
  Briefcase,
  Clock,
  DollarSign,
  Loader2,
  PartyPopper,
  Plus,
  TrendingUp,
  Users,
} from "lucide-react";

import { analytics as analyticsApi } from "@/lib/api";
import { parseApiDate } from "@/lib/dates";
import type {
  AnalyticsCalibration,
  AnalyticsFunnel,
  AnalyticsJobHealthRow,
  AnalyticsKPIs,
  AnalyticsOverview,
  AnalyticsTrendPoint,
  AnalyticsWindow,
} from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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

const FUNNEL_STAGES: {
  key: keyof AnalyticsFunnel;
  label: string;
}[] = [
  { key: "applied",      label: "Applied"      },
  { key: "under_review", label: "Under review" },
  { key: "invited",      label: "Invited"      },
  { key: "started",      label: "Started"      },
  { key: "completed",    label: "Completed"    },
  { key: "shortlisted",  label: "Shortlisted"  },
];

export default function DashboardPage() {
  const { user } = useAuth();
  const [windowSel, setWindowSel] = useState<AnalyticsWindow>("30d");
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (w: AnalyticsWindow) => {
    setIsLoading(true);
    setError(null);
    try {
      const overview = await analyticsApi.overview(w);
      setData(overview);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    analyticsApi.overview(windowSel).then(
      (result) => { if (active) { setData(result); setError(null); } },
      (err: unknown) => { if (active) setError(err instanceof Error ? err.message : "Failed to load"); },
    ).finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [windowSel]);

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
      <Header
        userName={user?.name ?? null}
        windowSel={windowSel}
        onWindowChange={(value) => { if (value !== windowSel) { setIsLoading(true); setWindowSel(value); } }}
        loading={isLoading}
      />

      <Section title="Key performance indicators">
        <KPIGrid kpis={data.kpis} window={windowSel} trends={data.trends} />
      </Section>

      <Section title="Pipeline & activity">
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            <FunnelCard funnel={data.funnel} window={windowSel} />
            <ActivityCard trends={data.trends} window={windowSel} />
          </div>
          <div className="space-y-6">
            <ActionNeededCard buckets={data.action_needed} />
            <CalibrationCard calibration={data.calibration} window={windowSel} />
          </div>
        </div>
      </Section>

      <Section title="Job health">
        <JobHealthCard rows={data.jobs} window={windowSel} />
      </Section>
    </div>
  );
}

// --- Section wrapper ---------------------------------------------------------

/**
 * Section heading + body, with consistent spacing between them. Replaces
 * the old `<SectionLabel>` + sibling pattern that relied on a negative
 * margin and ended up clipping the title behind the next card's ring.
 */
function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
        {title}
      </h3>
      {children}
    </section>
  );
}

// --- Header ------------------------------------------------------------------

function Header({
  userName,
  windowSel,
  onWindowChange,
  loading,
}: {
  userName: string | null;
  windowSel: AnalyticsWindow;
  onWindowChange: (w: AnalyticsWindow) => void;
  loading: boolean;
}) {
  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">
          Welcome back{userName ? `, ${userName.split(" ")[0]}` : ""}
        </h2>
        <p className="text-muted-foreground">
          Here&apos;s an overview of your hiring pipeline.
        </p>
      </div>
      <div className="flex items-center gap-3">
        {loading && (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        )}
        <div className="inline-flex rounded-md border bg-card p-0.5">
          {WINDOW_OPTIONS.map((opt) => {
            const active = opt.value === windowSel;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => onWindowChange(opt.value)}
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
        <Link href="/dashboard/jobs/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            New Job
          </Button>
        </Link>
      </div>
    </div>
  );
}

// --- KPI grid ----------------------------------------------------------------

/**
 * Color palette per accent — mirrors the gridiron-dashboard colorMap.
 * Each accent drives the badge bg/text AND the sparkline stroke/fill.
 */
type Accent = "violet" | "sky" | "amber" | "emerald" | "rose" | "slate";
const colorMap: Record<
  Accent,
  { text: string; bg: string; chart: string; gradient: string }
> = {
  violet: {
    text: "text-violet-600 dark:text-violet-400",
    bg: "bg-violet-50 dark:bg-violet-950/30",
    chart: "#8b5cf6",
    gradient: "#8b5cf640",
  },
  sky: {
    text: "text-blue-600 dark:text-blue-400",
    bg: "bg-blue-50 dark:bg-blue-950/30",
    chart: "#3b82f6",
    gradient: "#3b82f640",
  },
  amber: {
    text: "text-amber-600 dark:text-amber-400",
    bg: "bg-amber-50 dark:bg-amber-950/30",
    chart: "#f59e0b",
    gradient: "#f59e0b40",
  },
  emerald: {
    text: "text-emerald-600 dark:text-emerald-400",
    bg: "bg-emerald-50 dark:bg-emerald-950/30",
    chart: "#10b981",
    gradient: "#10b98140",
  },
  rose: {
    text: "text-red-600 dark:text-red-400",
    bg: "bg-red-50 dark:bg-red-950/30",
    chart: "#ef4444",
    gradient: "#ef444440",
  },
  slate: {
    text: "text-slate-600 dark:text-slate-400",
    bg: "bg-slate-50 dark:bg-slate-950/30",
    chart: "#64748b",
    gradient: "#64748b40",
  },
};

function KPIGrid({
  kpis,
  window,
  trends,
}: {
  kpis: AnalyticsKPIs;
  window: AnalyticsWindow;
  trends: AnalyticsTrendPoint[];
}) {
  const windowLabel = windowSuffix(window);
  const sparkSlice = useMemo(() => {
    if (window === "all") return trends;
    const days = window === "7d" ? 7 : window === "30d" ? 30 : 90;
    return trends.slice(-days);
  }, [trends, window]);
  const applicationsSeries = useMemo(
    () => sparkSlice.map((p) => p.applications),
    [sparkSlice],
  );

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      <KPICard
        title="Active jobs"
        value={kpis.active_jobs}
        subtitle="currently posted"
        href="/dashboard/jobs"
        accent="violet"
      />
      <KPICard
        title="Applications"
        value={kpis.applications}
        subtitle={windowLabel}
        accent="sky"
        sparkline={applicationsSeries}
      />
      <KPICard
        title="Pending review"
        value={kpis.pending_review}
        subtitle="awaiting HR"
        accent="amber"
        emphasized={kpis.pending_review > 0}
      />
      <KPICard
        title="Awaiting decision"
        value={kpis.completed_awaiting_decision}
        subtitle="completed · undecided"
        accent="rose"
        emphasized={kpis.completed_awaiting_decision > 0}
      />
      <KPICard
        title="Completion rate"
        value={formatPercent(kpis.completion_rate)}
        subtitle={`invited \u2192 completed`}
        accent="emerald"
      />
      <KPICard
        title="Avg cost / interview"
        value={formatUsd(kpis.avg_cost_per_interview_usd)}
        subtitle={windowLabel}
        accent="slate"
      />
    </div>
  );
}

/**
 * KPI card — gridiron-dashboard design:
 *
 *  LABEL (uppercase, muted)                              ← top
 *  2,451                                                ← value
 *  30 days                                              ← scope
 *  ─────────────────── sparkline ─────────────────────── ← bottom (h-10)
 */
function KPICard({
  title,
  value,
  subtitle,
  href,
  accent = "slate",
  emphasized = false,
  sparkline,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  href?: string;
  accent?: Accent;
  emphasized?: boolean;
  sparkline?: number[];
}) {
  const colors = colorMap[accent];

  const body = (
    <Card
      className={`overflow-hidden${
        href ? " cursor-pointer transition-colors hover:bg-accent/30" : ""
      }`}
    >
      <CardContent className="p-4">
        {/* Label */}
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {title}
        </p>

        {/* Value; the API does not provide previous-window comparisons. */}
        <div className="mt-2 flex items-end justify-between gap-2">
          <p
            className={`text-2xl font-bold tracking-tight${
              emphasized ? " " + colors.text : ""
            }`}
          >
            {value}
          </p>
        </div>

        {/* Subtitle */}
        {subtitle && (
          <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
        )}

        {/* Sparkline */}
        {sparkline && sparkline.length > 1 ? (
          <div className="mt-3 h-10">
            <Sparkline
              values={sparkline}
              chartColor={colors.chart}
              gradientId={`spark-${accent}`}
              gradientColor={colors.gradient}
            />
          </div>
        ) : (
          <div className="mt-3 h-10" />
        )}
      </CardContent>
    </Card>
  );
  return href ? <Link href={href}>{body}</Link> : body;
}

// --- Sparkline (inline SVG, no recharts) -------------------------------------

/**
 * Single-series area + line chart styled after gridiron-dashboard's
 * Recharts AreaChart: gradient fill that fades to transparent at the
 * bottom, solid colored stroke, no axes or dots.
 *
 * Uses explicit hex `chartColor` / `gradientColor` (from colorMap) so
 * the gradient `stop` colors are not subject to Tailwind JIT purging.
 */
function Sparkline({
  values,
  chartColor,
  gradientId,
  gradientColor,
}: {
  values: number[];
  chartColor: string;
  gradientId: string;
  gradientColor: string;
}) {
  const width  = 100;
  const height = 32;
  const min  = Math.min(...values);
  const max  = Math.max(...values);
  const span = max - min || 1;
  const stepX = values.length > 1 ? width / (values.length - 1) : width;
  const pts = values.map((v, i) => {
    const x = i * stepX;
    const y = height - 1 - ((v - min) / span) * (height - 2);
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });
  const polyPoints = pts.join(" ");
  const areaPoints = `${polyPoints} ${width.toFixed(2)},${height} 0,${height}`;
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className="h-full w-full"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={chartColor} stopOpacity={0.3} />
          <stop offset="100%" stopColor={chartColor} stopOpacity={0} />
        </linearGradient>
      </defs>
      <polygon points={areaPoints} fill={`url(#${gradientId})`} />
      <polyline
        points={polyPoints}
        fill="none"
        stroke={chartColor}
        strokeWidth={1.75}
        strokeLinejoin="round"
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

// --- Funnel ------------------------------------------------------------------

function FunnelCard({
  funnel,
  window,
}: {
  funnel: AnalyticsFunnel;
  window: AnalyticsWindow;
}) {
  const max = useMemo(
    () => Math.max(1, ...FUNNEL_STAGES.map((s) => funnel[s.key])),
    [funnel],
  );

  // Conversion ratios shown between adjacent stages.
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
          Events in the last {windowSuffix(window)}. Each row is a stage; the
          percentage shows conversion from the previous stage.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {FUNNEL_STAGES.map((stage) => {
            const value = funnel[stage.key];
            const conv = conversions[stage.key as string] ?? null;
            const widthPct = (value / max) * 100;
            return (
              <div key={stage.key}>
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="font-medium text-foreground/80">{stage.label}</span>
                  <span className="text-muted-foreground tabular-nums">
                    {value}
                    {conv != null && (
                      <span className="ml-2 text-muted-foreground/60">
                        ({(conv * 100).toFixed(0)}%)
                      </span>
                    )}
                  </span>
                </div>
                {/* Track + filled bar */}
                <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary transition-all"
                    style={{
                      width: value > 0 ? `max(4px, ${widthPct}%)` : "0%",
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
        {funnel.rejected > 0 && (
          <p className="mt-4 text-xs text-muted-foreground">
            {funnel.rejected} candidate
            {funnel.rejected === 1 ? "" : "s"} rejected in this window.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// --- Activity over time (stacked area chart) --------------------------------

/**
 * Daily applications + interview-completions for the selected window.
 * Renders as a two-series area chart so the user can see both volume
 * and the throughput gap at a glance. Uses the same trends payload as
 * the KPI sparklines, just at a larger size.
 */
function ActivityCard({
  trends,
  window,
}: {
  trends: AnalyticsTrendPoint[];
  window: AnalyticsWindow;
}) {
  // Trim to the active window so the chart matches the KPI cards.
  const slice = useMemo(() => {
    if (window === "all") return trends;
    const days = window === "7d" ? 7 : window === "30d" ? 30 : 90;
    return trends.slice(-days);
  }, [trends, window]);

  const apps = slice.map((p) => p.applications);
  const completed = slice.map((p) => p.completed);
  const totalApps = apps.reduce((s, v) => s + v, 0);
  const totalCompleted = completed.reduce((s, v) => s + v, 0);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Activity over time</CardTitle>
        <CardDescription>
          Daily applications and completed interviews for the last{" "}
          {windowSuffix(window)}.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {totalApps === 0 && totalCompleted === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground italic">
            No activity in this window yet.
          </p>
        ) : (
          <>
            <AreaChart series={[
              { values: apps, color: "text-sky-400", label: "Applications" },
              { values: completed, color: "text-emerald-400", label: "Completed" },
            ]} />
            <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-muted-foreground">
              <LegendDot className="bg-sky-400">
                Applications · <span className="text-foreground">{totalApps}</span>
              </LegendDot>
              <LegendDot className="bg-emerald-400">
                Completed · <span className="text-foreground">{totalCompleted}</span>
              </LegendDot>
              <span className="ml-auto text-muted-foreground/70">
                {slice[0]?.date} → {slice[slice.length - 1]?.date}
              </span>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function LegendDot({
  className,
  children,
}: {
  className: string;
  children: React.ReactNode;
}) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`h-2 w-2 rounded-full ${className}`} aria-hidden="true" />
      {children}
    </span>
  );
}

/**
 * Multi-series area chart. Each series has its own normalized scale
 * applied against a shared Y axis so the visual heights stay
 * comparable. SVG-only — no chart library.
 */
function AreaChart({
  series,
  height = 140,
}: {
  series: { values: number[]; color: string; label: string }[];
  height?: number;
}) {
  const width = 600;
  const n = series[0]?.values.length ?? 0;
  // Shared max so the two series can be compared visually. +1 keeps a
  // flat-zero series from dividing by zero in the y mapping below.
  const max = Math.max(1, ...series.flatMap((s) => s.values));
  const stepX = n > 1 ? width / (n - 1) : width;

  const buildPaths = (values: number[]) => {
    const points = values.map((v, i) => {
      const x = i * stepX;
      const y = height - 4 - (v / max) * (height - 8);
      return [x, y] as const;
    });
    const line = points
      .map(([x, y], i) => `${i === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`)
      .join(" ");
    const area =
      `M 0 ${height} ` +
      points
        .map(([x, y]) => `L ${x.toFixed(2)} ${y.toFixed(2)}`)
        .join(" ") +
      ` L ${width} ${height} Z`;
    return { line, area };
  };

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className="h-32 w-full"
      aria-hidden="true"
    >
      {/* Subtle horizontal gridlines at 0/50/100% for readability. */}
      {[0.25, 0.5, 0.75].map((p) => (
        <line
          key={p}
          x1={0}
          x2={width}
          y1={height * p}
          y2={height * p}
          className="stroke-muted/40"
          strokeWidth={1}
          strokeDasharray="2 4"
        />
      ))}
      {series.map((s) => {
        const { line, area } = buildPaths(s.values);
        return (
          <g key={s.label} className={s.color}>
            <path d={area} fill="currentColor" opacity={0.18} />
            <path
              d={line}
              fill="none"
              stroke="currentColor"
              strokeWidth={1.75}
              strokeLinejoin="round"
              strokeLinecap="round"
              vectorEffect="non-scaling-stroke"
            />
          </g>
        );
      })}
    </svg>
  );
}

// --- Action needed -----------------------------------------------------------

const ACTION_SECTIONS = [
  {
    key: "pending_review" as const,
    label: "Review resumes",
    sublabel: "AI pre-screened · awaiting your call",
    dotClass: "bg-rose-500",
    accentClass: "border-l-rose-400",
    countClass: "text-rose-600 dark:text-rose-400",
  },
  {
    key: "awaiting_decision" as const,
    label: "Make a decision",
    sublabel: "Interview done · no shortlist or reject yet",
    dotClass: "bg-amber-500",
    accentClass: "border-l-amber-400",
    countClass: "text-amber-600 dark:text-amber-400",
  },
  {
    key: "stalled_invites" as const,
    label: "Follow up on invites",
    sublabel: "Invite sent · candidate hasn't started",
    dotClass: "bg-sky-500",
    accentClass: "border-l-sky-400",
    countClass: "text-sky-600 dark:text-sky-400",
  },
] as const;

function ActionNeededCard({
  buckets,
}: {
  buckets: AnalyticsOverview["action_needed"];
}) {
  const total =
    buckets.pending_review.count +
    buckets.awaiting_decision.count +
    buckets.stalled_invites.count;

  const activeSections = ACTION_SECTIONS.filter(
    (s) => buckets[s.key].count > 0,
  );

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Action needed</CardTitle>
          {total > 0 && (
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-destructive text-[11px] font-bold text-destructive-foreground">
              {total}
            </span>
          )}
        </div>
      </CardHeader>

      <CardContent>
        {total === 0 ? (
          <div className="flex flex-col items-center gap-2 py-4 text-center">
            <PartyPopper className="h-8 w-8 text-muted-foreground/40" />
            <p className="text-sm font-medium">You&apos;re all caught up!</p>
            <p className="text-xs text-muted-foreground">
              No pending reviews, decisions, or stalled invites.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {activeSections.map((section) => {
              const bucket = buckets[section.key];
              return (
                <div
                  key={section.key}
                  className={`rounded-lg border border-border border-l-[3px] ${section.accentClass} bg-muted/40 p-3`}
                >
                  {/* Section header */}
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={`h-2 w-2 shrink-0 rounded-full ${section.dotClass}`}
                      />
                      <span className="text-sm font-semibold">
                        {section.label}
                      </span>
                    </div>
                    <span
                      className={`text-xs font-bold tabular-nums ${section.countClass}`}
                    >
                      {bucket.count}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground pl-4 mb-2">
                    {section.sublabel}
                  </p>

                  {/* Candidate rows */}
                  <ul className="space-y-0.5">
                    {bucket.items.slice(0, 4).map((item) => (
                      <li key={item.candidate_id}>
                        <Link
                          href={`/dashboard/jobs/${item.job_id}/candidates/${item.candidate_id}`}
                          className="flex items-center justify-between rounded px-2 py-1.5 text-xs transition-colors hover:bg-background/60"
                        >
                          <span className="min-w-0 flex-1 truncate font-medium">
                            {item.name || "Unnamed"}
                            <span className="font-normal text-muted-foreground">
                              {" "}· {item.job_title}
                            </span>
                          </span>
                          <span className="ml-3 shrink-0 inline-flex items-center gap-1 text-muted-foreground">
                            <Clock className="h-3 w-3" />
                            {item.since ? relativeTime(item.since) : "—"}
                          </span>
                        </Link>
                      </li>
                    ))}
                    {bucket.count > bucket.items.length && (
                      <li className="px-2 py-1 text-xs text-muted-foreground">
                        +{bucket.count - bucket.items.length} more
                      </li>
                    )}
                  </ul>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// --- Calibration -------------------------------------------------------------

function CalibrationCard({
  calibration,
  window,
}: {
  calibration: AnalyticsCalibration;
  window: AnalyticsWindow;
}) {
  const { agreement_rate, sample_size, min_sample, total_predictions } =
    calibration;
  const ready = agreement_rate != null;
  const remaining = Math.max(0, min_sample - sample_size);
  const progress = Math.min(100, Math.round((sample_size / min_sample) * 100));

  const rateColor =
    agreement_rate == null
      ? ""
      : agreement_rate >= 0.8
        ? "text-green-500 dark:text-green-400"
        : agreement_rate >= 0.6
          ? "text-amber-500 dark:text-amber-400"
          : "text-red-500 dark:text-red-400";

  const rateHint =
    agreement_rate == null
      ? null
      : agreement_rate >= 0.8
        ? "Thresholds look well-tuned."
        : agreement_rate >= 0.6
          ? "Consider raising your auto-invite score threshold."
          : "The AI is inviting candidates you're rejecting — review your thresholds.";

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">AI accuracy</CardTitle>
        <CardDescription>
          How often the AI&apos;s auto-invite decisions match your final call
          ({windowSuffix(window)}).
        </CardDescription>
      </CardHeader>
      <CardContent>
        {ready ? (
          <div className="space-y-2">
            <div className={`text-3xl font-bold ${rateColor}`}>
              {formatPercent(agreement_rate)}
            </div>
            <p className="text-xs text-muted-foreground">
              {calibration.auto_invite_agreed} of {calibration.auto_invite_n}
              {" "}auto-invited candidates matched your shortlist or reject
              decision.
            </p>
            {rateHint && (
              <p className="text-xs text-muted-foreground/70 border-l-2 border-muted pl-2">
                {rateHint}
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            <div className="text-sm font-medium text-muted-foreground">
              Warming up…
            </div>
            <div className="h-1.5 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full bg-primary/50 transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              {sample_size} of {min_sample} decisions needed to compute
              accuracy. {remaining} more to go.
            </p>
          </div>
        )}
        <p className="text-[11px] text-muted-foreground/50 mt-3">
          {total_predictions} total prediction
          {total_predictions === 1 ? "" : "s"} in this window.
        </p>
      </CardContent>
    </Card>
  );
}

// --- Job health table --------------------------------------------------------

function JobHealthCard({
  rows,
  window,
}: {
  rows: AnalyticsJobHealthRow[];
  window: AnalyticsWindow;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <CardTitle className="text-base">Job health</CardTitle>
          <CardDescription>
            Per-job metrics for the last {windowSuffix(window)}.
          </CardDescription>
        </div>
        <Link href="/dashboard/jobs">
          <Button variant="ghost" size="sm" className="text-xs">
            All jobs
            <ArrowRight className="ml-1 h-3 w-3" />
          </Button>
        </Link>
      </CardHeader>
      <CardContent>
        {rows.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Briefcase className="h-8 w-8 text-muted-foreground/40 mb-2" />
            <p className="text-sm text-muted-foreground">No active jobs.</p>
            <Link href="/dashboard/jobs/new" className="mt-2">
              <Button variant="outline" size="sm">
                <Plus className="mr-1.5 h-3 w-3" />
                Create one
              </Button>
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted-foreground border-b">
                  <th className="py-2 pr-4 font-medium">Job</th>
                  <th className="py-2 pr-4 font-medium text-right">
                    Candidates
                  </th>
                  <th className="py-2 pr-4 font-medium text-right">Pending</th>
                  <th className="py-2 pr-4 font-medium text-right">
                    Completion
                  </th>
                  <th className="py-2 pr-4 font-medium text-right">
                    Avg score
                  </th>
                  <th className="py-2 pr-4 font-medium text-right">
                    Avg cost
                  </th>
                  <th className="py-2 pr-2 font-medium text-right">
                    Median time
                  </th>
                  <th className="py-2 pr-2 font-medium text-right"></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr
                    key={row.id}
                    className="border-b last:border-b-0 hover:bg-accent/30"
                  >
                    <td className="py-2 pr-4">
                      <Link
                        href={`/dashboard/jobs/${row.id}`}
                        className="font-medium hover:underline"
                      >
                        {row.title}
                      </Link>
                      {row.status !== "active" && (
                        <Badge
                          variant="outline"
                          className="ml-2 text-[10px] uppercase"
                        >
                          {row.status}
                        </Badge>
                      )}
                    </td>
                    <td className="py-2 pr-4 text-right tabular-nums">
                      {row.candidate_count}
                    </td>
                    <td className="py-2 pr-4 text-right tabular-nums">
                      {row.pending_review > 0 ? (
                        <span className="inline-flex items-center gap-1 text-amber-600">
                          <AlertCircle className="h-3 w-3" />
                          {row.pending_review}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">0</span>
                      )}
                    </td>
                    <td className="py-2 pr-4 text-right tabular-nums">
                      {formatPercent(row.completion_rate)}
                    </td>
                    <td className="py-2 pr-4 text-right tabular-nums">
                      {row.avg_score != null ? row.avg_score.toFixed(1) : "—"}
                    </td>
                    <td className="py-2 pr-4 text-right tabular-nums">
                      {formatUsd(row.avg_cost)}
                    </td>
                    <td className="py-2 pr-2 text-right tabular-nums text-muted-foreground">
                      {row.median_time_to_complete_minutes != null
                        ? `${row.median_time_to_complete_minutes.toFixed(0)} min`
                        : "—"}
                    </td>
                    <td className="py-2 pr-2 text-right">
                      <Link
                        href={`/dashboard/jobs/${row.id}/analytics`}
                        className="text-xs text-primary hover:underline inline-flex items-center gap-0.5"
                      >
                        Analytics
                        <ArrowRight className="h-3 w-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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

function relativeTime(iso: string): string {
  const then = parseApiDate(iso).getTime();
  const diffMs = Date.now() - then;
  const min = Math.round(diffMs / 60_000);
  if (min < 60) return `${min}m`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h`;
  const d = Math.round(hr / 24);
  return `${d}d`;
}
