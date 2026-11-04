"use client";

import { useEffect, useState } from "react";

import { Loader2, Mail, Trash2, UserPlus, Users } from "lucide-react";
import { toast } from "sonner";

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
import { Separator } from "@/components/ui/separator";
import { team } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { TeamInvite, TeamMember } from "@/lib/types";

const formatDate = (iso: string) =>
  new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });

export default function TeamSettingsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [invites, setInvites] = useState<TeamInvite[]>([]);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [revokingId, setRevokingId] = useState<string | null>(null);


  useEffect(() => {
    let active = true;
    Promise.all([team.members(), isAdmin ? team.listInvites() : Promise.resolve({ invites: [] })]).then(
      ([m, i]) => { if (active) { setMembers(m.members); setInvites(i.invites); } },
      (err: unknown) => { if (active) toast.error(err instanceof Error ? err.message : "Failed to load team"); },
    ).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [isAdmin]);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = email.trim();
    if (!trimmed) return;
    setSubmitting(true);
    try {
      const invite = await team.createInvite(trimmed);
      setInvites((prev) => [invite, ...prev]);
      setEmail("");
      toast.success(`Invite sent to ${invite.email}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to send invite";
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleRevoke = async (invite: TeamInvite) => {
    if (
      !window.confirm(
        `Revoke invite for ${invite.email}? They won't be able to use the existing link.`,
      )
    ) {
      return;
    }
    setRevokingId(invite.id);
    try {
      await team.revokeInvite(invite.id);
      setInvites((prev) => prev.filter((i) => i.id !== invite.id));
      toast.success(`Revoked invite for ${invite.email}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to revoke";
      toast.error(message);
    } finally {
      setRevokingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Team & invites</h1>
        <p className="text-muted-foreground">
          Invite other recruiters in your company to collaborate on the same
          jobs and candidate pipeline.
        </p>
      </div>

      {isAdmin && <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <UserPlus className="h-5 w-5 text-muted-foreground" />
            <CardTitle>Invite a teammate</CardTitle>
          </div>
          <CardDescription>
            They join as recruiters and receive an email with a one-time link that expires in
            seven days.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleInvite} className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1 space-y-2">
              <Label htmlFor="invite-email">Email address</Label>
              <Input
                id="invite-email"
                type="email"
                placeholder="teammate@yourcompany.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={submitting}
              />
            </div>
            <Button type="submit" disabled={submitting || !email.trim()}>
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Sending…
                </>
              ) : (
                <>
                  <Mail className="mr-2 h-4 w-4" /> Send invite
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>}

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Mail className="h-5 w-5 text-muted-foreground" />
            <CardTitle>Pending invites</CardTitle>
          </div>
          <CardDescription>
            Outstanding invitations. Revoke any that should no longer be valid.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : invites.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No pending invites.
            </p>
          ) : (
            <ul className="divide-y">
              {invites.map((invite) => (
                <li
                  key={invite.id}
                  className="flex flex-wrap items-center justify-between gap-3 py-3"
                >
                  <div>
                    <p className="text-sm font-medium">{invite.email}</p>
                    <p className="text-xs text-muted-foreground">
                      Sent {formatDate(invite.created_at)} · Expires{" "}
                      {formatDate(invite.expires_at)}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRevoke(invite)}
                    disabled={revokingId === invite.id}
                  >
                    {revokingId === invite.id ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="mr-2 h-4 w-4" />
                    )}
                    Revoke
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Separator />

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-muted-foreground" />
            <CardTitle>Members</CardTitle>
          </div>
          <CardDescription>
            Everyone with access to this company workspace.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : (
            <ul className="divide-y">
              {members.map((m) => (
                <li
                  key={m.id}
                  className="flex flex-wrap items-center justify-between gap-3 py-3"
                >
                  <div>
                    <p className="text-sm font-medium">{m.name}</p>
                    <p className="text-xs text-muted-foreground">{m.email}</p>
                  </div>
                  <Badge variant={m.is_active ? "secondary" : "outline"} className="capitalize">
                    {m.role}
                  </Badge>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
