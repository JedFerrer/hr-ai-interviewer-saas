"use client";

import { useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import {
  Briefcase,
  Building2,
  ChevronDown,
  ChevronUp,
  Loader2,
  Upload,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";

import { interview as interviewApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface JobInfo {
  job_title: string;
  company_name: string;
  description: string;
}

export default function ApplicationPage() {
  const { token } = useParams<{ token: string }>();
  const [jobInfo, setJobInfo] = useState<JobInfo | null>(null);
  const [isLoadingJob, setIsLoadingJob] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [candidateName, setCandidateName] = useState("");
  const [candidateEmail, setCandidateEmail] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Post-submit state
  const [submitted, setSubmitted] = useState(false);

  // JD expand/collapse
  const [descExpanded, setDescExpanded] = useState(false);
  const [isOverflowing, setIsOverflowing] = useState(false);
  const descRef = useRef<HTMLDivElement>(null);

  // Load job info
  useEffect(() => {
    interviewApi
      .getJob(token)
      .then(setJobInfo)
      .catch((err) => setError(err.message))
      .finally(() => setIsLoadingJob(false));
  }, [token]);

  // Detect whether the description overflows its collapsed height
  useEffect(() => {
    if (descRef.current) {
      setIsOverflowing(descRef.current.scrollHeight > descRef.current.clientHeight);
    }
  }, [jobInfo]);

  const handleSubmit = async () => {
    if (!candidateName.trim() || !candidateEmail.trim()) {
      toast.error("Please enter your name and email.");
      return;
    }
    if (!resumeFile) {
      toast.error("Please upload your resume.");
      return;
    }
    setIsSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("job_token", token);
      formData.append("candidate_name", candidateName.trim());
      formData.append("candidate_email", candidateEmail.trim());
      formData.append("resume", resumeFile);

      await interviewApi.apply(formData);
      setSubmitted(true);
      toast.success("Application submitted successfully!");
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to submit application",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoadingJob) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !jobInfo) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md">
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <AlertTriangle className="h-12 w-12 text-destructive" />
            <h2 className="text-lg font-semibold">Position Not Found</h2>
            <p className="text-sm text-muted-foreground text-center">
              {error ?? "This application link is invalid or has expired."}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ── Success ──
  if (submitted) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <Card className="w-full max-w-lg">
          <CardContent className="flex flex-col items-center gap-6 py-12 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
              <CheckCircle2 className="h-8 w-8 text-green-600 dark:text-green-400" />
            </div>
            <div className="space-y-2">
              <h2 className="text-xl font-semibold">Application Received!</h2>
              <p className="text-sm text-muted-foreground max-w-md">
                Thank you for applying for <strong>{jobInfo.job_title}</strong>{" "}
                at <strong>{jobInfo.company_name}</strong>.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ── Application Form ──
  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-lg">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Briefcase className="h-6 w-6" />
          </div>
          <CardTitle className="text-xl">{jobInfo.job_title}</CardTitle>
          <CardDescription className="flex items-center justify-center gap-1">
            <Building2 className="h-3.5 w-3.5" />
            {jobInfo.company_name}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Job description — collapsed to ~5 lines, expandable */}
          <div className="rounded-lg border bg-muted/40 p-3">
            <div
              ref={descRef}
              className={`text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap overflow-hidden transition-all duration-300 ${
                descExpanded ? "max-h-none" : "max-h-30"
              }`}
            >
              {jobInfo.description}
            </div>
            {(isOverflowing || descExpanded) && (
              <button
                type="button"
                onClick={() => setDescExpanded((v) => !v)}
                className="mt-2 flex items-center gap-1 text-xs font-medium text-primary hover:underline focus:outline-none"
              >
                {descExpanded ? (
                  <>
                    <ChevronUp className="h-3.5 w-3.5" />
                    Show less
                  </>
                ) : (
                  <>
                    <ChevronDown className="h-3.5 w-3.5" />
                    Show full description
                  </>
                )}
              </button>
            )}
          </div>

          <div className="space-y-4 border-t pt-4">
            <div className="space-y-2">
              <Label htmlFor="name">Full Name *</Label>
              <Input
                id="name"
                placeholder="John Doe"
                value={candidateName}
                onChange={(e) => setCandidateName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email Address *</Label>
              <Input
                id="email"
                type="email"
                placeholder="john@example.com"
                value={candidateEmail}
                onChange={(e) => setCandidateEmail(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="resume">Resume (PDF or DOCX) *</Label>
              <div className="flex items-center gap-2">
                <Input
                  id="resume"
                  type="file"
                  accept=".pdf,.doc,.docx"
                  className="flex-1"
                  onChange={(e) =>
                    setResumeFile(e.target.files?.[0] ?? null)
                  }
                />
                {resumeFile && (
                  <Upload className="h-4 w-4 text-green-600" />
                )}
              </div>
            </div>
          </div>

          <Button
            className="w-full"
            size="lg"
            onClick={handleSubmit}
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Submitting…
              </>
            ) : (
              "Submit Application"
            )}
          </Button>

          <p className="text-xs text-muted-foreground text-center">
            After submitting, you&apos;ll receive an email with a link to complete
            your AI-powered screening interview.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
