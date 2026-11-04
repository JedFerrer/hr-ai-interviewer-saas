"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Plus, Briefcase, Users, BarChart3, Loader2, Archive } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { parseApiDate } from "@/lib/dates";

import { jobs as jobsApi } from "@/lib/api";
import type { JobPosting } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function JobsPage() {
  const [allJobs, setAllJobs] = useState<JobPosting[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"active" | "archived">("active");

  useEffect(() => {
    jobsApi
      .list()
      .then(({ jobs }) => setAllJobs(jobs))
      .catch((err) => setError(err.message))
      .finally(() => setIsLoading(false));
  }, []);

  const activeJobs = allJobs.filter((j) => j.status !== "archived");
  const archivedJobs = allJobs.filter((j) => j.status === "archived");
  const jobList = filter === "active" ? activeJobs : archivedJobs;

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
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Job Postings</h2>
          <p className="text-muted-foreground">
            Manage your open positions and review candidates.
          </p>
        </div>
        <Link href="/dashboard/jobs/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Create New Job
          </Button>
        </Link>
      </div>

      {/* Filter tabs */}
      <div className="flex items-center gap-1 rounded-lg border bg-muted/50 p-1 w-fit">
        <button
          onClick={() => setFilter("active")}
          className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            filter === "active"
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Briefcase className="h-3.5 w-3.5" />
          Active
          {activeJobs.length > 0 && (
            <span className="ml-1 rounded-full bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary">
              {activeJobs.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setFilter("archived")}
          className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            filter === "archived"
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Archive className="h-3.5 w-3.5" />
          Archived
          {archivedJobs.length > 0 && (
            <span className="ml-1 rounded-full bg-muted-foreground/10 px-1.5 py-0.5 text-xs font-medium text-muted-foreground">
              {archivedJobs.length}
            </span>
          )}
        </button>
      </div>

      {/* Job cards */}
      {jobList.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16">
            {filter === "active" ? (
              <>
                <Briefcase className="h-12 w-12 text-muted-foreground/50 mb-4" />
                <h3 className="text-lg font-semibold">No active job postings</h3>
                <p className="text-sm text-muted-foreground mt-1 mb-4">
                  {allJobs.length === 0
                    ? "Create your first job posting to start interviewing candidates."
                    : "All your jobs are archived. Create a new one or reactivate an archived job."}
                </p>
                <Link href="/dashboard/jobs/new">
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    Create New Job
                  </Button>
                </Link>
              </>
            ) : (
              <>
                <Archive className="h-12 w-12 text-muted-foreground/50 mb-4" />
                <h3 className="text-lg font-semibold">No archived jobs</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Archived job postings will appear here.
                </p>
              </>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 auto-rows-fr">
          {jobList.map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
        </div>
      )}
    </div>
  );
}

const STATUS_STYLES: Record<string, string> = {
  active: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  paused: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  archived: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400",
};

function JobCard({ job }: { job: JobPosting }) {
  return (
    <Link href={`/dashboard/jobs/${job.id}`} className="h-full">
      <Card className="h-full flex flex-col transition-colors hover:bg-accent/50 cursor-pointer">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <CardTitle className="text-base leading-tight">
              {job.title}
            </CardTitle>
            <Badge
              variant="secondary"
              className={STATUS_STYLES[job.status] ?? ""}
            >
              {job.status}
            </Badge>
          </div>
          {(job.department || job.location) && (
            <CardDescription>
              {[job.department, job.location].filter(Boolean).join(" · ")}
            </CardDescription>
          )}
        </CardHeader>
        <CardContent className="mt-auto">
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <Users className="h-3.5 w-3.5" />
              {job.candidate_count} candidates
            </span>
            {job.avg_score != null && (
              <span className="flex items-center gap-1">
                <BarChart3 className="h-3.5 w-3.5" />
                Avg {Number(job.avg_score).toFixed(1)}
              </span>
            )}
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Created{" "}
            {formatDistanceToNow(parseApiDate(job.created_at), {
              addSuffix: true,
            })}
          </p>
        </CardContent>
      </Card>
    </Link>
  );
}
