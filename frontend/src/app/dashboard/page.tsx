"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Briefcase,
  Users,
  BarChart3,
  TrendingUp,
  Clock,
  Plus,
  ArrowRight,
  Loader2,
  CheckCircle2,
  UserCheck,
  UserX,
} from "lucide-react";

import { jobs as jobsApi } from "@/lib/api";
import type { JobPosting, Candidate } from "@/lib/types";
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

interface DashboardStats {
  totalJobs: number;
  activeJobs: number;
  totalCandidates: number;
  avgScore: number | null;
  shortlisted: number;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [allJobs, setAllJobs] = useState<JobPosting[]>([]);
  const [recentCandidates, setRecentCandidates] = useState<
    (Candidate & { jobTitle: string; jobId: string })[]
  >([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const { jobs } = await jobsApi.list();
        setAllJobs(jobs);

        // Fetch candidates for active jobs to populate recent activity
        const activeJobs = jobs.filter((j) => j.status !== "archived").slice(0, 5);
        const candidateResults = await Promise.allSettled(
          activeJobs.map(async (job) => {
            const { candidates } = await jobsApi.candidates(job.id);
            return candidates.map((c) => ({
              ...c,
              jobTitle: job.title,
              jobId: job.id,
            }));
          }),
        );

        const allCandidates = candidateResults
          .filter(
            (r): r is PromiseFulfilledResult<(Candidate & { jobTitle: string; jobId: string })[]> =>
              r.status === "fulfilled",
          )
          .flatMap((r) => r.value)
          .sort(
            (a, b) =>
              new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
          )
          .slice(0, 5);

        setRecentCandidates(allCandidates);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, []);

  const stats: DashboardStats = {
    totalJobs: allJobs.length,
    activeJobs: allJobs.filter((j) => j.status === "active").length,
    totalCandidates: allJobs.reduce((sum, j) => sum + j.candidate_count, 0),
    avgScore:
      allJobs.filter((j) => j.avg_score != null).length > 0
        ? allJobs
            .filter((j) => j.avg_score != null)
            .reduce((sum, j) => sum + Number(j.avg_score), 0) /
          allJobs.filter((j) => j.avg_score != null).length
        : null,
    shortlisted: recentCandidates.filter((c) => c.status === "shortlisted").length,
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24">
        <p className="text-sm text-destructive">{error}</p>
        <Button variant="outline" onClick={() => window.location.reload()}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Welcome header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">
            Welcome back{user?.name ? `, ${user.name.split(" ")[0]}` : ""}
          </h2>
          <p className="text-muted-foreground">
            Here&apos;s an overview of your hiring pipeline.
          </p>
        </div>
        <Link href="/dashboard/jobs/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Create New Job
          </Button>
        </Link>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          title="Active Jobs"
          value={stats.activeJobs}
          subtitle={`${stats.totalJobs} total`}
          icon={Briefcase}
          href="/dashboard/jobs"
        />
        <StatCard
          title="Total Candidates"
          value={stats.totalCandidates}
          icon={Users}
          href="/dashboard/jobs"
        />
        <StatCard
          title="Avg. Score"
          value={stats.avgScore != null ? stats.avgScore.toFixed(1) : "—"}
          subtitle="across all jobs"
          icon={BarChart3}
        />
        <StatCard
          title="Shortlisted"
          value={stats.shortlisted}
          subtitle="recent candidates"
          icon={UserCheck}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent jobs */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="text-base">Active Jobs</CardTitle>
              <CardDescription>Your current open positions</CardDescription>
            </div>
            <Link href="/dashboard/jobs">
              <Button variant="ghost" size="sm" className="text-xs">
                View all
                <ArrowRight className="ml-1 h-3 w-3" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {allJobs.filter((j) => j.status !== "archived").length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <Briefcase className="h-8 w-8 text-muted-foreground/40 mb-2" />
                <p className="text-sm text-muted-foreground">
                  No active jobs yet
                </p>
                <Link href="/dashboard/jobs/new" className="mt-2">
                  <Button variant="outline" size="sm">
                    <Plus className="mr-1.5 h-3 w-3" />
                    Create one
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {allJobs
                  .filter((j) => j.status !== "archived")
                  .slice(0, 5)
                  .map((job) => (
                    <Link
                      key={job.id}
                      href={`/dashboard/jobs/${job.id}`}
                      className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-accent/50"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium truncate">
                          {job.title}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {[job.department, job.location]
                            .filter(Boolean)
                            .join(" · ") || "No department"}
                        </p>
                      </div>
                      <div className="flex items-center gap-3 ml-4 shrink-0">
                        <span className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Users className="h-3 w-3" />
                          {job.candidate_count}
                        </span>
                        {job.avg_score != null && (
                          <Badge variant="secondary" className="text-xs">
                            {Number(job.avg_score).toFixed(1)}
                          </Badge>
                        )}
                      </div>
                    </Link>
                  ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent candidates */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Recent Candidates</CardTitle>
            <CardDescription>Latest applicants across your jobs</CardDescription>
          </CardHeader>
          <CardContent>
            {recentCandidates.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <Users className="h-8 w-8 text-muted-foreground/40 mb-2" />
                <p className="text-sm text-muted-foreground">
                  No candidates yet
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Candidates will appear here once they apply.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {recentCandidates.map((candidate) => (
                  <Link
                    key={candidate.id}
                    href={`/dashboard/jobs/${candidate.jobId}/candidates/${candidate.id}`}
                    className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-accent/50"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium truncate">
                        {candidate.name}
                      </p>
                      <p className="text-xs text-muted-foreground truncate">
                        {candidate.jobTitle}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 ml-4 shrink-0">
                      <CandidateStatusBadge status={candidate.status} />
                      {candidate.overall_score != null && (
                        <Badge variant="outline" className="text-xs">
                          {Number(candidate.overall_score).toFixed(1)}
                        </Badge>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick actions */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            <Link href="/dashboard/jobs/new">
              <Button variant="outline" size="sm">
                <Plus className="mr-1.5 h-3.5 w-3.5" />
                New Job Posting
              </Button>
            </Link>
            <Link href="/dashboard/jobs">
              <Button variant="outline" size="sm">
                <Briefcase className="mr-1.5 h-3.5 w-3.5" />
                View All Jobs
              </Button>
            </Link>
            <Link href="/dashboard/settings">
              <Button variant="outline" size="sm">
                <TrendingUp className="mr-1.5 h-3.5 w-3.5" />
                Account Settings
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  href,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ComponentType<{ className?: string }>;
  href?: string;
}) {
  const content = (
    <Card className={`h-full ${href ? "transition-colors hover:bg-accent/50 cursor-pointer" : ""}`}>
      <CardContent className="pt-6 h-full">
        <div className="flex items-center justify-between h-full">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold">{value}</p>
            {subtitle && (
              <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
            )}
          </div>
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
            <Icon className="h-5 w-5 text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  );

  if (href) {
    return <Link href={href}>{content}</Link>;
  }
  return content;
}

const CANDIDATE_STATUS_CONFIG: Record<
  string,
  { label: string; className: string }
> = {
  completed: {
    label: "Completed",
    className: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  },
  shortlisted: {
    label: "Shortlisted",
    className: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  },
  rejected: {
    label: "Rejected",
    className: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  },
  in_progress: {
    label: "In Progress",
    className: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  },
  invited: {
    label: "Invited",
    className: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400",
  },
};

function CandidateStatusBadge({ status }: { status: string }) {
  const config = CANDIDATE_STATUS_CONFIG[status] ?? {
    label: status,
    className: "",
  };
  return (
    <Badge variant="secondary" className={`text-xs ${config.className}`}>
      {config.label}
    </Badge>
  );
}
