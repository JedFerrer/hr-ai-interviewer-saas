"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, Loader2, Mail, RotateCcw, Save } from "lucide-react";
import { toast } from "sonner";

import { emailTemplates } from "@/lib/api";
import type {
  EmailTemplateBody,
  EmailTemplateKind,
  EmailTemplates,
} from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

const PLACEHOLDERS = [
  { token: "{{candidate_name}}", example: "Alice Johnson" },
  { token: "{{job_title}}", example: "Senior Engineer" },
  { token: "{{company_name}}", example: "Acme Corp" },
] as const;

const KIND_META: Record<
  EmailTemplateKind,
  { title: string; description: string }
> = {
  shortlist: {
    title: "Shortlist email",
    description:
      "Sent when you click \u201cNotify candidate\u201d on a shortlisted candidate.",
  },
  reject: {
    title: "Rejection email",
    description:
      "Sent when you click \u201cNotify candidate\u201d on a rejected candidate.",
  },
  status_correction: {
    title: "Correction email",
    description:
      "Sent to apologise when a previous email went out in error \u2014 the candidate is told a follow-up is on the way.",
  },
};

const TEMPLATE_KINDS: readonly EmailTemplateKind[] = [
  "shortlist",
  "reject",
  "status_correction",
] as const;

export default function EmailTemplatesPage() {
  const [templates, setTemplates] = useState<EmailTemplates | null>(null);
  const [originals, setOriginals] = useState<EmailTemplates | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [saving, setSaving] = useState<EmailTemplateKind | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    emailTemplates
      .get()
      .then((data) => {
        setTemplates(data);
        setOriginals(data);
      })
      .catch((err) => setError(err.message))
      .finally(() => setIsLoading(false));
  }, []);

  const setField = (
    kind: EmailTemplateKind,
    field: keyof EmailTemplateBody,
    value: string,
  ) =>
    setTemplates((prev) =>
      prev
        ? {
            ...prev,
            [kind]: { ...prev[kind], [field]: value },
          }
        : prev,
    );

  const isDirty = useMemo(() => {
    const empty: Record<EmailTemplateKind, boolean> = {
      shortlist: false,
      reject: false,
      status_correction: false,
    };
    if (!templates || !originals) return empty;
    const result = { ...empty };
    for (const kind of TEMPLATE_KINDS) {
      result[kind] =
        templates[kind].subject !== originals[kind].subject ||
        templates[kind].body_html !== originals[kind].body_html;
    }
    return result;
  }, [templates, originals]);

  const save = async (kind: EmailTemplateKind) => {
    if (!templates) return;
    setSaving(kind);
    try {
      const updated = await emailTemplates.update({
        [kind]: templates[kind],
      });
      setTemplates(updated);
      setOriginals(updated);
      toast.success(`${KIND_META[kind].title} saved`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(null);
    }
  };

  const revert = (kind: EmailTemplateKind) => {
    if (!originals) return;
    setTemplates((prev) =>
      prev ? { ...prev, [kind]: originals[kind] } : prev,
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !templates) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24">
        <p className="text-sm text-destructive">
          {error ?? "Failed to load templates"}
        </p>
        <Link href="/dashboard/settings">
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Settings
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/dashboard/settings">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Status email templates
          </h1>
          <p className="text-sm text-muted-foreground">
            Customise the messages candidates receive when shortlisted,
            rejected, or when a previous email needs to be corrected.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Available variables</CardTitle>
          <CardDescription>
            Placeholders are substituted with each candidate&rsquo;s details
            when the email is sent.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {PLACEHOLDERS.map((p) => (
            <Badge key={p.token} variant="secondary" className="font-mono">
              {p.token}
            </Badge>
          ))}
        </CardContent>
      </Card>

      {TEMPLATE_KINDS.map((kind) => {
        const t = templates[kind];
        const dirty = isDirty[kind];
        return (
          <Card key={kind}>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Mail className="h-5 w-5 text-muted-foreground" />
                <CardTitle className="text-base">
                  {KIND_META[kind].title}
                </CardTitle>
              </div>
              <CardDescription>{KIND_META[kind].description}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor={`${kind}-subject`}>Subject</Label>
                <Input
                  id={`${kind}-subject`}
                  value={t.subject}
                  onChange={(e) => setField(kind, "subject", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor={`${kind}-body`}>HTML body</Label>
                <Textarea
                  id={`${kind}-body`}
                  rows={8}
                  className="font-mono text-xs"
                  value={t.body_html}
                  onChange={(e) =>
                    setField(kind, "body_html", e.target.value)
                  }
                />
              </div>

              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-wide text-muted-foreground">
                  Live preview
                </Label>
                <Preview body={t.body_html} subject={t.subject} />
              </div>

              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => revert(kind)}
                  disabled={!dirty || saving === kind}
                >
                  <RotateCcw className="mr-2 h-3.5 w-3.5" />
                  Revert
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => save(kind)}
                  disabled={!dirty || saving === kind}
                >
                  {saving === kind ? (
                    <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Save className="mr-2 h-3.5 w-3.5" />
                  )}
                  Save
                </Button>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

function Preview({ body, subject }: { body: string; subject: string }) {
  // Substitute placeholders with example values so HR sees what candidates
  // will actually receive.
  const renderedSubject = substitute(subject);
  const renderedBody = substitute(body);
  return (
    <div className="rounded-md border bg-muted/30 p-3">
      <p className="mb-2 text-xs text-muted-foreground">
        <span className="font-semibold">Subject:</span> {renderedSubject}
      </p>
      <div
        className="prose prose-sm max-w-none text-sm dark:prose-invert"
        // The preview is end-user-controlled but only displayed within the
        // authenticated dashboard to the user who authored it. Substituted
        // example values do not contain user-controlled HTML.
        dangerouslySetInnerHTML={{ __html: renderedBody }}
      />
    </div>
  );
}

function substitute(text: string): string {
  return PLACEHOLDERS.reduce(
    (acc, p) => acc.replaceAll(p.token, p.example),
    text,
  );
}
