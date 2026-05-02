"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import {
  ArrowLeft,
  Loader2,
  Mail,
  ThumbsUp,
  ThumbsDown,
  MessageSquare,
  Shield,
  FileText,
  BarChart3,
  Download,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

import { ApiError, candidates as candidatesApi, API_URL } from "@/lib/api";
import type {
  CandidateDetail,
  EmailTemplateKind,
  NotificationConflictDetail,
  PreScreenSummary,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ShareReportDialog } from "@/components/share-report-dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

// Pre-screen actions create irreversible side effects (interview invite
// email on approve), so they always require an explicit confirmation.
// Post-evaluation shortlist/reject status changes are reversible (Undo
// toast) and never email the candidate by themselves — candidate
// notifications are dispatched separately via the "Notify candidate"
// dialog so HR can change their mind before anything reaches the inbox.
type PreScreenConfirm = "approve_pre_screen" | "reject_pre_screen" | null;

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
  const [confirm, setConfirm] = useState<PreScreenConfirm>(null);

  useEffect(() => {
    candidatesApi
      .get(candidateId)
      .then(setCandidate)
      .catch((err) => setError(err.message))
      .finally(() => setIsLoading(false));
  }, [candidateId]);

  type Action =
    | "approve_pre_screen"
    | "reject_pre_screen"
    | "shortlist"
    | "reject";

  const runAction = async (action: Action) => {
    setIsActioning(true);
    try {
      let updated;
      switch (action) {
        case "approve_pre_screen":
          updated = await candidatesApi.approveInterview(candidateId);
          break;
        case "reject_pre_screen":
          updated = await candidatesApi.rejectPreScreen(candidateId);
          break;
        case "shortlist":
          updated = await candidatesApi.shortlist(candidateId);
          break;
        case "reject":
          updated = await candidatesApi.reject(candidateId);
          break;
      }
      setCandidate((prev) =>
        prev ? { ...prev, status: updated.status as typeof prev.status } : prev,
      );
      const messages: Record<Action, string> = {
        approve_pre_screen: "Interview invite sent",
        reject_pre_screen: "Candidate rejected at pre-screen",
        shortlist: "Candidate shortlisted",
        reject: "Candidate rejected",
      };
      toast.success(messages[action]);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Action failed");
    } finally {
      setIsActioning(false);
      setConfirm(null);
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
          <CandidateHeaderActions
            candidate={candidate}
            candidateId={candidateId}
            isActioning={isActioning}
            onPreScreenAction={(kind) => setConfirm(kind)}
            onPostEvalAction={runAction}
            layout="desktop"
          />
        </div>
        <CandidateHeaderActions
          candidate={candidate}
          candidateId={candidateId}
          isActioning={isActioning}
          onPreScreenAction={(kind) => setConfirm(kind)}
          onPostEvalAction={runAction}
          layout="mobile"
        />
      </div>

      {/* Confirmation dialog for pre-screen actions (irreversible: send email). */}
      <AlertDialog open={confirm !== null} onOpenChange={(open) => !open && setConfirm(null)}>
        <AlertDialogContent>
          {confirm === "approve_pre_screen" && (
            <>
              <AlertDialogHeader>
                <AlertDialogTitle>Send interview invite?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will create an interview for{" "}
                  <span className="font-medium">{candidate.name}</span> and email
                  the invite link to{" "}
                  <span className="font-medium">{candidate.email}</span>{" "}
                  immediately. The email cannot be recalled.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel disabled={isActioning}>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  disabled={isActioning}
                  onClick={() => {
                    runAction("approve_pre_screen");
                  }}
                >
                  {isActioning ? "Sending…" : "Approve & send invite"}
                </AlertDialogAction>
              </AlertDialogFooter>
            </>
          )}
          {confirm === "reject_pre_screen" && (
            <>
              <AlertDialogHeader>
                <AlertDialogTitle>Reject this candidate?</AlertDialogTitle>
                <AlertDialogDescription>
                  <span className="font-medium">{candidate.name}</span> will be
                  marked as rejected and will not move forward to an interview.
                  No email is sent to the candidate during this resume pre-screen
                  stage.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel disabled={isActioning}>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  disabled={isActioning}
                  onClick={(e) => {
                    e.preventDefault();
                    runAction("reject_pre_screen");
                  }}
                >
                  {isActioning ? "Rejecting…" : "Reject candidate"}
                </AlertDialogAction>
              </AlertDialogFooter>
            </>
          )}
        </AlertDialogContent>
      </AlertDialog>

      {/* Candidate notification panel: shows the most recent email we sent
          and lets HR explicitly dispatch a shortlist / reject / correction
          email. Decoupled from the status change itself so HR can revise
          their decision before anything reaches the candidate. */}
      <NotifyCandidatePanel
        candidate={candidate}
        onNotified={(updates) =>
          setCandidate((prev) => (prev ? { ...prev, ...updates } : prev))
        }
      />

      {/* Pre-screen summary (visible whenever pre-screen ran, regardless of
          current status). Gives HR the score, confidence, matched/missing
          skills, and the engine's reason for the routing decision. */}
      {candidate.pre_screen && (
        <PreScreenCard
          summary={candidate.pre_screen}
          candidateStatus={candidate.status}
        />
      )}

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

/* ── Stage-aware action group ─────────────────────────────────
 * Decides which buttons to show based on where the candidate is
 * in the funnel:
 *   • review_pending → Approve & Invite + Reject (pre-screen),
 *     both gated by a confirmation dialog (irreversible: email).
 *   • has evaluation → Share Report + Reject + Shortlist
 *     (post-evaluation hiring decision; status itself is reversible
 *     via the list-page Undo toast, side-effect emails are not).
 *   • processing / ready / in_progress / error and no eval → no
 *     hiring buttons (HR has nothing meaningful to act on yet).
 */
function CandidateHeaderActions({
  candidate,
  candidateId,
  isActioning,
  onPreScreenAction,
  onPostEvalAction,
  layout,
}: {
  candidate: CandidateDetail;
  candidateId: string;
  isActioning: boolean;
  onPreScreenAction: (kind: "approve_pre_screen" | "reject_pre_screen") => void;
  onPostEvalAction: (action: "shortlist" | "reject") => void;
  layout: "desktop" | "mobile";
}) {
  const isReviewPending = candidate.status === "review_pending";
  const hasEvaluation = candidate.evaluation !== null;

  if (!isReviewPending && !hasEvaluation) {
    // Nothing actionable yet — interview pending or processing failed.
    return null;
  }

  const wrapperClass =
    layout === "desktop"
      ? "hidden sm:flex gap-2 shrink-0"
      : "flex flex-col gap-2 sm:hidden";
  const buttonClass = layout === "desktop" ? "" : "flex-1";

  if (isReviewPending) {
    return (
      <div className={wrapperClass}>
        <div className={layout === "desktop" ? "flex gap-2" : "flex gap-2"}>
          <Button
            variant="outline"
            size="sm"
            className={buttonClass}
            onClick={() => onPreScreenAction("reject_pre_screen")}
            disabled={isActioning}
          >
            <ThumbsDown className="mr-2 h-3.5 w-3.5" />
            Reject (pre-screen)
          </Button>
          <Button
            size="sm"
            className={buttonClass}
            onClick={() => onPreScreenAction("approve_pre_screen")}
            disabled={isActioning}
          >
            <ThumbsUp className="mr-2 h-3.5 w-3.5" />
            Approve & invite
          </Button>
        </div>
      </div>
    );
  }

  // hasEvaluation === true
  return (
    <div className={wrapperClass}>
      {layout === "mobile" ? (
        <>
          <ShareReportDialog
            candidateId={candidateId}
            candidateName={candidate.name}
          />
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className={buttonClass}
              onClick={() => onPostEvalAction("reject")}
              disabled={isActioning || candidate.status === "rejected"}
            >
              <ThumbsDown className="mr-2 h-3.5 w-3.5" />
              Reject
            </Button>
            <Button
              size="sm"
              className={buttonClass}
              onClick={() => onPostEvalAction("shortlist")}
              disabled={isActioning || candidate.status === "shortlisted"}
            >
              <ThumbsUp className="mr-2 h-3.5 w-3.5" />
              Shortlist
            </Button>
          </div>
        </>
      ) : (
        <>
          <ShareReportDialog
            candidateId={candidateId}
            candidateName={candidate.name}
          />
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPostEvalAction("reject")}
            disabled={isActioning || candidate.status === "rejected"}
          >
            <ThumbsDown className="mr-2 h-3.5 w-3.5" />
            Reject
          </Button>
          <Button
            size="sm"
            onClick={() => onPostEvalAction("shortlist")}
            disabled={isActioning || candidate.status === "shortlisted"}
          >
            <ThumbsUp className="mr-2 h-3.5 w-3.5" />
            Shortlist
          </Button>
        </>
      )}
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
          <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full border-4 border-primary">
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
    <Card>
      <CardContent className="space-y-6 py-6">
        {transcript.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "candidate" ? "justify-end" : "justify-start"}`}
          >
            {msg.role === "candidate" ? (
              <div className="max-w-[75%] rounded-3xl bg-muted px-4 py-3 text-sm">
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
            ) : (
              <p className="max-w-[80%] text-sm leading-relaxed text-foreground whitespace-pre-wrap">
                {msg.content}
              </p>
            )}
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

/* ── Pre-Screen Card ──────────────────────────────────────── */

const PRE_SCREEN_DECISION_STYLES: Record<string, string> = {
  auto_invite:
    "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  review:
    "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400",
  reject: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  error: "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300",
};

const PRE_SCREEN_DECISION_LABELS: Record<string, string> = {
  auto_invite: "Auto-invited",
  review: "Awaiting review",
  reject: "Rejected",
  error: "Error",
};

function PreScreenCard({
  summary,
  candidateStatus,
}: {
  summary: PreScreenSummary;
  candidateStatus: CandidateDetail["status"];
}) {
  const isTerminal = ["completed", "shortlisted", "rejected"].includes(candidateStatus);
  const [expanded, setExpanded] = useState(!isTerminal);

  const score = summary.score;
  const confidence = summary.confidence;
  const matched = summary.breakdown?.matched_skills ?? [];
  const missing = summary.breakdown?.missing_must_haves ?? [];
  const rationale = summary.breakdown?.rationale;
  const showDecisionBadge =
    summary.decision !== null &&
    !(summary.decision === "review" && candidateStatus !== "review_pending");
  const scoreColorClass =
    score == null
      ? "text-muted-foreground"
      : score >= 75
        ? "text-green-600 dark:text-green-400"
        : score >= 55
          ? "text-amber-600 dark:text-amber-400"
          : "text-red-600 dark:text-red-400";

  return (
    <Card>
      <CardHeader
        className="flex flex-row items-start justify-between gap-3 space-y-0 cursor-pointer select-none"
        onClick={() => setExpanded((v) => !v)}
      >
        <div>
          <CardTitle className="text-base">Resume pre-screen</CardTitle>
          {summary.reason && (
            <p className="mt-1 text-xs text-muted-foreground">
              {summary.reason}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {showDecisionBadge && summary.decision && (
            <Badge
              variant="secondary"
              className={PRE_SCREEN_DECISION_STYLES[summary.decision] ?? ""}
            >
              {PRE_SCREEN_DECISION_LABELS[summary.decision] ?? summary.decision}
            </Badge>
          )}
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground shrink-0" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
          )}
        </div>
      </CardHeader>

      {expanded && (
        <CardContent className="space-y-4">
          <div className="flex items-center gap-6">
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">
                Match score
              </p>
              <p className={`text-3xl font-bold ${scoreColorClass}`}>
                {score != null ? `${score}/100` : "—"}
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">
                Confidence
              </p>
              <p className="text-3xl font-bold">
                {confidence != null ? confidence.toFixed(2) : "—"}
              </p>
            </div>
          </div>

          {matched.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Matched skills
              </p>
              <div className="flex flex-wrap gap-1.5">
                {matched.map((skill) => (
                  <Badge key={skill} variant="secondary">
                    {skill}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {missing.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Missing must-haves
              </p>
              <div className="flex flex-wrap gap-1.5">
                {missing.map((skill) => (
                  <Badge
                    key={skill}
                    variant="secondary"
                    className="bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300"
                  >
                    {skill}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {rationale && (
            <div className="space-y-1">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Rationale
              </p>
              <p className="text-sm leading-relaxed">{rationale}</p>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}

/* ── Notify candidate panel ──────────────────────────────────
 * Shows the most recent email we sent to the candidate and lets HR
 * explicitly dispatch a new notification. Two layers of protection:
 *  1. Pre-send: inline amber warning when the chosen kind contradicts
 *     the last email sent (visible before the user clicks Send).
 *  2. Post-confirm: 10-second undo window via a loading toast — the
 *     actual API call only fires after the window expires so HR can
 *     still cancel without spamming the candidate.
 * A 409 conflict (e.g. shortlist sent after reject) can appear during
 * the API call and re-opens the conflict confirmation dialog even after
 * the main dialog has been closed.
 */

const NOTIFICATION_KIND_LABEL: Record<EmailTemplateKind, string> = {
  shortlist: "Shortlist",
  reject: "Rejection",
  status_correction: "Correction / apology",
};

function NotifyCandidatePanel({
  candidate,
  onNotified,
}: {
  candidate: CandidateDetail;
  onNotified: (updates: Partial<CandidateDetail>) => void;
}) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<EmailTemplateKind>(() =>
    candidate.status === "rejected" ? "reject" : "shortlist",
  );
  const [conflict, setConflict] = useState<NotificationConflictDetail | null>(
    null,
  );
  const [isSending, setIsSending] = useState(false);
  const undoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Candidate-facing notifications are available only once the
  // candidate has completed the screening interview (evaluation exists).
  // Also don't render when we have no email address.
  if (!candidate.email || !candidate.evaluation) return null;

  const lastKind = candidate.last_notification_kind ?? null;
  const lastSentAt = candidate.last_notification_sent_at ?? null;

  // Amber indicator in the card header: status changed since last email.
  const hasStatusNotifMismatch =
    lastKind !== null &&
    ((candidate.status === "rejected" && lastKind === "shortlist") ||
      (candidate.status === "shortlisted" && lastKind === "reject"));

  // Inline warning inside the dialog: chosen kind would contradict last email.
  const hasDialogConflict =
    lastKind !== null &&
    ((lastKind === "shortlist" && kind === "reject") ||
      (lastKind === "reject" && kind === "shortlist"));

  // Actual API dispatch — called after the undo window expires.
  const dispatchSend = async (kindToSend: EmailTemplateKind, force: boolean) => {
    setIsSending(true);
    try {
      const result = await candidatesApi.sendNotification(candidate.id, {
        kind: kindToSend,
        force,
      });
      onNotified({
        last_notification_kind: result.last_notification_kind,
        last_notification_sent_at: result.last_notification_sent_at,
      });
      toast.success(
        result.sent
          ? `${NOTIFICATION_KIND_LABEL[kindToSend]} email sent`
          : "Email skipped (recently sent)",
      );
      setConflict(null);
    } catch (err) {
      if (
        err instanceof ApiError &&
        err.status === 409 &&
        err.detail &&
        typeof err.detail === "object" &&
        (err.detail as { code?: string }).code === "notification_conflict"
      ) {
        // Re-open the conflict dialog even though the main dialog is closed.
        setConflict(err.detail as NotificationConflictDetail);
        return;
      }
      toast.error(err instanceof Error ? err.message : "Failed to send email");
    } finally {
      setIsSending(false);
    }
  };

  // Close dialogs and start the 10-second undo window before dispatching.
  const send = (kindToSend: EmailTemplateKind, force: boolean) => {
    setOpen(false);
    setConflict(null);

    if (undoTimerRef.current) {
      clearTimeout(undoTimerRef.current);
    }

    const label = NOTIFICATION_KIND_LABEL[kindToSend];
    const toastId = toast.loading(`${label} email queued`, {
      duration: Infinity,
      description: "10 seconds to undo",
      cancel: {
        label: "Undo",
        onClick: () => {
          if (undoTimerRef.current) {
            clearTimeout(undoTimerRef.current);
            undoTimerRef.current = null;
          }
        },
      },
    });

    undoTimerRef.current = setTimeout(async () => {
      undoTimerRef.current = null;
      toast.dismiss(toastId);
      await dispatchSend(kindToSend, force);
    }, 10000);
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
        <div className="space-y-1">
          <CardTitle className="text-base">Candidate notifications</CardTitle>
          <p className="text-sm text-muted-foreground">
            {lastKind && lastSentAt ? (
              <>
                Last notified:{" "}
                <span className="font-medium">
                  {NOTIFICATION_KIND_LABEL[lastKind]}
                </span>{" "}
                · {new Date(lastSentAt).toLocaleString()}
              </>
            ) : (
              <>No emails sent to this candidate yet.</>
            )}
          </p>
          {hasStatusNotifMismatch && (
            <p className="flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-400">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
              Status changed since last notification — candidate may need an
              update.
            </p>
          )}
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            setKind(candidate.status === "rejected" ? "reject" : "shortlist");
            setOpen(true);
          }}
        >
          <Mail className="mr-2 h-3.5 w-3.5" />
          Notify candidate
        </Button>
      </CardHeader>

      <Dialog open={open} onOpenChange={(o) => !o && !isSending && setOpen(false)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Email {candidate.name}</DialogTitle>
            <DialogDescription>
              Pick which template to send to{" "}
              <span className="font-medium">{candidate.email}</span>. The
              candidate&apos;s internal status is unchanged by this action.
            </DialogDescription>
          </DialogHeader>

          {hasDialogConflict && (
            <div className="flex gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800/40 dark:bg-amber-900/20 dark:text-amber-300">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                A <strong>{NOTIFICATION_KIND_LABEL[lastKind!]}</strong> email
                was previously sent
                {lastSentAt && (
                  <> on {new Date(lastSentAt).toLocaleString()}</>
                )}
                . Sending a <strong>{NOTIFICATION_KIND_LABEL[kind]}</strong>{" "}
                now may confuse the candidate — consider a correction email
                first.
              </span>
            </div>
          )}

          <div className="space-y-2 py-2">
            {(
              ["shortlist", "reject", "status_correction"] as EmailTemplateKind[]
            ).map((k) => (
              <label
                key={k}
                className={`flex cursor-pointer items-start gap-3 rounded-md border p-3 text-sm transition-colors ${
                  kind === k
                    ? "border-primary bg-primary/5"
                    : "hover:bg-muted/50"
                }`}
              >
                <input
                  type="radio"
                  name="notify-kind"
                  className="mt-0.5"
                  checked={kind === k}
                  onChange={() => setKind(k)}
                  disabled={isSending}
                />
                <span className="flex-1">
                  <span className="block font-medium">
                    {NOTIFICATION_KIND_LABEL[k]}
                  </span>
                  <span className="block text-xs text-muted-foreground">
                    {k === "shortlist" &&
                      "Tell the candidate they're moving to the next round."}
                    {k === "reject" &&
                      "Inform the candidate that their application is unsuccessful."}
                    {k === "status_correction" &&
                      "Apologise for a prior message sent in error and let the candidate know a follow-up will arrive."}
                  </span>
                </span>
              </label>
            ))}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              disabled={isSending}
              onClick={() => setOpen(false)}
            >
              Cancel
            </Button>
            <Button disabled={isSending} onClick={() => send(kind, false)}>
              Send email
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Conflict confirmation: candidate already received an opposing email. */}
      <AlertDialog
        open={conflict !== null}
        onOpenChange={(o) => !o && !isSending && setConflict(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Send a contradictory email?</AlertDialogTitle>
            <AlertDialogDescription>
              {conflict && (
                <>
                  This candidate was previously emailed a{" "}
                  <span className="font-medium">
                    {NOTIFICATION_KIND_LABEL[conflict.previous_kind]}
                  </span>{" "}
                  notification
                  {conflict.last_sent_at && (
                    <> on {new Date(conflict.last_sent_at).toLocaleString()}</>
                  )}
                  . Sending a{" "}
                  <span className="font-medium">
                    {NOTIFICATION_KIND_LABEL[conflict.requested_kind]}
                  </span>{" "}
                  email now will likely confuse them. Consider sending a
                  correction email first to apologise and explain a follow-up
                  is coming.
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <AlertDialogCancel disabled={isSending}>Cancel</AlertDialogCancel>
            <Button
              variant="outline"
              disabled={isSending}
              onClick={() => send("status_correction", false)}
            >
              Send correction first
            </Button>
            <AlertDialogAction
              disabled={isSending}
              onClick={(e) => {
                e.preventDefault();
                send(kind, true);
              }}
            >
              Send anyway
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}
