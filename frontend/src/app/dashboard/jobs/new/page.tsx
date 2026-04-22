"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Copy,
  Loader2,
  X,
} from "lucide-react";

import { jobs as jobsApi } from "@/lib/api";
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

const STEPS = ["Details", "Description", "Interview", "Review"];

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

const INTERVIEW_STYLES: { value: string; label: string; description: string }[] = [
  {
    value: "quick",
    label: "Quick",
    description: "5 questions, ~10 minutes",
  },
  {
    value: "standard",
    label: "Standard",
    description: "8 questions, ~20 minutes",
  },
  {
    value: "deep",
    label: "Deep Dive",
    description: "12 questions, ~30 minutes",
  },
];

const step1Schema = z.object({
  title: z.string().min(3, "Title must be at least 3 characters"),
  department: z.string().optional(),
  location: z.string().optional(),
  employment_type: z.string().min(1, "Select an employment type"),
});

const step2Schema = z.object({
  description: z.string().min(50, "Description must be at least 50 characters"),
});

const step3Schema = z.object({
  required_skills: z.array(z.string()).min(1, "Add at least one skill"),
  interview_style: z.string().min(1, "Select an interview style"),
  num_questions: z.number().min(3).max(15),
});

type Step1Data = z.infer<typeof step1Schema>;
type Step2Data = z.infer<typeof step2Schema>;
type Step3Data = z.infer<typeof step3Schema>;

export default function CreateJobPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [interviewLink, setInterviewLink] = useState<string | null>(null);

  // Step data
  const [step1Data, setStep1Data] = useState<Step1Data | null>(null);
  const [step2Data, setStep2Data] = useState<Step2Data | null>(null);
  const [step3Data, setStep3Data] = useState<Step3Data | null>(null);

  const handleStep1 = (data: Step1Data) => {
    setStep1Data(data);
    setCurrentStep(1);
  };

  const handleStep2 = (data: Step2Data) => {
    setStep2Data(data);
    setCurrentStep(2);
  };

  const handleStep3 = (data: Step3Data) => {
    setStep3Data(data);
    setCurrentStep(3);
  };

  const handleSubmit = async () => {
    if (!step1Data || !step2Data || !step3Data) return;

    setIsSubmitting(true);
    try {
      const payload = {
        title: step1Data.title,
        department: step1Data.department || null,
        location: step1Data.location || null,
        employment_type: step1Data.employment_type,
        description: step2Data.description,
        required_skills: step3Data.required_skills,
        interview_config: {
          style: step3Data.interview_style as "quick" | "standard" | "deep",
          num_questions: step3Data.num_questions,
        },
      };

      const { interview_link } = await jobsApi.create(payload);
      setInterviewLink(interview_link);
      toast.success("Job posting created!");
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to create job",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyLink = () => {
    if (interviewLink) {
      navigator.clipboard.writeText(interviewLink);
      toast.success("Link copied to clipboard!");
    }
  };

  // Success state
  if (interviewLink) {
    return (
      <div className="mx-auto max-w-lg space-y-6">
        <Card>
          <CardHeader className="text-center">
            <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
              <Check className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <CardTitle>Job Created!</CardTitle>
            <CardDescription>
              Share the interview link with candidates to get started.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2 rounded-md border bg-muted/50 p-3">
              <code className="flex-1 truncate text-sm">{interviewLink}</code>
              <Button variant="ghost" size="icon" onClick={copyLink}>
                <Copy className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => router.push("/dashboard")}
              >
                Back to Dashboard
              </Button>
              <Button
                className="flex-1"
                onClick={() => {
                  setInterviewLink(null);
                  setCurrentStep(0);
                  setStep1Data(null);
                  setStep2Data(null);
                  setStep3Data(null);
                }}
              >
                Create Another
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {/* Step indicator */}
      <div className="flex items-center justify-between">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push("/dashboard")}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Cancel
        </Button>
        <div className="flex items-center gap-2">
          {STEPS.map((step, i) => (
            <div key={step} className="flex items-center gap-2">
              <div
                className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium ${
                  i < currentStep
                    ? "bg-primary text-primary-foreground"
                    : i === currentStep
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground"
                }`}
              >
                {i < currentStep ? (
                  <Check className="h-3.5 w-3.5" />
                ) : (
                  i + 1
                )}
              </div>
              <span
                className={`hidden text-sm sm:inline ${
                  i === currentStep
                    ? "font-medium"
                    : "text-muted-foreground"
                }`}
              >
                {step}
              </span>
              {i < STEPS.length - 1 && (
                <div className="hidden h-px w-6 bg-border sm:block" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Step content */}
      {currentStep === 0 && (
        <Step1Form defaultValues={step1Data} onNext={handleStep1} />
      )}
      {currentStep === 1 && (
        <Step2Form
          defaultValues={step2Data}
          onNext={handleStep2}
          onBack={() => setCurrentStep(0)}
        />
      )}
      {currentStep === 2 && (
        <Step3Form
          defaultValues={step3Data}
          onNext={handleStep3}
          onBack={() => setCurrentStep(1)}
        />
      )}
      {currentStep === 3 && step1Data && step2Data && step3Data && (
        <ReviewStep
          step1={step1Data}
          step2={step2Data}
          step3={step3Data}
          onBack={() => setCurrentStep(2)}
          onSubmit={handleSubmit}
          isSubmitting={isSubmitting}
        />
      )}
    </div>
  );
}

/* ── Step 1: Details ──────────────────────────────────────── */

function Step1Form({
  defaultValues,
  onNext,
}: {
  defaultValues: Step1Data | null;
  onNext: (data: Step1Data) => void;
}) {
  const isCustomDefault = defaultValues?.department
    ? !DEPARTMENTS.includes(defaultValues.department)
    : false;
  const [isCustomDept, setIsCustomDept] = useState(isCustomDefault);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<Step1Data>({
    resolver: zodResolver(step1Schema),
    defaultValues: defaultValues ?? {
      title: "",
      department: "",
      location: "",
      employment_type: "",
    },
  });

  const handleDeptChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    if (val === "__custom__") {
      setIsCustomDept(true);
      setValue("department", "");
    } else {
      setIsCustomDept(false);
      setValue("department", val);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Job Details</CardTitle>
        <CardDescription>
          Basic information about the position.
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit(onNext)}>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="title">Job Title *</Label>
            <Input
              id="title"
              placeholder="Senior Marketing Manager"
              {...register("title")}
            />
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
                    id="department"
                    placeholder="Enter department..."
                    {...register("department")}
                    autoFocus
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="shrink-0"
                    onClick={() => {
                      setIsCustomDept(false);
                      setValue("department", "");
                    }}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <select
                  id="department"
                  className="flex h-9 w-full rounded-md border border-input bg-background text-foreground px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring [&>option]:bg-background [&>option]:text-foreground"
                  defaultValue={defaultValues?.department ?? ""}
                  onChange={handleDeptChange}
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
        <div className="flex justify-end p-6 pt-0">
          <Button type="submit">
            Next
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </div>
      </form>
    </Card>
  );
}

/* ── Step 2: Description ──────────────────────────────────── */

function Step2Form({
  defaultValues,
  onNext,
  onBack,
}: {
  defaultValues: Step2Data | null;
  onNext: (data: Step2Data) => void;
  onBack: () => void;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<Step2Data>({
    resolver: zodResolver(step2Schema),
    defaultValues: defaultValues ?? { description: "" },
  });

  const desc = watch("description");

  return (
    <Card>
      <CardHeader>
        <CardTitle>Job Description</CardTitle>
        <CardDescription>
          Describe the role, responsibilities, and requirements.
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit(onNext)}>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="description">Description *</Label>
            <Textarea
              id="description"
              placeholder="Describe the role, responsibilities, requirements, and ideal candidate profile..."
              rows={10}
              {...register("description")}
            />
            <div className="flex items-center justify-between">
              {errors.description ? (
                <p className="text-sm text-destructive">
                  {errors.description.message}
                </p>
              ) : (
                <span />
              )}
              <span className="text-xs text-muted-foreground">
                {desc?.length ?? 0} / 50 min
              </span>
            </div>
          </div>
        </CardContent>
        <div className="flex justify-between p-6 pt-0">
          <Button variant="outline" type="button" onClick={onBack}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <Button type="submit">
            Next
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </div>
      </form>
    </Card>
  );
}

/* ── Step 3: Interview Config ─────────────────────────────── */

function Step3Form({
  defaultValues,
  onNext,
  onBack,
}: {
  defaultValues: Step3Data | null;
  onNext: (data: Step3Data) => void;
  onBack: () => void;
}) {
  const [skillInput, setSkillInput] = useState("");
  const [skills, setSkills] = useState<string[]>(
    defaultValues?.required_skills ?? [],
  );
  const [style, setStyle] = useState(defaultValues?.interview_style ?? "standard");

  const numQuestions =
    style === "quick" ? 5 : style === "standard" ? 8 : 12;

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

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddSkill();
    }
  };

  const handleNext = () => {
    if (skills.length === 0) {
      toast.error("Add at least one required skill");
      return;
    }
    onNext({
      required_skills: skills,
      interview_style: style,
      num_questions: numQuestions,
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Interview Setup</CardTitle>
        <CardDescription>
          Configure how the AI interview will run.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Skills input */}
        <div className="space-y-2">
          <Label>Required Skills *</Label>
          <div className="flex gap-2">
            <Input
              placeholder="e.g. React, TypeScript..."
              value={skillInput}
              onChange={(e) => setSkillInput(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <Button type="button" variant="secondary" onClick={handleAddSkill}>
              Add
            </Button>
          </div>
          {skills.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2">
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
        </div>

        {/* Interview style */}
        <div className="space-y-2">
          <Label>Interview Style *</Label>
          <div className="grid gap-3 sm:grid-cols-3">
            {INTERVIEW_STYLES.map((opt) => (
              <button
                key={opt.value}
                type="button"
                className={`rounded-lg border p-4 text-left transition-colors ${
                  style === opt.value
                    ? "border-primary bg-primary/5 ring-1 ring-primary"
                    : "border-border hover:bg-accent/50"
                }`}
                onClick={() => setStyle(opt.value)}
              >
                <p className="text-sm font-medium">{opt.label}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {opt.description}
                </p>
              </button>
            ))}
          </div>
        </div>
      </CardContent>
      <div className="flex justify-between p-6 pt-0">
        <Button variant="outline" type="button" onClick={onBack}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <Button type="button" onClick={handleNext}>
          Next
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </Card>
  );
}

/* ── Step 4: Review ───────────────────────────────────────── */

function ReviewStep({
  step1,
  step2,
  step3,
  onBack,
  onSubmit,
  isSubmitting,
}: {
  step1: Step1Data;
  step2: Step2Data;
  step3: Step3Data;
  onBack: () => void;
  onSubmit: () => void;
  isSubmitting: boolean;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Review & Create</CardTitle>
        <CardDescription>
          Confirm the details before creating your job posting.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Details */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            Details
          </h4>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <span className="text-muted-foreground">Title</span>
            <span className="font-medium">{step1.title}</span>
            {step1.department && (
              <>
                <span className="text-muted-foreground">Department</span>
                <span>{step1.department}</span>
              </>
            )}
            {step1.location && (
              <>
                <span className="text-muted-foreground">Location</span>
                <span>{step1.location}</span>
              </>
            )}
            <span className="text-muted-foreground">Type</span>
            <span>{step1.employment_type}</span>
          </div>
        </div>

        {/* Description */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            Description
          </h4>
          <p className="text-sm whitespace-pre-wrap leading-relaxed">
            {step2.description.slice(0, 300)}
            {step2.description.length > 300 && "..."}
          </p>
        </div>

        {/* Interview Config */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            Interview
          </h4>
          <div className="flex flex-wrap gap-2">
            {step3.required_skills.map((skill) => (
              <Badge key={skill} variant="secondary">
                {skill}
              </Badge>
            ))}
          </div>
          <p className="text-sm text-muted-foreground">
            Style:{" "}
            <span className="font-medium text-foreground capitalize">
              {step3.interview_style}
            </span>{" "}
            · {step3.num_questions} questions
          </p>
        </div>
      </CardContent>
      <div className="flex justify-between p-6 pt-0">
        <Button variant="outline" type="button" onClick={onBack}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <Button onClick={onSubmit} disabled={isSubmitting}>
          {isSubmitting && (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          )}
          Create Job Posting
        </Button>
      </div>
    </Card>
  );
}
