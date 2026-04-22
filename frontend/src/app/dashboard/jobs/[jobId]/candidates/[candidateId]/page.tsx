"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import {
  ArrowLeft,
  Loader2,
  ThumbsUp,
  ThumbsDown,
  MessageSquare,
  Shield,
  FileText,
  BarChart3,
  Download,
} from "lucide-react";

import { candidates as candidatesApi, API_URL } from "@/lib/api";
import type { CandidateDetail } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ShareReportDialog } from "@/components/share-report-dialog";

const TABS = [
  { id: "evaluation", label: "Evaluation", icon: BarChart3 },
  { id: "transcript", label: "Transcript", icon: MessageSquare },
  { id: "integrity", label: "Integrity", icon: Shield },
  { id: "resume", label: "Resume", icon: FileText },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function CandidateDetailPage() {
  const { jobId, candidateId } = useParams<{
    jobId: string;
    candidateId: string;
  }>();
  const [candidate, setCandidate] = useState<CandidateDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("evaluation");
  const [isActioning, setIsActioning] = useState(false);

  useEffect(() => {
    candidatesApi
      .get(candidateId)
      .then(setCandidate)
      .catch((err) => setError(err.message))
      .finally(() => setIsLoading(false));
  }, [candidateId]);

  const handleAction = async (action: "shortlist" | "reject") => {
    setIsActioning(true);
    try {
      const fn =
        action === "shortlist"
          ? candidatesApi.shortlist
          : candidatesApi.reject;
      const updated = await fn(candidateId);
      setCandidate((prev) =>
        prev ? { ...prev, status: updated.status } : prev,
      );
      toast.success(
        action === "shortlist"
          ? "Candidate shortlisted"
          : "Candidate rejected",
      );
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Action failed",
      );
    } finally {
      setIsActioning(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !candidate) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24">
        <p className="text-sm text-destructive">
          {error ?? "Candidate not found"}
        </p>
        <Link href={`/dashboard/jobs/${jobId}`}>
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 overflow-x-hidden">
      {/* Header */}
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <Link href={`/dashboard/jobs/${jobId}`}>
            <Button variant="ghost" size="icon" className="shrink-0">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-3">
              <h2 className="truncate text-2xl font-bold tracking-tight">
                {candidate.name}
              </h2>
              <Badge variant="secondary" className="shrink-0 capitalize">
                {candidate.status.replace("_", " ")}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">{candidate.email}</p>
          </div>
          <div className="hidden sm:flex gap-2 shrink-0">
            <ShareReportDialog
              candidateId={candidateId}
              candidateName={candidate.name}
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleAction("reject")}
              disabled={
                isActioning || candidate.status === "rejected"
              }
            >
              <ThumbsDown className="mr-2 h-3.5 w-3.5" />
              Reject
            </Button>
            <Button
              size="sm"
              onClick={() => handleAction("shortlist")}
              disabled={
                isActioning || candidate.status === "shortlisted"
              }
            >
              <ThumbsUp className="mr-2 h-3.5 w-3.5" />
              Shortlist
            </Button>
          </div>
        </div>
        {/* Mobile action buttons */}
        <div className="flex flex-col gap-2 sm:hidden">
          <ShareReportDialog
            candidateId={candidateId}
            candidateName={candidate.name}
          />
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => handleAction("reject")}
              disabled={
                isActioning || candidate.status === "rejected"
              }
            >
              <ThumbsDown className="mr-2 h-3.5 w-3.5" />
              Reject
            </Button>
            <Button
              size="sm"
              className="flex-1"
              onClick={() => handleAction("shortlist")}
              disabled={
                isActioning || candidate.status === "shortlisted"
              }
            >
              <ThumbsUp className="mr-2 h-3.5 w-3.5" />
              Shortlist
            </Button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              className={`flex items-center gap-2 px-3 sm:px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px whitespace-nowrap ${
                activeTab === tab.id
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
              onClick={() => setActiveTab(tab.id)}
            >
              <Icon className="h-4 w-4" />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      {activeTab === "evaluation" && (
        <EvaluationTab candidate={candidate} />
      )}
      {activeTab === "transcript" && (
        <TranscriptTab candidate={candidate} />
      )}
      {activeTab === "integrity" && (
        <IntegrityTab candidate={candidate} />
      )}
      {activeTab === "resume" && <ResumeTab candidate={candidate} />}
    </div>
  );
}

/* ── Evaluation Tab ───────────────────────────────────────── */

const RECOMMENDATION_STYLES: Record<string, string> = {
  strong_yes: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  yes: "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300",
  maybe: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  no: "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300",
  strong_no: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
};

function EvaluationTab({ candidate }: { candidate: CandidateDetail }) {
  const evaluation = candidate.evaluation;

  if (!evaluation) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-sm text-muted-foreground">
            Evaluation not yet available. The interview may still be in progress.
          </p>
        </CardContent>
      </Card>
    );
  }

  const scoreCategories = [
    { label: "Skill Match", value: evaluation.scores.skill_match },
    { label: "Communication", value: evaluation.scores.communication },
    { label: "Problem Solving", value: evaluation.scores.problem_solving },
    { label: "Cultural Fit", value: evaluation.scores.cultural_fit },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {/* Overall score */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Overall Score</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-6">
          <div className="flex h-20 w-20 items-center justify-center rounded-full border-4 border-primary">
            <span className="text-3xl font-bold">
              {evaluation.overall_score != null
                ? Number(evaluation.overall_score).toFixed(1)
                : "N/A"}
            </span>
          </div>
          <div className="space-y-2">
            <Badge
              variant="secondary"
              className={
                RECOMMENDATION_STYLES[evaluation.recommendation] ?? ""
              }
            >
              {evaluation.recommendation.replace("_", " ")}
            </Badge>
            <p className="text-sm text-muted-foreground">
              {evaluation.summary}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Score breakdown */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Score Breakdown</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {scoreCategories.map((cat) => (
            <div key={cat.label} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span>{cat.label}</span>
                <span className="font-medium">
                  {cat.value != null ? Number(cat.value).toFixed(1) : "N/A"}/10
                </span>
              </div>
              <div className="h-2 rounded-full bg-muted">
                <div
                  className="h-2 rounded-full bg-primary transition-all"
                  style={{ width: `${((cat.value ?? 0) / 10) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Strengths */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Strengths</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {evaluation.strengths.map((s) => (
            <Badge
              key={s}
              variant="secondary"
              className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
            >
              {s}
            </Badge>
          ))}
        </CardContent>
      </Card>

      {/* Gaps & Red Flags */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Gaps {evaluation.red_flags.length > 0 && "& Red Flags"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {evaluation.gaps.map((g) => (
              <Badge
                key={g}
                variant="secondary"
                className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400"
              >
                {g}
              </Badge>
            ))}
          </div>
          {evaluation.red_flags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {evaluation.red_flags.map((r) => (
                <Badge
                  key={r}
                  variant="secondary"
                  className="bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
                >
                  {r}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

/* ── Transcript Tab ───────────────────────────────────────── */

function TranscriptTab({ candidate }: { candidate: CandidateDetail }) {
  const transcript = candidate.interview?.transcript ?? [];

  if (transcript.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-sm text-muted-foreground">
            No transcript available.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="flex flex-col overflow-hidden" style={{ maxHeight: "calc(100vh - 280px)" }}>
      <CardContent className="space-y-4 py-6 overflow-y-auto">
        {transcript.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "candidate" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[75%] rounded-lg px-4 py-3 text-sm ${
                msg.role === "candidate"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              <p
                className={`mt-1 text-xs ${
                  msg.role === "candidate"
                    ? "text-primary-foreground/70"
                    : "text-muted-foreground"
                }`}
              >
                {msg.timestamp}
              </p>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

/* ── Integrity Tab ────────────────────────────────────────── */

function IntegrityTab({ candidate }: { candidate: CandidateDetail }) {
  const signals = candidate.interview?.integrity_signals;

  if (!signals) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-sm text-muted-foreground">
            No integrity data available.
          </p>
        </CardContent>
      </Card>
    );
  }

  const stats = [
    { label: "Paste Count", value: signals.paste_count ?? 0 },
    { label: "Tab Switches", value: signals.tab_switch_count ?? 0 },
    {
      label: "Avg Response Time",
      value: signals.avg_response_time_seconds != null
        ? `${Number(signals.avg_response_time_seconds).toFixed(1)}s`
        : "N/A",
    },
    { label: "Timing Anomalies", value: signals.timing_anomalies ?? 0 },
    {
      label: "Length Variance Flag",
      value: signals.length_variance_flag ? "Yes" : "No",
    },
  ];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Integrity Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm">{signals.summary}</p>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardContent className="py-4">
              <p className="text-2xl font-bold">{stat.value}</p>
              <p className="text-xs text-muted-foreground">{stat.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ── Resume Tab ───────────────────────────────────────────── */

function ResumeTab({ candidate }: { candidate: CandidateDetail }) {
  const parsed = candidate.resume_parsed_data;

  if (!parsed) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-sm text-muted-foreground">
            No parsed resume data available.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card className="md:col-span-2">
        <CardContent className="flex items-center justify-between py-4">
          <div className="text-sm text-muted-foreground">
            Parsed resume data shown below. Download the original file for full details.
          </div>
          {candidate.resume_url ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                fetch(`${API_URL}/candidates/${candidate.id}/resume`, {
                  credentials: "include",
                })
                  .then((res) => {
                    if (!res.ok) throw new Error("Download failed");
                    const disposition = res.headers.get("content-disposition");
                    const match = disposition?.match(/filename="?(.+?)"?$/);
                    const filename = match?.[1] || "resume.pdf";
                    return res.blob().then((blob) => ({ blob, filename }));
                  })
                  .then(({ blob, filename }) => {
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = filename;
                    a.click();
                    URL.revokeObjectURL(url);
                  })
                  .catch(() => toast.error("Failed to download resume"));
              }}
            >
              <Download className="mr-2 h-4 w-4" />
              Download Resume
            </Button>
          ) : (
            <Button variant="outline" size="sm" disabled>
              <Download className="mr-2 h-4 w-4" />
              No File
            </Button>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Overview</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="grid grid-cols-2 gap-2">
            <span className="text-muted-foreground">Name</span>
            <span className="font-medium">{parsed.name}</span>
            <span className="text-muted-foreground">Email</span>
            <span>{parsed.email}</span>
            <span className="text-muted-foreground">Current Role</span>
            <span>{parsed.current_role}</span>
            <span className="text-muted-foreground">Experience</span>
            <span>{parsed.years_experience} years</span>
          </div>
          <p className="text-muted-foreground pt-2">{parsed.summary}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Skills</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {parsed.skills.map((skill) => (
            <Badge key={skill} variant="secondary">
              {skill}
            </Badge>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Experience</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {parsed.experience.map((exp, i) => (
            <div key={i} className="text-sm">
              <p className="font-medium">{exp.role}</p>
              <p className="text-muted-foreground">
                {exp.company} · {exp.duration}
              </p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Education</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {parsed.education.map((edu, i) => (
            <div key={i} className="text-sm">
              <p className="font-medium">{edu.degree}</p>
              <p className="text-muted-foreground">
                {edu.institution} · {edu.year}
              </p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
