"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import { toast } from "sonner";
import {
  ArrowLeft,
  Archive,
  ArchiveRestore,
  Copy,
  Download,
  Loader2,
  Users,
  BarChart3,
  Pencil,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

import { jobs as jobsApi, API_URL } from "@/lib/api";
import type { JobPosting, Candidate } from "@/lib/types";
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

export default function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const router = useRouter();
  const [job, setJob] = useState<JobPosting | null>(null);
  const [candidateList, setCandidateList] = useState<Candidate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    Promise.all([jobsApi.get(jobId), jobsApi.candidates(jobId)])
      .then(([jobRes, candRes]) => {
        setJob(jobRes.job);
        setCandidateList(candRes.candidates);
      })
      .catch((err) => setError(err.message))
      .finally(() => setIsLoading(false));
  }, [jobId]);

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
            <div className="flex flex-wrap gap-1.5 sm:gap-2">
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
                    <th className="pb-3 pr-3 font-medium text-muted-foreground whitespace-nowrap">
                      Name
                    </th>
                    <th className="pb-3 pr-3 font-medium text-muted-foreground whitespace-nowrap hidden sm:table-cell">
                      Email
                    </th>
                    <th className="pb-3 pr-3 font-medium text-muted-foreground whitespace-nowrap">
                      Status
                    </th>
                    <th className="pb-3 pr-3 font-medium text-muted-foreground whitespace-nowrap">
                      Score
                    </th>
                    <th className="pb-3 pr-3 font-medium text-muted-foreground whitespace-nowrap hidden md:table-cell">
                      Date
                    </th>
                    <th className="pb-3 font-medium text-muted-foreground w-12">
                      Resume
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((candidate) => (
                    <CandidateRow
                      key={candidate.id}
                      candidate={candidate}
                      jobId={jobId}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
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
}: {
  candidate: Candidate;
  jobId: string;
}) {
  return (
    <tr className="border-b last:border-0 hover:bg-accent/50 transition-colors">
      <td className="py-3">
        <Link
          href={`/dashboard/jobs/${jobId}/candidates/${candidate.id}`}
          className="font-medium hover:underline"
        >
          {candidate.name}
        </Link>
      </td>
      <td className="py-3 text-muted-foreground hidden sm:table-cell">
        {candidate.email}
      </td>
      <td className="py-3">
        <Badge
          variant="secondary"
          className={CANDIDATE_STATUS_STYLES[candidate.status] ?? ""}
        >
          {candidate.status.replace("_", " ")}
        </Badge>
      </td>
      <td
        className={`py-3 font-medium ${scoreColor(candidate.overall_score)}`}
      >
        {candidate.overall_score != null
          ? Number(candidate.overall_score).toFixed(1)
          : "—"}
      </td>
      <td className="py-3 text-muted-foreground hidden md:table-cell">
        {candidate.completed_at
          ? formatDistanceToNow(new Date(candidate.completed_at), {
              addSuffix: true,
            })
          : "—"}
      </td>
      <td className="py-3">
        {candidate.resume_url ? (
          <a
            href={`${API_URL}/candidates/${candidate.id}/resume`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center rounded-md p-1.5 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            title="Download resume"
            onClick={(e) => {
              e.stopPropagation();
              const token = localStorage.getItem("access_token");
              if (token) {
                e.preventDefault();
                fetch(`${API_URL}/candidates/${candidate.id}/resume`, {
                  headers: { Authorization: `Bearer ${token}` },
                })
                  .then((res) => {
                    if (!res.ok) throw new Error("Download failed");
                    const disposition =
                      res.headers.get("content-disposition");
                    let filename = "";
                    if (disposition) {
                      const match = disposition.match(
                        /filename\*?=(?:UTF-8''|"?)([^";]+)"?/i,
                      );
                      if (match)
                        filename = decodeURIComponent(match[1]);
                    }
                    if (!filename) {
                      const ct = res.headers.get("content-type") || "";
                      const ext =
                        ct.includes("wordprocessingml") ||
                        ct.includes("msword")
                          ? ".docx"
                          : ct.includes("pdf")
                            ? ".pdf"
                            : "";
                      filename = `${candidate.name?.replace(/\s+/g, "_") || "resume"}_resume${ext}`;
                    }
                    return res
                      .blob()
                      .then((blob) => ({ blob, filename }));
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
            }}
          >
            <Download className="h-4 w-4" />
          </a>
        ) : (
          <span className="text-muted-foreground/40">—</span>
        )}
      </td>
    </tr>
  );
}
