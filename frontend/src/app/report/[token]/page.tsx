"use client";

import { use, useEffect, useState } from "react";
import { format } from "date-fns";
import {
  AlertTriangle,
  Award,
  CheckCircle2,
  Loader2,
  MessageSquare,
  XCircle,
} from "lucide-react";

import { publicReports } from "@/lib/api";
import type { PublicReport } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

const RECOMMENDATION_STYLES: Record<string, string> = {
  strong_yes:
    "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  yes: "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300",
  maybe:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  no: "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300",
  strong_no:
    "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
};

interface PageProps {
  params: Promise<{ token: string }>;
}

export default function PublicReportPage({ params }: PageProps) {
  const { token } = use(params);
  const [report, setReport] = useState<PublicReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    publicReports
      .get(token)
      .then(setReport)
      .catch((err) =>
        setError(
          err instanceof Error
            ? err.message
            : "This share link is invalid or has expired.",
        ),
      )
      .finally(() => setIsLoading(false));
  }, [token]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
        <AlertTriangle className="h-10 w-10 text-muted-foreground" />
        <h1 className="text-xl font-semibold">Link unavailable</h1>
        <p className="max-w-md text-sm text-muted-foreground">
          {error ?? "This share link is invalid or has expired."}
        </p>
      </div>
    );
  }

  const ev = report.evaluation;
  const scoreCategories: Array<[string, number | undefined]> = [
    ["Skill Match", ev.scores?.skill_match],
    ["Communication", ev.scores?.communication],
    ["Problem Solving", ev.scores?.problem_solving],
    ["Cultural Fit", ev.scores?.cultural_fit],
  ];

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-4 py-8 sm:p-8">
      {/* Header */}
      <header className="space-y-2 border-b pb-6">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">
          Evaluation report
        </p>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
          {report.candidate_name}
        </h1>
        <p className="text-sm text-muted-foreground">
          {report.job_title} · {report.company_name}
          {report.completed_at && (
            <>
              {" "}
              · Interviewed{" "}
              {format(new Date(report.completed_at), "MMM d, yyyy")}
            </>
          )}
        </p>
      </header>

      {/* Overall + recommendation */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Award className="h-4 w-4 text-muted-foreground" />
            Overall assessment
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6 sm:flex-row sm:items-center">
          <div className="flex h-24 w-24 shrink-0 items-center justify-center rounded-full border-4 border-primary">
            <span className="text-3xl font-bold">
              {ev.overall_score != null
                ? Number(ev.overall_score).toFixed(1)
                : "—"}
            </span>
          </div>
          <div className="space-y-2">
            {ev.recommendation && (
              <Badge
                variant="secondary"
                className={
                  RECOMMENDATION_STYLES[ev.recommendation] ?? ""
                }
              >
                {ev.recommendation.replace("_", " ")}
              </Badge>
            )}
            <p className="text-sm leading-relaxed">{ev.summary}</p>
          </div>
        </CardContent>
      </Card>

      {/* Score breakdown */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Score breakdown</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {scoreCategories.map(([label, value]) => (
            <div key={label} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span>{label}</span>
                <span className="font-medium">
                  {value != null ? Number(value).toFixed(1) : "—"}/10
                </span>
              </div>
              <div className="h-2 rounded-full bg-muted">
                <div
                  className="h-2 rounded-full bg-primary transition-all"
                  style={{ width: `${((value ?? 0) / 10) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Strengths / gaps / red flags */}
      <div className="grid gap-4 sm:grid-cols-2">
        {ev.strengths?.length ? (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                Strengths
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-1 text-sm">
                {ev.strengths.map((s, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-green-600">•</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ) : null}

        {ev.gaps?.length ? (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <XCircle className="h-4 w-4 text-yellow-600" />
                Gaps
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-1 text-sm">
                {ev.gaps.map((g, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-yellow-600">•</span>
                    <span>{g}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ) : null}
      </div>

      {ev.red_flags?.length ? (
        <Card className="border-red-200 dark:border-red-900/40">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base text-red-700 dark:text-red-400">
              <AlertTriangle className="h-4 w-4" />
              Red flags
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm">
              {ev.red_flags.map((r, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-red-600">•</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      {/* Transcript */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
            Interview transcript
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {report.transcript.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No transcript available.
            </p>
          ) : (
            report.transcript.map((m, i) => (
              <div
                key={i}
                className={`rounded-lg p-3 text-sm ${
                  m.role === "interviewer"
                    ? "bg-muted"
                    : "bg-primary/5 border border-primary/20"
                }`}
              >
                <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  {m.role}
                </p>
                <p className="leading-relaxed whitespace-pre-wrap">{m.content}</p>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Separator />

      <footer className="text-center text-xs text-muted-foreground">
        Shared via {report.company_name} · Link expires{" "}
        {format(new Date(report.expires_at), "MMM d, yyyy")}
      </footer>
    </div>
  );
}
