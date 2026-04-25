"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { ArrowLeft, Loader2, Save, X } from "lucide-react";

import { jobs as jobsApi } from "@/lib/api";
import type { JobPosting, ScreeningMode } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const EMPLOYMENT_TYPES = [
  "Full-time",
  "Part-time",
  "Contract",
  "Internship",
];

const DEPARTMENTS = [
  "Engineering",
  "Product",
  "Design",
  "Marketing",
  "Sales",
  "Customer Support",
  "Human Resources",
  "Finance",
  "Operations",
  "Legal",
  "Data Science",
  "DevOps",
];

const editSchema = z.object({
  title: z.string().min(3, "Title must be at least 3 characters"),
  department: z.string().optional(),
  location: z.string().optional(),
  employment_type: z.string().min(1, "Select an employment type"),
  description: z.string().min(50, "Description must be at least 50 characters"),
});

type EditFormData = z.infer<typeof editSchema>;

export default function EditJobPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const router = useRouter();
  const [job, setJob] = useState<JobPosting | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Skills state (managed outside react-hook-form)
  const [skills, setSkills] = useState<string[]>([]);
  const [skillInput, setSkillInput] = useState("");

  // Status-email toggle (also managed outside RHF since it's a controlled
  // boolean and not a registered field).
  const [autoSendEmails, setAutoSendEmails] = useState(false);

  // Screening policy state. Defaults match the backend's hybrid defaults
  // (75 auto-invite / 55 review) so existing jobs upgrading from `auto_all`
  // get sensible thresholds the moment they switch modes.
  const [screeningMode, setScreeningMode] = useState<ScreeningMode>("hybrid_threshold");
  const [autoInviteThreshold, setAutoInviteThreshold] = useState<number>(75);
  const [reviewThreshold, setReviewThreshold] = useState<number>(55);
  const [screeningError, setScreeningError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<EditFormData>({
    resolver: zodResolver(editSchema),
  });

  // Custom department handling
  const [isCustomDept, setIsCustomDept] = useState(false);
  const [deptValue, setDeptValue] = useState("");

  useEffect(() => {
    jobsApi
      .get(jobId)
      .then(({ job }) => {
        setJob(job);
        setSkills(job.required_skills ?? []);
        setAutoSendEmails(job.auto_send_status_emails ?? false);
        setScreeningMode(job.screening_mode ?? "hybrid_threshold");
        setAutoInviteThreshold(job.auto_invite_threshold ?? 75);
        setReviewThreshold(job.review_threshold ?? 55);
        const isCustom = job.department
          ? !DEPARTMENTS.includes(job.department)
          : false;
        setIsCustomDept(isCustom);
        setDeptValue(job.department ?? "");
        reset({
          title: job.title,
          department: job.department ?? "",
          location: job.location ?? "",
          employment_type: job.employment_type,
          description: job.description,
        });
      })
      .catch((err) => setError(err.message))
      .finally(() => setIsLoading(false));
  }, [jobId, reset]);

  const handleAddSkill = () => {
    const trimmed = skillInput.trim();
    if (trimmed && !skills.includes(trimmed)) {
      setSkills((prev) => [...prev, trimmed]);
      setSkillInput("");
    }
  };

  const handleRemoveSkill = (skill: string) => {
    setSkills((prev) => prev.filter((s) => s !== skill));
  };

  const handleSkillKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddSkill();
    }
  };

  const onSubmit = async (data: EditFormData) => {
    // Cross-field validation that mirrors the backend Pydantic rules.
    // Doing it client-side keeps a confused HR user from getting a 422.
    if (screeningMode === "hybrid_threshold") {
      if (
        !Number.isFinite(autoInviteThreshold) ||
        !Number.isFinite(reviewThreshold) ||
        autoInviteThreshold < 0 ||
        autoInviteThreshold > 100 ||
        reviewThreshold < 0 ||
        reviewThreshold > 100
      ) {
        setScreeningError("Thresholds must be between 0 and 100.");
        return;
      }
      if (reviewThreshold > autoInviteThreshold) {
        setScreeningError(
          "Review threshold must be less than or equal to the auto-invite threshold.",
        );
        return;
      }
    }
    setScreeningError(null);

    setIsSaving(true);
    try {
      const payload: Record<string, unknown> = {
        title: data.title,
        description: data.description,
        department: isCustomDept ? deptValue : data.department || null,
        location: data.location || null,
        employment_type: data.employment_type,
        required_skills: skills,
        auto_send_status_emails: autoSendEmails,
        screening_mode: screeningMode,
        auto_invite_threshold: autoInviteThreshold,
        review_threshold: reviewThreshold,
      };

      await jobsApi.update(jobId, payload as Partial<JobPosting>);
      toast.success("Job updated successfully");
      router.push(`/dashboard/jobs/${jobId}`);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to update job",
      );
    } finally {
      setIsSaving(false);
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

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href={`/dashboard/jobs/${jobId}`}>
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h2 className="text-xl font-bold tracking-tight">Edit Job</h2>
          <p className="text-sm text-muted-foreground">{job.title}</p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)}>
        {/* Details */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">Job Details</CardTitle>
            <CardDescription>
              Update basic information about the position.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="title">Job Title *</Label>
              <Input id="title" {...register("title")} />
              {errors.title && (
                <p className="text-sm text-destructive">
                  {errors.title.message}
                </p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="department">Department</Label>
                {isCustomDept ? (
                  <div className="flex gap-2">
                    <Input
                      value={deptValue}
                      onChange={(e) => setDeptValue(e.target.value)}
                      placeholder="Enter department..."
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="shrink-0"
                      onClick={() => {
                        setIsCustomDept(false);
                        setDeptValue("");
                      }}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ) : (
                  <select
                    className="flex h-9 w-full rounded-md border border-input bg-background text-foreground px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring [&>option]:bg-background [&>option]:text-foreground"
                    value={deptValue}
                    onChange={(e) => {
                      if (e.target.value === "__custom__") {
                        setIsCustomDept(true);
                        setDeptValue("");
                      } else {
                        setDeptValue(e.target.value);
                      }
                    }}
                  >
                    <option value="">Select department...</option>
                    {DEPARTMENTS.map((dept) => (
                      <option key={dept} value={dept}>
                        {dept}
                      </option>
                    ))}
                    <option value="__custom__">Custom...</option>
                  </select>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="location">Location</Label>
                <Input
                  id="location"
                  placeholder="Remote"
                  {...register("location")}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="employment_type">Employment Type *</Label>
              <select
                id="employment_type"
                className="flex h-9 w-full rounded-md border border-input bg-background text-foreground px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring [&>option]:bg-background [&>option]:text-foreground"
                {...register("employment_type")}
              >
                <option value="">Select type...</option>
                {EMPLOYMENT_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
              {errors.employment_type && (
                <p className="text-sm text-destructive">
                  {errors.employment_type.message}
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Description */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">Description</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Textarea
              id="description"
              rows={8}
              {...register("description")}
            />
            {errors.description && (
              <p className="text-sm text-destructive">
                {errors.description.message}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Skills */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">Required Skills</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2">
              <Input
                placeholder="e.g. React, TypeScript..."
                value={skillInput}
                onChange={(e) => setSkillInput(e.target.value)}
                onKeyDown={handleSkillKeyDown}
              />
              <Button
                type="button"
                variant="secondary"
                onClick={handleAddSkill}
              >
                Add
              </Button>
            </div>
            {skills.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {skills.map((skill) => (
                  <Badge key={skill} variant="secondary" className="gap-1 pr-1">
                    {skill}
                    <button
                      type="button"
                      onClick={() => handleRemoveSkill(skill)}
                      className="ml-1 rounded-full p-0.5 hover:bg-muted-foreground/20"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Screening policy */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">Screening policy</CardTitle>
            <CardDescription>
              Decide how applicants are routed after their resume is parsed and
              scored against this job.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="screening_mode">Mode</Label>
              <select
                id="screening_mode"
                className="flex h-9 w-full rounded-md border border-input bg-background text-foreground px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring [&>option]:bg-background [&>option]:text-foreground"
                value={screeningMode}
                onChange={(e) =>
                  setScreeningMode(e.target.value as ScreeningMode)
                }
              >
                <option value="auto_all">
                  Auto-invite everyone (legacy behaviour)
                </option>
                <option value="hybrid_threshold">
                  Hybrid — score and route by threshold
                </option>
                <option value="manual_all">
                  Manual review for every applicant
                </option>
              </select>
              <p className="text-xs text-muted-foreground">
                Hybrid is the recommended default: strong matches get an
                interview link automatically, weaker or borderline matches wait
                for your approval.
              </p>
            </div>

            {screeningMode === "hybrid_threshold" && (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="auto_invite_threshold">
                    Auto-invite at score ≥
                  </Label>
                  <Input
                    id="auto_invite_threshold"
                    type="number"
                    min={0}
                    max={100}
                    value={autoInviteThreshold}
                    onChange={(e) =>
                      setAutoInviteThreshold(Number(e.target.value))
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Candidates at or above this score are emailed an interview
                    link automatically.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="review_threshold">
                    Send to review below
                  </Label>
                  <Input
                    id="review_threshold"
                    type="number"
                    min={0}
                    max={100}
                    value={reviewThreshold}
                    onChange={(e) =>
                      setReviewThreshold(Number(e.target.value))
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Anything below the auto-invite score lands in the HR review
                    queue — no auto-rejection.
                  </p>
                </div>
              </div>
            )}

            {screeningError && (
              <p className="text-sm text-destructive">{screeningError}</p>
            )}
          </CardContent>
        </Card>

        {/* Notifications */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">Candidate notifications</CardTitle>
            <CardDescription>
              Control which automated emails candidates receive about their
              status on this job.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <label className="flex cursor-pointer items-start gap-3">
              <input
                type="checkbox"
                checked={autoSendEmails}
                onChange={(e) => setAutoSendEmails(e.target.checked)}
                className="mt-0.5 h-4 w-4 cursor-pointer rounded border-input accent-primary"
              />
              <div className="space-y-0.5">
                <p className="text-sm font-medium">
                  Send status emails automatically
                </p>
                <p className="text-xs text-muted-foreground">
                  When a candidate is shortlisted or rejected, send them the
                  corresponding email using your{" "}
                  <Link
                    href="/dashboard/settings/email-templates"
                    className="underline hover:text-foreground"
                  >
                    company templates
                  </Link>
                  .
                </p>
              </div>
            </label>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex items-center justify-between">
          <Link href={`/dashboard/jobs/${jobId}`}>
            <Button variant="outline" type="button">
              Cancel
            </Button>
          </Link>
          <Button type="submit" disabled={isSaving}>
            {isSaving ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            Save Changes
          </Button>
        </div>
      </form>
    </div>
  );
}
