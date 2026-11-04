"use client";

import {
  Building2,
  ChevronRight,
  Mail,
  Shield,
  User,
  Users,
} from "lucide-react";

import Link from "next/link";
import { useAuth } from "@/lib/auth";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

export default function SettingsPage() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account and company settings.
        </p>
      </div>

      <div className="grid gap-6">
        {/* Profile */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <User className="h-5 w-5 text-muted-foreground" />
              <CardTitle>Profile</CardTitle>
            </div>
            <CardDescription>Your personal account information.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Name</Label>
                <Input value={user?.name ?? ""} disabled />
              </div>
              <div className="space-y-2">
                <Label>Email</Label>
                <div className="flex items-center gap-2">
                  <Mail className="h-4 w-4 text-muted-foreground" />
                  <Input value={user?.email ?? ""} disabled />
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Role</Label>
              <div>
                <Badge variant="secondary" className="capitalize">
                  <Shield className="mr-1 h-3 w-3" />
                  {user?.role ?? "—"}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Company */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-muted-foreground" />
              <CardTitle>Company</CardTitle>
            </div>
            <CardDescription>
              Your organization details.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Company Name</Label>
              <Input value={user?.company?.name ?? ""} disabled />
            </div>
            <div className="space-y-2">
              <Label>Company ID</Label>
              <Input
                value={user?.company?.id ?? ""}
                disabled
                className="font-mono text-xs"
              />
            </div>
          </CardContent>
        </Card>

        <Separator />

        {/* Team */}
        <Link href="/dashboard/settings/team" className="block group">
          <Card className="transition-colors group-hover:border-primary/40">
            <CardContent className="flex items-center justify-between py-4">
              <div className="flex items-center gap-3">
                <Users className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">Team & invites</p>
                  <p className="text-xs text-muted-foreground">
                    Invite other recruiters to share this company workspace.
                  </p>
                </div>
              </div>
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            </CardContent>
          </Card>
        </Link>

        {/* Email templates */}
        <Link
          href="/dashboard/settings/email-templates"
          className="block group"
        >
          <Card className="transition-colors group-hover:border-primary/40">
            <CardContent className="flex items-center justify-between py-4">
              <div className="flex items-center gap-3">
                <Mail className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">Status email templates</p>
                  <p className="text-xs text-muted-foreground">
                    Customise shortlist and rejection emails sent to candidates.
                  </p>
                </div>
              </div>
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            </CardContent>
          </Card>
        </Link>

        <p className="text-sm text-muted-foreground">
          More settings (password change, notifications, integrations) coming
          soon.
        </p>
      </div>
    </div>
  );
}
