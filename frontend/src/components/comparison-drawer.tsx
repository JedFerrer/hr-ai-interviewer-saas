"use client";

import Link from "next/link";
import { ExternalLink, ThumbsDown, ThumbsUp } from "lucide-react";

import type { Candidate } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const RECOMMENDATION_STYLES: Record<string, string> = {
  strong_yes:
    "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  yes: "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300",
  maybe:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  no: "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300",
  strong_no:
    "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
};

const SCORE_ROWS: Array<{
  key: keyof Pick<
    Candidate,
    "overall_score" | "skill_match" | "communication" | "problem_solving" | "cultural_fit"
  >;
  label: string;
  emphasis?: boolean;
}> = [
  { key: "overall_score", label: "Overall", emphasis: true },
  { key: "skill_match", label: "Skill match" },
  { key: "communication", label: "Communication" },
  { key: "problem_solving", label: "Problem solving" },
  { key: "cultural_fit", label: "Cultural fit" },
];

interface Props {
  jobId: string;
  candidates: Candidate[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onShortlist: (candidateId: string) => void | Promise<void>;
  onReject: (candidateId: string) => void | Promise<void>;
  pendingId: string | null;
}

/**
 * Side-by-side comparison drawer for 2–4 candidates.
 *
 * The selection-limit invariant is enforced by the parent (the table
 * disables checkboxes once the cap is reached); this component only
 * renders whatever it is given.
 */
export function ComparisonDrawer({
  jobId,
  candidates,
  open,
  onOpenChange,
  onShortlist,
  onReject,
  pendingId,
}: Props) {
  const winner = pickWinner(candidates);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="full" className="sm:max-w-[1100px]">
        <DialogHeader>
          <DialogTitle>Compare candidates</DialogTitle>
          <DialogDescription>
            Side-by-side view of {candidates.length} candidate
            {candidates.length === 1 ? "" : "s"}. Highest score in each row is
            highlighted.
          </DialogDescription>
        </DialogHeader>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="py-2 pr-3 text-left font-medium text-muted-foreground">
                  Metric
                </th>
                {candidates.map((c) => (
                  <th
                    key={c.id}
                    className="py-2 px-3 text-left align-top min-w-[180px]"
                  >
                    <div className="space-y-1">
                      <Link
                        href={`/dashboard/jobs/${jobId}/candidates/${c.id}`}
                        className="font-semibold hover:underline inline-flex items-center gap-1"
                      >
                        {c.name}
                        <ExternalLink className="h-3 w-3" />
                      </Link>
                      <p className="text-xs text-muted-foreground truncate">
                        {c.email}
                      </p>
                      {winner && winner.id === c.id && (
                        <Badge variant="secondary" className="text-[10px]">
                          Top overall
                        </Badge>
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {SCORE_ROWS.map((row) => {
                const top = topValueFor(candidates, row.key);
                return (
                  <tr key={row.key} className="border-b last:border-0">
                    <td className="py-2 pr-3 font-medium text-muted-foreground">
                      {row.label}
                    </td>
                    {candidates.map((c) => {
                      const v = c[row.key];
                      const isTop =
                        v != null && top != null && v === top && candidates.length > 1;
                      return (
                        <td
                          key={c.id}
                          className={`py-2 px-3 ${row.emphasis ? "font-semibold" : ""} ${
                            isTop ? "text-green-700 dark:text-green-400" : ""
                          }`}
                        >
                          {formatScore(v)}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}

              <tr className="border-b">
                <td className="py-2 pr-3 font-medium text-muted-foreground">
                  Recommendation
                </td>
                {candidates.map((c) => (
                  <td key={c.id} className="py-2 px-3">
                    {c.recommendation ? (
                      <Badge
                        variant="secondary"
                        className={RECOMMENDATION_STYLES[c.recommendation] ?? ""}
                      >
                        {c.recommendation.replace("_", " ")}
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </td>
                ))}
              </tr>

              <tr className="border-b">
                <td className="py-2 pr-3 font-medium text-muted-foreground">
                  Status
                </td>
                {candidates.map((c) => (
                  <td key={c.id} className="py-2 px-3 capitalize">
                    {c.status.replace("_", " ")}
                  </td>
                ))}
              </tr>

              <tr>
                <td className="py-3 pr-3 font-medium text-muted-foreground align-top">
                  Action
                </td>
                {candidates.map((c) => (
                  <td key={c.id} className="py-3 px-3 align-top">
                    <div className="flex flex-col gap-2">
                      <Button
                        size="sm"
                        onClick={() => onShortlist(c.id)}
                        disabled={
                          pendingId === c.id || c.status === "shortlisted"
                        }
                      >
                        <ThumbsUp className="mr-2 h-3.5 w-3.5" />
                        Shortlist
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onReject(c.id)}
                        disabled={pendingId === c.id || c.status === "rejected"}
                      >
                        <ThumbsDown className="mr-2 h-3.5 w-3.5" />
                        Reject
                      </Button>
                    </div>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function formatScore(v: number | null): string {
  return v != null ? Number(v).toFixed(1) : "—";
}

function topValueFor(
  list: Candidate[],
  key: keyof Pick<
    Candidate,
    "overall_score" | "skill_match" | "communication" | "problem_solving" | "cultural_fit"
  >,
): number | null {
  const values = list
    .map((c) => c[key])
    .filter((v): v is number => v != null);
  return values.length ? Math.max(...values) : null;
}

function pickWinner(list: Candidate[]): Candidate | null {
  let winner: Candidate | null = null;
  for (const c of list) {
    if (c.overall_score == null) continue;
    if (!winner || (winner.overall_score ?? -Infinity) < c.overall_score) {
      winner = c;
    }
  }
  return winner;
}
