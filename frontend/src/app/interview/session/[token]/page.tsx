"use client";

import { useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import {
  Briefcase,
  Building2,
  Loader2,
  ArrowUp,
  AlertTriangle,
  CheckCircle2,
  Play,
  Sparkles,
  Clock,
  MessageCircle,
  ShieldCheck,
} from "lucide-react";

import type { SessionLandingResponse } from "@/lib/types";
import { interview as interviewApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

type SessionInfo = SessionLandingResponse;

interface Message {
  role: "ai" | "candidate";
  content: string;
  isLastQuestion?: boolean;
  isClosing?: boolean;
}

export default function InterviewSessionPage() {
  const { token } = useParams<{ token: string }>();
  const [sessionInfo, setSessionInfo] = useState<SessionInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Interview state
  const [phase, setPhase] = useState<"landing" | "interview" | "completed">(
    "landing",
  );
  const [interviewToken, setInterviewToken] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [isResuming, setIsResuming] = useState(false);
  const [isInterviewDone, setIsInterviewDone] = useState(false);
  const [progress, setProgress] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [redirectCountdown, setRedirectCountdown] = useState<number | null>(
    null,
  );

  // Integrity tracking refs (not rendered, so refs are fine)
  const wasPastedRef = useRef(false);
  const tabSwitchCountRef = useRef(0);
  const lastAiTimestampRef = useRef<number>(0);

  const messagesScrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-grow the textarea up to a max height (ChatGPT-style).
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    const next = Math.min(ta.scrollHeight, 200); // ~8 lines max
    ta.style.height = `${next}px`;
  }, [inputMessage]);

  // Track tab/window visibility changes
  useEffect(() => {
    const handler = () => {
      if (document.hidden && phase === "interview" && !isInterviewDone) {
        tabSwitchCountRef.current += 1;
      }
    };
    document.addEventListener("visibilitychange", handler);
    return () => document.removeEventListener("visibilitychange", handler);
  }, [phase, isInterviewDone]);

  // Load session info (instant — questions are pre-generated)
  useEffect(() => {
    interviewApi
      .sessionLanding(token)
      .then(async (data) => {
        setSessionInfo(data);
        if (data.status === "completed") {
          setPhase("completed");
          setIsLoading(false);
          return;
        }
        if (data.status === "in_progress") {
          // Auto-resume: call sessionStart which returns interview_token + last AI message.
          // The backend allows begin_session for in_progress candidates and returns
          // the last AI message from the stored transcript.
          setIsResuming(true);
          setIsLoading(false);
          try {
            const resumed = await interviewApi.sessionStart(token);
            setInterviewToken(resumed.interview_token);
            lastAiTimestampRef.current = Date.now();
            // Restore progress from the landing data (current_question_index is 0-based)
            const resumedQ = data.current_question_index + 1;
            setProgress(`${resumedQ}/${data.total_questions}`);
            setMessages([
              {
                role: "ai",
                content: resumed.first_message,
              },
            ]);
            setPhase("interview");
          } catch {
            setError("Failed to resume your interview. Please try refreshing.");
          } finally {
            setIsResuming(false);
          }
          return;
        }
        setIsLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setIsLoading(false);
      });
  }, [token]);

  // Auto-scroll messages
  useEffect(() => {
    const pane = messagesScrollRef.current;
    pane?.scrollTo({ top: pane.scrollHeight, behavior: "smooth" });
  }, [messages, isTyping]);

  // Countdown timer for redirect after completion
  useEffect(() => {
    if (redirectCountdown === null) return;
    const timer = setTimeout(
      () => {
        if (redirectCountdown <= 1) setPhase("completed");
        else setRedirectCountdown(redirectCountdown - 1);
      },
      1000,
    );
    return () => clearTimeout(timer);
  }, [redirectCountdown]);

  const handleStart = async () => {
    setIsStarting(true);
    try {
      const response = await interviewApi.sessionStart(token);
      setInterviewToken(response.interview_token);
      setProgress(`1/${response.total_questions}`);

      // Show welcome message immediately
      const welcomeMsg: Message = {
        role: "ai",
        content: `Hi ${sessionInfo!.candidate_name}! I'm your AI interviewer for the ${sessionInfo!.job_title} position at ${sessionInfo!.company_name}. I'll be asking you ${response.total_questions} questions today. Take your time with each answer — there's no rush. Let's get started!`,
      };
      setMessages([welcomeMsg]);
      setPhase("interview");

      // Show typing indicator, then reveal first question after a delay
      setIsTyping(true);
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          { role: "ai", content: response.first_message },
        ]);
        setIsTyping(false);
        lastAiTimestampRef.current = Date.now();
      }, 1800);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to start interview",
      );
    } finally {
      setIsStarting(false);
    }
  };

  const handleSend = async () => {
    if (!inputMessage.trim() || !interviewToken || isInterviewDone) return;

    const userMsg = inputMessage.trim();
    const timeToAnswer = (Date.now() - lastAiTimestampRef.current) / 1000;
    const signals = {
      was_pasted: wasPastedRef.current,
      tab_switch_count: tabSwitchCountRef.current,
      time_to_answer_seconds: Math.round(timeToAnswer),
    };

    // Reset per-message trackers
    wasPastedRef.current = false;
    tabSwitchCountRef.current = 0;

    setInputMessage("");
    setMessages((prev) => [...prev, { role: "candidate", content: userMsg }]);
    setIsSending(true);

    try {
      const response = await interviewApi.sendMessage({
        interview_token: interviewToken,
        message: userMsg,
        integrity_signals: signals,
      });

      setProgress(response.progress);
      lastAiTimestampRef.current = Date.now();

      const aiMsg: Message = {
        role: "ai",
        content: response.ai_response,
        isLastQuestion: response.is_last_question,
        isClosing: response.is_complete,
      };
      setMessages((prev) => [...prev, aiMsg]);

      if (response.is_complete) {
        setIsInterviewDone(true);
        setRedirectCountdown(5);
      }
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to send message",
      );
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Parse progress string "3/8" into numbers
  const parseProgress = (p: string) => {
    const [current, total] = p.split("/").map(Number);
    return { current: current || 0, total: total || 0 };
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (isResuming) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Resuming your interview…</p>
      </div>
    );
  }

  if (error || !sessionInfo) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md">
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <AlertTriangle className="h-12 w-12 text-destructive" />
            <h2 className="text-lg font-semibold">Session Not Found</h2>
            <p className="text-sm text-muted-foreground text-center">
              {error ??
                "This interview session link is invalid or has expired."}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ── Landing (Ready to start) ──
  if (phase === "landing") {
    const initials = sessionInfo.candidate_name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((w) => w[0]?.toUpperCase() ?? "")
      .join("");

    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <div className="w-full max-w-xl">
          {/* Identity */}
          <div className="flex flex-col items-center text-center mb-8">
            <div className="relative mb-5">
              <div className="absolute inset-0 rounded-full bg-primary/20 blur-xl" />
              <div className="relative flex h-20 w-20 items-center justify-center rounded-full bg-linear-to-br from-primary to-primary/70 text-primary-foreground text-2xl font-semibold shadow-lg ring-4 ring-background">
                {initials || <Briefcase className="h-8 w-8" />}
              </div>
            </div>
            <h1 className="text-3xl font-bold tracking-tight">
              Welcome, {sessionInfo.candidate_name.split(/\s+/)[0]}
            </h1>
            <p className="mt-2 flex items-center gap-1.5 text-sm text-muted-foreground">
              <Building2 className="h-3.5 w-3.5" />
              <span className="font-medium text-foreground">{sessionInfo.job_title}</span>
              <span className="text-muted-foreground/60">·</span>
              <span>{sessionInfo.company_name}</span>
            </p>
          </div>

          {/* Details card */}
          <Card className="border-border/60 shadow-sm">
            <CardContent className="p-6 space-y-5">
              <div className="grid grid-cols-3 gap-4">
                <DetailStat
                  icon={<MessageCircle className="h-4 w-4" />}
                  value={String(sessionInfo.total_questions)}
                  label="Questions"
                />
                <DetailStat
                  icon={<Clock className="h-4 w-4" />}
                  value="15–25"
                  label="Minutes"
                />
                <DetailStat
                  icon={<Sparkles className="h-4 w-4" />}
                  value="AI"
                  label="Conversational"
                />
              </div>

              <div className="border-t pt-5 space-y-3">
                <h3 className="text-sm font-semibold flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-primary" />
                  Before you begin
                </h3>
                <ul className="text-sm text-muted-foreground space-y-2 pl-6 list-disc marker:text-muted-foreground/40">
                  <li>Be specific — use concrete examples from your experience.</li>
                  <li>Take your time. There&apos;s no time limit on any question.</li>
                  <li>The interviewer may ask follow-ups if it needs more detail.</li>
                </ul>
              </div>

              <Button
                className="w-full h-11 text-base font-medium"
                onClick={handleStart}
                disabled={isStarting}
              >
                {isStarting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Starting…
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Start Interview
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          <p className="mt-6 text-center text-xs text-muted-foreground">
            Your responses are confidential and reviewed only by the {sessionInfo.company_name} hiring team.
          </p>
        </div>
      </div>
    );
  }

  // ── Completed ──
  if (phase === "completed") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <div className="w-full max-w-lg text-center">
          <div className="relative mx-auto mb-6 flex h-20 w-20 items-center justify-center">
            <div className="absolute inset-0 rounded-full bg-green-500/20 blur-xl" />
            <div className="relative flex h-20 w-20 items-center justify-center rounded-full bg-linear-to-br from-green-500 to-emerald-600 shadow-lg ring-4 ring-background">
              <CheckCircle2 className="h-10 w-10 text-white" />
            </div>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">Interview complete</h1>
          <p className="mt-3 text-base text-muted-foreground">
            Thank you for completing your interview for{" "}
            <span className="font-medium text-foreground">{sessionInfo.job_title}</span>{" "}
            at{" "}
            <span className="font-medium text-foreground">{sessionInfo.company_name}</span>.
          </p>

          <Card className="mt-8 text-left border-border/60">
            <CardContent className="p-6 space-y-4">
              <h3 className="text-sm font-semibold">What happens next</h3>
              <ol className="space-y-3">
                {[
                  "Your responses are reviewed and scored.",
                  "The hiring team evaluates the results.",
                  `${sessionInfo.company_name} will be in touch via email.`,
                ].map((step, i) => (
                  <li key={i} className="flex gap-3 text-sm">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                      {i + 1}
                    </span>
                    <span className="text-muted-foreground pt-0.5">{step}</span>
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>

          <p className="mt-6 text-xs text-muted-foreground">
            You can safely close this window.
          </p>
        </div>
      </div>
    );
  }

  // ── Chat ──
  const { current: qCurrent, total: qTotal } = parseProgress(progress);

  return (
    <div className="flex h-[calc(100dvh-var(--portfolio-demo-height,0px))] min-h-96 flex-col bg-background overflow-hidden">
      {/* Sticky Header */}
      <header className="shrink-0 border-b bg-background/80 backdrop-blur-md px-4 py-3 z-10">
        <div className="mx-auto flex max-w-3xl items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Briefcase className="h-4 w-4" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold truncate leading-tight">{sessionInfo.job_title}</p>
            <p className="text-xs text-muted-foreground truncate">
              {sessionInfo.company_name}
            </p>
          </div>
          {progress && !isInterviewDone && (
            <div className="flex items-center gap-2.5 shrink-0">
              <span className="text-xs font-medium text-muted-foreground whitespace-nowrap tabular-nums">
                {qCurrent} / {qTotal}
              </span>
              <div className="h-1.5 w-20 rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full rounded-full bg-primary transition-all duration-500"
                  style={{
                    width: `${qTotal > 0 ? (qCurrent / qTotal) * 100 : 0}%`,
                  }}
                />
              </div>
            </div>
          )}
          {isInterviewDone && (
            <Badge
              variant="secondary"
              className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 shrink-0"
            >
              <CheckCircle2 className="mr-1 h-3 w-3" />
              Complete
            </Badge>
          )}
        </div>
      </header>

      {/* Messages — only this area scrolls */}
      <div ref={messagesScrollRef} role="region" aria-label="Interview messages" tabIndex={0} className="flex-1 overflow-y-auto px-4 py-8 min-h-0">
        <div className="mx-auto max-w-3xl space-y-6">
          {/* Resumed banner — only shown when session was auto-resumed on refresh */}
          {sessionInfo?.status === "in_progress" && messages.length > 0 && !isInterviewDone && (
            <div className="flex justify-center">
              <span className="rounded-full border border-border/50 bg-muted/40 px-4 py-1.5 text-xs text-muted-foreground">
                Interview resumed — continuing from where you left off
              </span>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i}>
              {/* Last question badge */}
              {msg.role === "ai" && msg.isLastQuestion && (
                <div className="flex justify-start mb-2 pl-11">
                  <Badge
                    variant="outline"
                    className="text-xs border-amber-300 text-amber-600 dark:text-amber-400"
                  >
                    Final Question
                  </Badge>
                </div>
              )}
              {msg.role === "ai" ? (
                // AI: no bubble, plain text with avatar (ChatGPT-style).
                <div className="flex gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-linear-to-br from-primary to-primary/70 text-primary-foreground shadow-sm">
                    <Sparkles className="h-4 w-4" />
                  </div>
                  <div
                    className={`flex-1 pt-0.5 text-[15px] leading-relaxed whitespace-pre-wrap ${
                      msg.isClosing ? "text-foreground" : "text-foreground"
                    }`}
                  >
                    {msg.content}
                    {msg.isClosing && (
                      <div className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-green-500/10 px-3 py-1 text-xs font-medium text-green-700 dark:text-green-400">
                        <CheckCircle2 className="h-3 w-3" />
                        Interview complete
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                // Candidate: rounded pill bubble on the right.
                <div className="flex justify-end">
                  <div className="max-w-[85%] rounded-3xl bg-muted px-5 py-2.5 text-[15px] leading-relaxed whitespace-pre-wrap">
                    {msg.content}
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* Typing indicator (AI thinking) */}
          {(isSending || isTyping) && (
            <div className="flex gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-linear-to-br from-primary to-primary/70 text-primary-foreground shadow-sm">
                <Sparkles className="h-4 w-4" />
              </div>
              <div className="flex items-center gap-1 pt-3">
                <span className="h-2 w-2 rounded-full bg-muted-foreground/50 animate-bounce [animation-delay:0ms]" />
                <span className="h-2 w-2 rounded-full bg-muted-foreground/50 animate-bounce [animation-delay:150ms]" />
                <span className="h-2 w-2 rounded-full bg-muted-foreground/50 animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          )}

          {/* Redirect countdown notice */}
          {isInterviewDone && redirectCountdown !== null && (
            <div className="flex justify-center">
              <p className="text-xs text-muted-foreground animate-pulse">
                Redirecting to summary in {redirectCountdown}s…
              </p>
            </div>
          )}

        </div>
      </div>

      {/* Input — pinned to bottom (ChatGPT-style auto-grow) */}
      <div className="shrink-0 px-4 pb-4 pt-2 z-10">
        <div className="mx-auto max-w-3xl">
          {isInterviewDone ? (
            <div className="flex items-center justify-center py-2">
              <p className="text-sm text-muted-foreground">
                Interview completed — thank you for your time!
              </p>
            </div>
          ) : (
            <>
              <div className="flex items-end gap-2 rounded-3xl border border-border/80 bg-muted/40 px-4 py-3 shadow-sm focus-within:border-border focus-within:bg-muted/60 transition-colors">
                <textarea
                  ref={textareaRef}
                  placeholder="Type your response…"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  onPaste={() => { wasPastedRef.current = true; }}
                  rows={1}
                  className="min-w-0 flex-1 resize-none bg-transparent text-[15px] leading-6 placeholder:text-muted-foreground focus:outline-none disabled:opacity-50"
                  style={{ minHeight: 24, maxHeight: 200 }}
                  disabled={isSending || isTyping}
                />
                <Button
                  size="icon"
                  onClick={handleSend}
                  aria-label="Send response"
                  disabled={isSending || isTyping || !inputMessage.trim()}
                  className="shrink-0 h-8 w-8 rounded-full"
                >
                  <ArrowUp className="h-4 w-4" />
                </Button>
              </div>
              <p className="mt-2 text-center text-[11px] text-muted-foreground">
                Press Enter to send, Shift + Enter for new line
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function DetailStat({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode;
  value: string;
  label: string;
}) {
  return (
    <div className="flex flex-col items-center text-center gap-1.5 rounded-lg bg-muted/40 px-2 py-3">
      <div className="text-primary">{icon}</div>
      <div className="text-lg font-semibold leading-none">{value}</div>
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
    </div>
  );
}
