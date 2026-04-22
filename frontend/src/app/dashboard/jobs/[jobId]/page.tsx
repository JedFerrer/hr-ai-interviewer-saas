"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import { toast } from "sonner";
import {
  ArrowLeft,
  Archive,
  ArchiveRestore,
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  Copy,
  Download,
  GitCompare,
  Loader2,
  Users,
  BarChart3,
  Pencil,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

import {
  jobs as jobsApi,
  candidates as candidatesApi,
  API_URL,
} from "@/lib/api";
import type { JobPosting, Candidate } from "@/lib/types";
import { ComparisonDrawer } from "@/components/comparison-drawer";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

type SortKey =
  | "overall_score"
  | "skill_match"
  | "communication"
  | "problem_solving"
  | "cultural_fit"
  | "name";

type SortOrder = "asc" | "desc";

/** Maximum number of candidates that can be compared side-by-side. */
const MAX_COMPARE = 4;
/** Minimum number of candidates needed to open the comparison view. */
const MIN_COMPARE = 2;

export default function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const router = useRouter();
  const [job, setJob] = useState<JobPosting | null>(null);
  const [candidateList, setCandidateList] = useState<Candidate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortKey, setSortKey] = useState<SortKey>("overall_score");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [compareOpen, setCompareOpen] = useState(false);
  const [actioningId, setActioningId] = useState<string | null>(null);

  const fetchCandidates = useCallback(
    (key: SortKey, order: SortOrder) =>
      jobsApi.candidates(jobId, `sort=${key}&order=${order}`),
    [jobId],
  );

  useEffect(() => {
    Promise.all([jobsApi.get(jobId), fetchCandidates(sortKey, sortOrder)])
      .then(([jobRes, candRes]) => {
        setJob(jobRes.job);
        setCandidateList(candRes.candidates);
      })
      .catch((err) => setError(err.message))
      .finally(() => setIsLoading(false));
  }, [jobId, fetchCandidates, sortKey, sortOrder]);

  // Trim selection when the underlying list changes (e.g. status filter
  // hides a previously-selected row) so we never have a stale selection.
  const filteredIds = useFilteredIds(candidateList, statusFilter);
  useEffect(() => {
    setSelectedIds((prev) => {
      const next = new Set<string>();
      for (const id of prev) if (filteredIds.has(id)) next.add(id);
      return next.size === prev.size ? prev : next;
    });
  }, [filteredIds]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortOrder((o) => (o === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      // Numeric scores default to descending (highest first); name to asc.
      setSortOrder(key === "name" ? "asc" : "desc");
    }
  };

  const toggleSelected = (candidateId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(candidateId)) {
        next.delete(candidateId);
      } else if (next.size < MAX_COMPARE) {
        next.add(candidateId);
      } else {
        toast.info(`You can compare up to ${MAX_COMPARE} candidates at once.`);
      }
      return next;
    });
  };

  const handleInlineAction = async (
    candidateId: string,
    action: "shortlist" | "reject",
  ) => {
    setActioningId(candidateId);
    try {
      const fn =
        action === "shortlist"
          ? candidatesApi.shortlist
          : candidatesApi.reject;
      const updated = await fn(candidateId);
      setCandidateList((prev) =>
        prev.map((c) =>
          c.id === candidateId ? { ...c, status: updated.status } : c,
        ),
      );
      toast.success(
        action === "shortlist"
          ? "Candidate shortlisted"
          : "Candidate rejected",
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Action failed");
    } finally {
      setActioningId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24">
        <p className="text-sm text-destructive">{error ?? "Job not found"}</p>
        <Link href="/dashboard">
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Button>
        </Link>
      </div>
    );
  }

  const interviewUrl = `${window.location.origin}/interview/${job.interview_link_token}`;
  const filtered =
    statusFilter === "all"
      ? candidateList
      : candidateList.filter((c) => c.status === statusFilter);
  const selectedCandidates = candidateList.filter((c) =>
    selectedIds.has(c.id),
  );
  const canCompare =
    selectedCandidates.length >= MIN_COMPARE &&
    selectedCandidates.length <= MAX_COMPARE;

  const copyLink = () => {
    navigator.clipboard.writeText(interviewUrl);
    toast.success("Link copied!");
  };

  const handleArchive = () => {
    jobsApi
      .delete(jobId)
      .then(() => {
        toast.success("Job archived");
        router.push("/dashboard");
      })
      .catch((err: Error) => toast.error(err.message));
  };

  const handleUnarchive = () => {
    jobsApi
      .update(jobId, { status: "active" } as Partial<JobPosting>)
      .then(() => {
        toast.success("Job reactivated");
        setJob((prev) => (prev ? { ...prev, status: "active" } : prev));
      })
      .catch((err: Error) => toast.error(err.message));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <Link href="/dashboard">
          <Button variant="ghost" size="icon" className="shrink-0 mt-0.5">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div className="flex-1 min-w-0 space-y-2">
          {/* Title + badge row */}
          <div className="flex items-center gap-3 flex-wrap">
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight break-words">
              {job.title}
            </h2>
            <Badge variant="secondary" className="shrink-0">
              {job.status}
            </Badge>
          </div>
          {/* Subtitle */}
          <p className="text-sm text-muted-foreground">
            {[
              job.department,
              job.location,
              job.employment_type
                ?.replace("_", " ")
                .replace(/\b\w/g, (c: string) => c.toUpperCase()),
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
          {/* Action buttons - below info on mobile, inline on desktop */}
          <div className="flex items-center gap-2 flex-wrap sm:hidden">
            {job.status !== "archived" && (
              <>
                <Link href={`/dashboard/jobs/${jobId}/edit`}>
                  <Button variant="outline" size="sm">
                    <Pencil className="mr-2 h-3.5 w-3.5" />
                    Edit
                  </Button>
                </Link>
                <Button variant="outline" size="sm" onClick={copyLink}>
                  <Copy className="mr-2 h-3.5 w-3.5" />
                  Copy Link
                </Button>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-destructive hover:bg-destructive hover:text-destructive-foreground"
                    >
                      <Archive className="mr-2 h-3.5 w-3.5" />
                      Archive
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Archive this job?</AlertDialogTitle>
                      <AlertDialogDescription>
                        This will archive the job posting. Candidates will no
                        longer be able to apply or start new interviews. You
                        can reactivate it later.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={handleArchive}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      >
                        Archive Job
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </>
            )}
            {job.status === "archived" && (
              <Button variant="outline" size="sm" onClick={handleUnarchive}>
                <ArchiveRestore className="mr-2 h-3.5 w-3.5" />
                Reactivate
              </Button>
            )}
          </div>
        </div>
        {/* Desktop action buttons - top right */}
        <div className="hidden sm:flex items-center gap-2 shrink-0">
          {job.status !== "archived" && (
            <>
              <Link href={`/dashboard/jobs/${jobId}/edit`}>
                <Button variant="outline" size="sm">
                  <Pencil className="mr-2 h-3.5 w-3.5" />
                  Edit
                </Button>
              </Link>
              <Button variant="outline" size="sm" onClick={copyLink}>
                <Copy className="mr-2 h-3.5 w-3.5" />
                Copy Link
              </Button>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-destructive hover:bg-destructive hover:text-destructive-foreground"
                  >
                    <Archive className="mr-2 h-3.5 w-3.5" />
                    Archive
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Archive this job?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will archive the job posting. Candidates will no
                      longer be able to apply or start new interviews. You
                      can reactivate it later.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={handleArchive}
                      className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    >
                      Archive Job
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </>
          )}
          {job.status === "archived" && (
            <Button variant="outline" size="sm" onClick={handleUnarchive}>
              <ArchiveRestore className="mr-2 h-3.5 w-3.5" />
              Reactivate
            </Button>
          )}
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="py-4 text-center">
            <Users className="mx-auto mb-1 hidden sm:block h-5 w-5 text-muted-foreground" />
            <p className="text-2xl font-bold">{job.candidate_count ?? 0}</p>
            <p className="text-xs text-muted-foreground">
              <span className="sm:hidden">Total<br />Candidates</span>
              <span className="hidden sm:inline">Total Candidates</span>
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4 text-center">
            <BarChart3 className="mx-auto mb-1 hidden sm:block h-5 w-5 text-muted-foreground" />
            <p className="text-2xl font-bold">
              {job.avg_score != null && job.avg_score !== 0
                ? Number(job.avg_score).toFixed(1)
                : "—"}
            </p>
            <p className="text-xs text-muted-foreground">
              <span className="sm:hidden">Avg<br />Score</span>
              <span className="hidden sm:inline">Avg Score</span>
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4 text-center">
            <BarChart3 className="mx-auto mb-1 hidden sm:block h-5 w-5 text-muted-foreground" />
            <p className="text-2xl font-bold">
              {candidateList.filter((c) => c.status === "completed").length}
            </p>
            <p className="text-xs text-muted-foreground">Completed</p>
          </CardContent>
        </Card>
      </div>

      {/* Candidate table */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="text-base shrink-0">Candidates</CardTitle>
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
              {[
                "all",
                "completed",
                "shortlisted",
                "rejected",
                "in_progress",
                "ready",
                "processing",
              ].map((s) => (
                <Button
                  key={s}
                  variant={statusFilter === s ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setStatusFilter(s)}
                  className="capitalize text-xs h-7 px-2 sm:h-8 sm:px-3"
                >
                  {s === "all" ? "All" : s.replace("_", " ")}
                </Button>
              ))}
              <Button
                size="sm"
                variant="default"
                disabled={!canCompare}
                onClick={() => setCompareOpen(true)}
                title={
                  canCompare
                    ? `Compare ${selectedCandidates.length} candidates`
                    : `Select ${MIN_COMPARE}–${MAX_COMPARE} candidates to compare`
                }
                className="h-7 sm:h-8 ml-2"
              >
                <GitCompare className="mr-2 h-3.5 w-3.5" />
                Compare ({selectedCandidates.length})
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filtered.length === 0 ? (
            <div className="py-12 text-center">
              <p className="text-sm text-muted-foreground">
                {candidateList.length === 0
                  ? "No candidates yet. Share the interview link to get started."
                  : "No candidates match this filter."}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="pb-3 pr-3 w-8" />
                    <SortableHeader
                      label="Name"
                      sortKey="name"
                      currentKey={sortKey}
                      currentOrder={sortOrder}
                      onClick={toggleSort}
                    />
                    <th className="pb-3 pr-3 font-medium text-muted-foreground whitespace-nowrap hidden lg:table-cell">
                      Email
                    </th>
                    <th className="pb-3 pr-3 font-medium text-muted-foreground whitespace-nowrap">
                      Status
                    </th>
                    <SortableHeader
                      label="Overall"
                      sortKey="overall_score"
                      currentKey={sortKey}
                      currentOrder={sortOrder}
                      onClick={toggleSort}
                    />
                    <SortableHeader
                      label="Skill"
                      sortKey="skill_match"
                      currentKey={sortKey}
                      currentOrder={sortOrder}
                      onClick={toggleSort}
                      className="hidden md:table-cell"
                    />
                    <SortableHeader
                      label="Comm."
                      sortKey="communication"
                      currentKey={sortKey}
                      currentOrder={sortOrder}
                      onClick={toggleSort}
                      className="hidden md:table-cell"
                    />
                    <SortableHeader
                      label="Problem"
                      sortKey="problem_solving"
                      currentKey={sortKey}
                      currentOrder={sortOrder}
                      onClick={toggleSort}
                      className="hidden lg:table-cell"
                    />
                    <SortableHeader
                      label="Culture"
                      sortKey="cultural_fit"
                      currentKey={sortKey}
                      currentOrder={sortOrder}
                      onClick={toggleSort}
                      className="hidden lg:table-cell"
                    />
                    <th className="pb-3 pr-3 font-medium text-muted-foreground whitespace-nowrap hidden xl:table-cell">
                      Rec.
                    </th>
                    <th className="pb-3 pr-3 font-medium text-muted-foreground whitespace-nowrap hidden xl:table-cell">
                      Date
                    </th>
                    <th className="pb-3 font-medium text-muted-foreground w-32">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((candidate) => (
                    <CandidateRow
                      key={candidate.id}
                      candidate={candidate}
                      jobId={jobId}
                      selected={selectedIds.has(candidate.id)}
                      selectionFull={
                        selectedIds.size >= MAX_COMPARE &&
                        !selectedIds.has(candidate.id)
                      }
                      onToggleSelected={() => toggleSelected(candidate.id)}
                      onShortlist={() =>
                        handleInlineAction(candidate.id, "shortlist")
                      }
                      onReject={() =>
                        handleInlineAction(candidate.id, "reject")
                      }
                      isActioning={actioningId === candidate.id}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <ComparisonDrawer
        jobId={jobId}
        candidates={selectedCandidates}
        open={compareOpen}
        onOpenChange={setCompareOpen}
        onShortlist={(id) => handleInlineAction(id, "shortlist")}
        onReject={(id) => handleInlineAction(id, "reject")}
        pendingId={actioningId}
      />
    </div>
  );
}

function useFilteredIds(
  list: Candidate[],
  statusFilter: string,
): Set<string> {
  // Memoised by reference equality of the inputs; recomputes only when the
  // candidate list or filter changes.
  return new Set(
    (statusFilter === "all"
      ? list
      : list.filter((c) => c.status === statusFilter)
    ).map((c) => c.id),
  );
}

function SortableHeader({
  label,
  sortKey,
  currentKey,
  currentOrder,
  onClick,
  className,
}: {
  label: string;
  sortKey: SortKey;
  currentKey: SortKey;
  currentOrder: SortOrder;
  onClick: (key: SortKey) => void;
  className?: string;
}) {
  const active = currentKey === sortKey;
  const Icon = !active
    ? ArrowUpDown
    : currentOrder === "asc"
      ? ArrowUp
      : ArrowDown;
  return (
    <th
      className={`pb-3 pr-3 font-medium text-muted-foreground whitespace-nowrap ${className ?? ""}`}
    >
      <button
        type="button"
        onClick={() => onClick(sortKey)}
        className={`inline-flex items-center gap-1 hover:text-foreground transition-colors ${
          active ? "text-foreground" : ""
        }`}
      >
        {label}
        <Icon className="h-3 w-3" />
      </button>
    </th>
  );
}

const CANDIDATE_STATUS_STYLES: Record<string, string> = {
  completed:
    "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  shortlisted:
    "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  rejected: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  in_progress:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  ready:
    "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400",
  processing:
    "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400",
  applied:
    "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400",
};

function scoreColor(score: number | null): string {
  if (score === null) return "";
  if (score >= 7) return "text-green-600 dark:text-green-400";
  if (score >= 5) return "text-yellow-600 dark:text-yellow-400";
  return "text-red-600 dark:text-red-400";
}

function CandidateRow({
  candidate,
  jobId,
  selected,
  selectionFull,
  onToggleSelected,
  onShortlist,
  onReject,
  isActioning,
}: {
  candidate: Candidate;
  jobId: string;
  selected: boolean;
  selectionFull: boolean;
  onToggleSelected: () => void;
  onShortlist: () => void;
  onReject: () => void;
  isActioning: boolean;
}) {
  const recommendationStyles: Record<string, string> = {
    strong_yes:
      "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
    yes: "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300",
    maybe:
      "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
    no: "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300",
    strong_no:
      "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  };

  return (
    <tr className="border-b last:border-0 hover:bg-accent/50 transition-colors">
      <td className="py-3 pr-2">
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggleSelected}
          disabled={selectionFull}
          aria-label={`Select ${candidate.name} for comparison`}
          className="h-4 w-4 cursor-pointer rounded border-input accent-primary disabled:cursor-not-allowed disabled:opacity-40"
        />
      </td>
      <td className="py-3 pr-3">
        <Link
          href={`/dashboard/jobs/${jobId}/candidates/${candidate.id}`}
          className="font-medium hover:underline"
        >
          {candidate.name}
        </Link>
      </td>
      <td className="py-3 pr-3 text-muted-foreground hidden lg:table-cell">
        {candidate.email}
      </td>
      <td className="py-3 pr-3">
        <Badge
          variant="secondary"
          className={CANDIDATE_STATUS_STYLES[candidate.status] ?? ""}
        >
          {candidate.status.replace("_", " ")}
        </Badge>
      </td>
      <td
        className={`py-3 pr-3 font-medium ${scoreColor(candidate.overall_score)}`}
      >
        {formatScore(candidate.overall_score)}
      </td>
      <td className="py-3 pr-3 hidden md:table-cell">
        {formatScore(candidate.skill_match)}
      </td>
      <td className="py-3 pr-3 hidden md:table-cell">
        {formatScore(candidate.communication)}
      </td>
      <td className="py-3 pr-3 hidden lg:table-cell">
        {formatScore(candidate.problem_solving)}
      </td>
      <td className="py-3 pr-3 hidden lg:table-cell">
        {formatScore(candidate.cultural_fit)}
      </td>
      <td className="py-3 pr-3 hidden xl:table-cell">
        {candidate.recommendation ? (
          <Badge
            variant="secondary"
            className={recommendationStyles[candidate.recommendation] ?? ""}
          >
            {candidate.recommendation.replace("_", " ")}
          </Badge>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </td>
      <td className="py-3 pr-3 text-muted-foreground hidden xl:table-cell">
        {candidate.completed_at
          ? formatDistanceToNow(new Date(candidate.completed_at), {
              addSuffix: true,
            })
          : "—"}
      </td>
      <td className="py-3">
        <div className="flex items-center gap-1">
          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-green-700 hover:bg-green-100 hover:text-green-800 dark:text-green-400 dark:hover:bg-green-900/30"
            onClick={onShortlist}
            disabled={isActioning || candidate.status === "shortlisted"}
            title="Shortlist"
          >
            <ThumbsUp className="h-3.5 w-3.5" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-red-700 hover:bg-red-100 hover:text-red-800 dark:text-red-400 dark:hover:bg-red-900/30"
            onClick={onReject}
            disabled={isActioning || candidate.status === "rejected"}
            title="Reject"
          >
            <ThumbsDown className="h-3.5 w-3.5" />
          </Button>
          {candidate.resume_url && (
            <a
              href={`${API_URL}/candidates/${candidate.id}/resume`}
              className="inline-flex h-7 items-center justify-center rounded-md px-2 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              title="Download resume"
              onClick={(e) => {
                e.stopPropagation();
                e.preventDefault();
                downloadResume(candidate.id, candidate.name);
              }}
            >
              <Download className="h-3.5 w-3.5" />
            </a>
          )}
        </div>
      </td>
    </tr>
  );
}

function formatScore(value: number | null): string {
  return value != null ? Number(value).toFixed(1) : "—";
}

function downloadResume(candidateId: string, candidateName: string): void {
  fetch(`${API_URL}/candidates/${candidateId}/resume`, {
    credentials: "include",
  })
    .then((res) => {
      if (!res.ok) throw new Error("Download failed");
      const disposition = res.headers.get("content-disposition");
      let filename = "";
      if (disposition) {
        const match = disposition.match(
          /filename\*?=(?:UTF-8''|"?)([^";]+)"?/i,
        );
        if (match) filename = decodeURIComponent(match[1]);
      }
      if (!filename) {
        const ct = res.headers.get("content-type") || "";
        const ext =
          ct.includes("wordprocessingml") || ct.includes("msword")
            ? ".docx"
            : ct.includes("pdf")
              ? ".pdf"
              : "";
        filename = `${candidateName?.replace(/\s+/g, "_") || "resume"}_resume${ext}`;
      }
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
}
