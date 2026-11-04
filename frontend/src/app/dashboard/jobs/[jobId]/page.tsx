"use client";

import { useState, useEffect, useCallback, useRef } from "react";
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
  GitCompare,
  Loader2,
  Users,
  BarChart3,
  Pencil,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";

import { jobs as jobsApi, candidates as candidatesApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { JobPosting, Candidate, CandidateUpdatedEvent } from "@/lib/types";
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
  const { user: currentUser } = useAuth();
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
  // Pre-screen actions (approve/reject) trigger irreversible side effects
  // (email send, interview row creation), so they always go through a
  // confirmation dialog. Store the pending request here so the parent can
  // render a single dialog driven by both the row buttons and the comparison
  // drawer.
  const [preScreenConfirm, setPreScreenConfirm] = useState<{
    candidateId: string;
    candidateName: string;
    candidateEmail: string | null;
    kind: "approve_pre_screen" | "reject_pre_screen";
  } | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  const PAGE_SIZE = 50;

  const fetchCandidates = useCallback(
    (key: SortKey, order: SortOrder, offset = 0) =>
      jobsApi.candidates(jobId, { sort: key, order, limit: PAGE_SIZE, offset }),
    [jobId],
  );

  useEffect(() => {
    Promise.all([jobsApi.get(jobId), fetchCandidates(sortKey, sortOrder, 0)])
      .then(([jobRes, candRes]) => {
        setJob(jobRes.job);
        setCandidateList(candRes.candidates);
        setTotalCount(candRes.total);
      })
      .catch((err) => setError(err.message))
      .finally(() => setIsLoading(false));
  }, [jobId, fetchCandidates, sortKey, sortOrder]);

  // Keep a ref of current candidate IDs so the SSE handler (which captures
  // a stale closure) can detect brand-new applicants without reading stale state.
  const candidateIdsRef = useRef<Set<string>>(new Set());
  useEffect(() => {
    candidateIdsRef.current = new Set(candidateList.map((c) => c.id));
  }, [candidateList]);

  // Real-time updates: subscribe to the job's SSE stream so background-pipeline
  // results AND actions taken by other recruiters in the same company appear
  // here without a refresh. For candidates already in the list we patch the row
  // in place. For brand-new applicants (not yet in the list) we fetch their
  // full details and append them, then show a notification.
  useEffect(() => {
    if (!jobId) return;
    const close = jobsApi.streamUpdates(jobId, {
      onCandidateUpdated: (event: CandidateUpdatedEvent) => {
        // Suppress no-op self-updates: optimistic UI already applied them.
        const isSelf =
          event.actor_user_id !== null &&
          currentUser !== null &&
          event.actor_user_id === currentUser.id;

        if (!candidateIdsRef.current.has(event.candidate_id)) {
          // Brand-new applicant — fetch their full details and add to the list.
          candidatesApi
            .get(event.candidate_id)
            .then((detail) => {
              setCandidateList((prev) => {
                if (prev.some((c) => c.id === detail.id)) return prev;
                return [...prev, detail];
              });
              setTotalCount((n) => n + 1);
              if (!isSelf) {
                const name = detail.name ?? event.name ?? "A candidate";
                toast.message(`New application: ${name}`, {
                  description: `Status: ${detail.status.replace(/_/g, " ")}`,
                });
              }
            })
            .catch(() => {
              // Fetch failed — silently ignore; the user can refresh.
            });
          return;
        }

        setCandidateList((prev) => {
          const idx = prev.findIndex((c) => c.id === event.candidate_id);
          if (idx === -1) return prev;
          if (prev[idx].status === event.status) return prev;
          const next = [...prev];
          next[idx] = { ...next[idx], status: event.status };
          return next;
        });

        // Toast for changes made by other recruiters or by the system, so the
        // viewer notices the row updating. Skip self-actions to avoid noise.
        if (isSelf) return;
        const who = event.actor_name ?? "The system";
        const candidateName = event.name ?? "a candidate";
        toast.message(`${who} updated ${candidateName}`, {
          description: `Status → ${event.status.replace(/_/g, " ")}`,
        });
      },
    });
    return close;
  }, [jobId, currentUser]);

  const loadMore = async () => {
    setIsLoadingMore(true);
    try {
      const res = await fetchCandidates(sortKey, sortOrder, candidateList.length);
      setCandidateList((prev) => [...prev, ...res.candidates]);
      setTotalCount(res.total);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load more");
    } finally {
      setIsLoadingMore(false);
    }
  };

  // Trim selection when the underlying list changes (e.g. status filter
  // hides a previously-selected row) so we never have a stale selection.
  const filteredIds = useFilteredIds(candidateList, statusFilter);
  // Adjust only when a selection becomes hidden; avoid an effect on every render.
  if ([...selectedIds].some((id) => !filteredIds.has(id))) {
    setSelectedIds(new Set([...selectedIds].filter((id) => filteredIds.has(id))));
  }

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
    const candidate = candidateList.find((c) => c.id === candidateId);
    if (!candidate) return;

    // For candidates awaiting pre-screen review, the same thumbs-up / thumbs-down
    // buttons mean different things: approve the candidate for an interview, or
    // reject them at the pre-screen stage. Both endpoints are intentionally
    // non-undoable (approve sends an email, reject is a terminal status).
    const isPreScreenDecision = candidate.status === "review_pending";

    setActioningId(candidateId);
    try {
      let fn: (id: string) => Promise<{ status: string }>;
      if (isPreScreenDecision) {
        fn =
          action === "shortlist"
            ? (id) => candidatesApi.approveInterview(id)
            : (id) => candidatesApi.rejectPreScreen(id);
      } else {
        fn =
          action === "shortlist"
            ? candidatesApi.shortlist
            : candidatesApi.reject;
      }
      const updated = await fn(candidateId);
      const newStatus = updated.status;
      setCandidateList((prev) =>
        prev.map((c) =>
          c.id === candidateId ? { ...c, status: newStatus as Candidate["status"] } : c,
        ),
      );

      if (isPreScreenDecision) {
        toast.success(
          action === "shortlist"
            ? "Interview invite sent"
            : "Candidate rejected at pre-screen",
        );
        return;
      }

      toast.success(
        action === "shortlist" ? "Candidate shortlisted" : "Candidate rejected",
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Action failed");
    } finally {
      setActioningId(null);
    }
  };

  // Row-level entry point: pre-screen rows route through the confirmation
  // dialog; all other rows go straight to the inline handler.
  const requestInlineAction = (
    candidate: Candidate,
    action: "shortlist" | "reject",
  ) => {
    if (candidate.status === "review_pending") {
      setPreScreenConfirm({
        candidateId: candidate.id,
        candidateName: candidate.name,
        candidateEmail: candidate.email,
        kind: action === "shortlist" ? "approve_pre_screen" : "reject_pre_screen",
      });
      return;
    }
    void handleInlineAction(candidate.id, action);
  };

  const confirmPreScreen = async () => {
    if (!preScreenConfirm) return;
    // Reuse the same handler — it already routes review_pending statuses to
    // the approve/reject pre-screen endpoints.
    await handleInlineAction(
      preScreenConfirm.candidateId,
      preScreenConfirm.kind === "approve_pre_screen" ? "shortlist" : "reject",
    );
    setPreScreenConfirm(null);
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
        <Link href="/dashboard/jobs">
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
            <p className="text-2xl font-bold">{totalCount}</p>
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
              {(() => {
                const scored = candidateList.filter((c) => c.overall_score != null);
                if (scored.length === 0) return "—";
                const avg = scored.reduce((sum, c) => sum + (c.overall_score ?? 0), 0) / scored.length;
                return avg.toFixed(1);
              })()}
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
          {/* Mobile layout: select + compare button in one row (< 1200px) */}
          <div className="flex items-center justify-between gap-3 min-[1200px]:hidden">
            <CardTitle className="text-base shrink-0">Candidates</CardTitle>
            <div className="flex items-center gap-2">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="h-8 rounded-md border border-input bg-background px-2.5 text-xs font-medium shadow-sm focus:outline-none focus:ring-1 focus:ring-ring cursor-pointer"
              >
                {[
                  { value: "all", label: "All Statuses" },
                  { value: "review_pending", label: "Awaiting Review" },
                  { value: "completed", label: "Completed" },
                  { value: "shortlisted", label: "Shortlisted" },
                  { value: "rejected", label: "Rejected" },
                  { value: "in_progress", label: "In Progress" },
                  { value: "ready", label: "Ready" },
                  { value: "processing", label: "Processing" },
                ].map(({ value, label }) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <Button
                size="sm"
                variant={canCompare ? "default" : "outline"}
                disabled={!canCompare}
                onClick={() => setCompareOpen(true)}
                title={
                  canCompare
                    ? `Compare ${selectedCandidates.length} candidates`
                    : `Select ${MIN_COMPARE}–${MAX_COMPARE} candidates to compare`
                }
                className="h-8 shrink-0"
              >
                <GitCompare className="h-3.5 w-3.5" />
                {selectedCandidates.length > 0 && (
                  <span className="ml-1.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-primary-foreground/20 px-1 text-[10px] font-bold leading-none">
                    {selectedCandidates.length}
                  </span>
                )}
              </Button>
            </div>
          </div>

          {/* Desktop layout: button filters + compare — original look (≥ 1200px) */}
          <div className="hidden min-[1200px]:flex min-[1200px]:flex-row min-[1200px]:items-center min-[1200px]:justify-between gap-3">
            <CardTitle className="text-base shrink-0">Candidates</CardTitle>
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
              {[
                "all",
                "review_pending",
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
                    <th className="pb-3 font-medium text-muted-foreground w-28">
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
                        requestInlineAction(candidate, "shortlist")
                      }
                      onReject={() =>
                        requestInlineAction(candidate, "reject")
                      }
                      isActioning={actioningId === candidate.id}
                    />
                  ))}
                </tbody>
              </table>
              {/* Load more — only when status filter is "all" so we don't
                  promise more results than the current filter can yield. */}
              {statusFilter === "all" && candidateList.length < totalCount && (
                <div className="flex flex-col items-center gap-2 pt-6 pb-2">
                  <p className="text-xs text-muted-foreground">
                    Showing {candidateList.length} of {totalCount}
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={loadMore}
                    disabled={isLoadingMore}
                  >
                    {isLoadingMore ? (
                      <>
                        <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                        Loading…
                      </>
                    ) : (
                      `Load ${Math.min(PAGE_SIZE, totalCount - candidateList.length)} more`
                    )}
                  </Button>
                </div>
              )}
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

      {/* Pre-screen confirmation: irreversible side effects (email send and
          interview row creation), so we always require an explicit confirm. */}
      <AlertDialog
        open={preScreenConfirm !== null}
        onOpenChange={(open) => !open && setPreScreenConfirm(null)}
      >
        <AlertDialogContent>
          {preScreenConfirm?.kind === "approve_pre_screen" && (
            <>
              <AlertDialogHeader>
                <AlertDialogTitle>Send interview invite?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will create an interview for{" "}
                  <span className="font-medium">
                    {preScreenConfirm.candidateName}
                  </span>{" "}
                  and email the invite link
                  {preScreenConfirm.candidateEmail ? (
                    <>
                      {" "}to{" "}
                      <span className="font-medium">
                        {preScreenConfirm.candidateEmail}
                      </span>
                    </>
                  ) : null}{" "}
                  immediately. The email cannot be recalled.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel disabled={actioningId !== null}>
                  Cancel
                </AlertDialogCancel>
                <AlertDialogAction
                  disabled={actioningId !== null}
                  onClick={(e) => {
                    e.preventDefault();
                    void confirmPreScreen();
                  }}
                >
                  {actioningId ? "Sending…" : "Approve & send invite"}
                </AlertDialogAction>
              </AlertDialogFooter>
            </>
          )}
          {preScreenConfirm?.kind === "reject_pre_screen" && (
            <>
              <AlertDialogHeader>
                <AlertDialogTitle>Reject this candidate?</AlertDialogTitle>
                <AlertDialogDescription>
                  <span className="font-medium">
                    {preScreenConfirm.candidateName}
                  </span>{" "}
                  will be marked as rejected and will not move forward to an
                  interview. No email is sent to the candidate by this action
                  — open the candidate&apos;s page and use{" "}
                  <span className="font-medium">Notify candidate</span> when
                  you&apos;re ready to send the rejection email.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel disabled={actioningId !== null}>
                  Cancel
                </AlertDialogCancel>
                <AlertDialogAction
                  disabled={actioningId !== null}
                  onClick={(e) => {
                    e.preventDefault();
                    void confirmPreScreen();
                  }}
                >
                  {actioningId ? "Rejecting…" : "Reject candidate"}
                </AlertDialogAction>
              </AlertDialogFooter>
            </>
          )}
        </AlertDialogContent>
      </AlertDialog>
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
  review_pending:
    "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400",
  error: "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300",
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
      <td className="py-3">
        <CandidateRowActions
          candidate={candidate}
          onShortlist={onShortlist}
          onReject={onReject}
          isActioning={isActioning}
        />
      </td>
    </tr>
  );
}

/* Decides which inline icon-buttons to expose for a candidate row.
 * Mirrors the candidate-detail page's stage logic:
 *   • review_pending → Approve & invite + Reject (pre-screen)
 *   • has evaluation (overall_score != null) → Shortlist + Reject
 *   • interview pending / processing / error w/o eval → no buttons
 *
 * The actual confirmation dialogs and mutation logic live in the parent
 * page; this component just decides visibility. */
function CandidateRowActions({
  candidate,
  onShortlist,
  onReject,
  isActioning,
}: {
  candidate: Candidate;
  onShortlist: () => void;
  onReject: () => void;
  isActioning: boolean;
}) {
  const isReviewPending = candidate.status === "review_pending";
  const hasEvaluation =
    candidate.overall_score !== null && candidate.overall_score !== undefined;

  if (!isReviewPending && !hasEvaluation) {
    return <span className="text-xs text-muted-foreground">—</span>;
  }

  return (
    <div className="flex items-center gap-1">
      <Button
        size="sm"
        variant="ghost"
        className="h-7 px-2 text-green-700 hover:bg-green-100 hover:text-green-800 dark:text-green-400 dark:hover:bg-green-900/30"
        onClick={onShortlist}
        disabled={isActioning || candidate.status === "shortlisted"}
        title={
          isReviewPending
            ? "Approve & send interview invite"
            : "Shortlist"
        }
      >
        <ThumbsUp className="h-3.5 w-3.5" />
      </Button>
      <Button
        size="sm"
        variant="ghost"
        className="h-7 px-2 text-red-700 hover:bg-red-100 hover:text-red-800 dark:text-red-400 dark:hover:bg-red-900/30"
        onClick={onReject}
        disabled={isActioning || candidate.status === "rejected"}
        title={
          isReviewPending
            ? "Reject at pre-screen (no interview will be sent)"
            : "Reject"
        }
      >
        <ThumbsDown className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}

function formatScore(value: number | null): string {
  return value != null ? Number(value).toFixed(1) : "—";
}
