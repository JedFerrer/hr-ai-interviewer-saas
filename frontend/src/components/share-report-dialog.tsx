"use client";

import { useState } from "react";
import { Copy, Loader2, Share2, Trash2 } from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";

import { share } from "@/lib/api";
import type { ShareTokenResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

interface Props {
  candidateId: string;
  candidateName: string;
}

/**
 * Share-evaluation-report dialog.
 *
 * Generates a public, time-limited URL the HR user can send externally.
 * The raw token is displayed exactly once; the backend stores only its hash.
 * Revoking deletes the token server-side immediately.
 */
export function ShareReportDialog({ candidateId, candidateName }: Props) {
  const [open, setOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [shareData, setShareData] = useState<ShareTokenResponse | null>(null);

  const generate = async () => {
    setIsLoading(true);
    try {
      const data = await share.create(candidateId);
      setShareData(data);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to create share link",
      );
    } finally {
      setIsLoading(false);
    }
  };

  const revoke = async () => {
    if (!shareData) return;
    setIsLoading(true);
    try {
      await share.revoke(candidateId, shareData.token_id);
      setShareData(null);
      toast.success("Share link revoked");
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to revoke link",
      );
    } finally {
      setIsLoading(false);
    }
  };

  const copy = async () => {
    if (!shareData) return;
    const fullUrl = absoluteUrl(shareData.url);
    try {
      await navigator.clipboard.writeText(fullUrl);
      toast.success("Link copied to clipboard");
    } catch {
      toast.error("Could not copy automatically — select the URL manually.");
    }
  };

  const handleOpenChange = (next: boolean) => {
    setOpen(next);
    // Reset on close so reopening doesn't expose a stale (potentially revoked)
    // token from the previous session.
    if (!next) setShareData(null);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Share2 className="mr-2 h-3.5 w-3.5" />
          Share Report
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Share evaluation report</DialogTitle>
          <DialogDescription>
            Generates a public, read-only link to {candidateName}&rsquo;s
            evaluation. The link expires automatically and can be revoked at
            any time. Internal HR data (resume, integrity signals, internal
            notes) is never shared.
          </DialogDescription>
        </DialogHeader>

        {!shareData ? (
          <div className="flex justify-center py-6">
            <Button onClick={generate} disabled={isLoading}>
              {isLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Share2 className="mr-2 h-4 w-4" />
              )}
              Generate share link
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex gap-2">
              <Input
                readOnly
                value={absoluteUrl(shareData.url)}
                onFocus={(e) => e.currentTarget.select()}
                className="font-mono text-xs"
              />
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={copy}
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Expires{" "}
              <span className="font-medium text-foreground">
                {format(new Date(shareData.expires_at), "MMM d, yyyy 'at' h:mm a")}
              </span>
              . You won&rsquo;t be able to view this link again after closing
              this dialog.
            </p>
          </div>
        )}

        <DialogFooter>
          {shareData && (
            <Button
              type="button"
              variant="outline"
              onClick={revoke}
              disabled={isLoading}
              className="text-destructive hover:bg-destructive hover:text-destructive-foreground"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Revoke
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Convert backend-returned absolute or relative URL into a browser-usable URL. */
function absoluteUrl(url: string): string {
  if (url.startsWith("http://") || url.startsWith("https://")) {
    // Backend may return its own host (e.g. http://localhost:8000) which won't
    // resolve in the user's browser when running through the Next.js proxy.
    // Replace the host with the current window origin.
    try {
      const u = new URL(url);
      return `${window.location.origin}${u.pathname}${u.search}${u.hash}`;
    } catch {
      return url;
    }
  }
  return `${window.location.origin}${url.startsWith("/") ? "" : "/"}${url}`;
}
