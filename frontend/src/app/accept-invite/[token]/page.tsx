"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { LayoutGrid, Loader2 } from "lucide-react";

import { useAuth } from "@/lib/auth";
import { invites as invitesApi } from "@/lib/api";
import type { InvitePreview } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const acceptSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  password: z
    .string()
    .min(10, "Password must be at least 10 characters")
    .refine(
      (v) => /[a-zA-Z]/.test(v) && /\d/.test(v),
      "Password must contain at least one letter and one digit",
    ),
});

type AcceptForm = z.infer<typeof acceptSchema>;

export default function AcceptInvitePage() {
  const params = useParams<{ token: string }>();
  const router = useRouter();
  const { acceptInvite } = useAuth();

  const [preview, setPreview] = useState<InvitePreview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const token = params?.token ?? "";

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await invitesApi.preview(token);
        if (!cancelled) setPreview(data);
      } catch (err) {
        if (!cancelled) {
          setPreviewError(
            err instanceof Error
              ? err.message
              : "This invitation link is invalid or has expired.",
          );
        }
      } finally {
        if (!cancelled) setPreviewLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AcceptForm>({ resolver: zodResolver(acceptSchema) });

  const onSubmit = async (data: AcceptForm) => {
    setIsSubmitting(true);
    try {
      await acceptInvite(token, data.name, data.password);
      toast.success(`Welcome to ${preview?.company_name ?? "your team"}!`);
      router.push("/dashboard");
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to accept invitation",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <LayoutGrid className="h-6 w-6" />
          </div>
          <CardTitle className="text-2xl">Join the team</CardTitle>
          <CardDescription>
            {previewLoading
              ? "Validating invitation…"
              : preview
                ? `You've been invited to join ${preview.company_name}`
                : "Invitation unavailable"}
          </CardDescription>
        </CardHeader>

        {previewLoading ? (
          <CardContent className="flex justify-center py-10">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </CardContent>
        ) : previewError || !preview ? (
          <CardContent>
            <p className="text-sm text-destructive">
              {previewError ??
                "This invitation link is invalid or has expired."}
            </p>
            <Button
              variant="outline"
              className="mt-4 w-full"
              onClick={() => router.push("/login")}
            >
              Go to sign in
            </Button>
          </CardContent>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Email</Label>
                <Input value={preview.email} disabled />
              </div>

              <div className="space-y-2">
                <Label htmlFor="name">Full name</Label>
                <Input
                  id="name"
                  type="text"
                  placeholder="Jane Doe"
                  autoComplete="name"
                  {...register("name")}
                />
                {errors.name && (
                  <p className="text-sm text-destructive">
                    {errors.name.message}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Choose a password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="At least 10 characters with a digit"
                  autoComplete="new-password"
                  {...register("password")}
                />
                {errors.password && (
                  <p className="text-sm text-destructive">
                    {errors.password.message}
                  </p>
                )}
              </div>
            </CardContent>

            <CardFooter className="flex flex-col gap-2">
              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating account…
                  </>
                ) : (
                  "Accept invitation"
                )}
              </Button>
              <p className="text-xs text-muted-foreground">
                By continuing you agree to share an account with your team&apos;s
                workspace.
              </p>
            </CardFooter>
          </form>
        )}
      </Card>
    </div>
  );
}
