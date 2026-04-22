"use client";

import { useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import {
  Briefcase,
  Building2,
  Loader2,
  Send,
  AlertTriangle,
  CheckCircle2,
  Play,
  MessageSquare,
} from "lucide-react";

import { interview as interviewApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface SessionInfo {
  job_title: string;
  company_name: string;
  candidate_name: string;
  total_questions: number;
  status: string;
}

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
  const [isInterviewDone, setIsInterviewDone] = useState(false);
  const [progress, setProgress] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [redirectCountdown, setRedirectCountdown] = useState<number | null>(
    null,
  );

  // Integrity tracking refs (not rendered, so refs are fine)
  const wasPastedRef = useRef(false);
  const tabSwitchCountRef = useRef(0);
  const lastAiTimestampRef = useRef<number>(Date.now());

  const messagesEndRef = useRef<HTMLDivElement>(null);

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
      .then((data) => {
        setSessionInfo(data);
        if (data.status === "in_progress") {
          setPhase("interview");
        } else if (data.status === "completed") {
          setPhase("completed");
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setIsLoading(false));
  }, [token]);

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // Countdown timer for redirect after completion
  useEffect(() => {
    if (redirectCountdown === null) return;
    if (redirectCountdown <= 0) {
      setPhase("completed");
      return;
    }
    const timer = setTimeout(
      () => setRedirectCountdown(redirectCountdown - 1),
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
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <Card className="w-full max-w-lg">
          <CardHeader className="text-center">
            <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground">
              <Briefcase className="h-6 w-6" />
            </div>
            <CardTitle className="text-xl">
              Welcome, {sessionInfo.candidate_name}!
            </CardTitle>
            <CardDescription className="flex items-center justify-center gap-1">
              <Building2 className="h-3.5 w-3.5" />
              {sessionInfo.job_title} · {sessionInfo.company_name}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="rounded-lg border bg-muted/50 p-4 space-y-3">
              <h3 className="text-sm font-semibold">Interview Details</h3>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>
                  • {sessionInfo.total_questions} tailored questions based on
                  your resume
                </li>
                <li>• AI-powered conversational interview</li>
                <li>• Estimated duration: 15–25 minutes</li>
              </ul>
            </div>

            <div className="rounded-lg border bg-blue-50 dark:bg-blue-950/30 p-4 space-y-2">
              <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-300">
                Tips for best results
              </h3>
              <ul className="text-sm text-blue-600 dark:text-blue-400 space-y-1">
                <li>• Be specific — use real examples from your experience</li>
                <li>• Take your time — there&apos;s no time limit per question</li>
                <li>• The AI may ask follow-ups if it needs more detail</li>
              </ul>
            </div>

            <Button
              className="w-full"
              size="lg"
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
      </div>
    );
  }

  // ── Completed ──
  if (phase === "completed") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md">
          <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
              <CheckCircle2 className="h-8 w-8 text-green-600 dark:text-green-400" />
            </div>
            <h2 className="text-xl font-semibold">Interview Complete!</h2>
            <p className="text-sm text-muted-foreground">
              Thank you for completing your interview for{" "}
              <strong>{sessionInfo.job_title}</strong> at{" "}
              <strong>{sessionInfo.company_name}</strong>. The hiring team will
              review your responses and get back to you.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ── Chat ──
  const { current: qCurrent, total: qTotal } = parseProgress(progress);

  return (
    <div className="flex h-screen flex-col bg-background overflow-hidden">
      {/* Sticky Header */}
      <header className="shrink-0 border-b bg-card px-4 py-3 z-10">
        <div className="mx-auto flex max-w-2xl items-center gap-3">
          <Briefcase className="h-5 w-5 text-primary" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{sessionInfo.job_title}</p>
            <p className="text-xs text-muted-foreground truncate">
              {sessionInfo.company_name} · AI Interview
            </p>
          </div>
          {progress && !isInterviewDone && (
            <div className="flex items-center gap-2 shrink-0">
              <MessageSquare className="h-3.5 w-3.5 text-muted-foreground hidden sm:block" />
              <span className="text-xs font-medium text-muted-foreground whitespace-nowrap">
                Question {qCurrent} of {qTotal}
              </span>
              <div className="h-1.5 w-16 rounded-full bg-muted overflow-hidden">
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
      <div className="flex-1 overflow-y-auto px-4 py-6 min-h-0">
        <div className="mx-auto max-w-2xl space-y-4">
          {messages.map((msg, i) => (
            <div key={i}>
              {/* Last question badge */}
              {msg.role === "ai" && msg.isLastQuestion && (
                <div className="flex justify-start mb-1">
                  <Badge
                    variant="outline"
                    className="text-xs border-amber-300 text-amber-600 dark:text-amber-400"
                  >
                    Final Question
                  </Badge>
                </div>
              )}
              <div
                className={`flex ${msg.role === "candidate" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    msg.role === "candidate"
                      ? "bg-primary text-primary-foreground"
                      : msg.isClosing
                        ? "bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800"
                        : "bg-muted"
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            </div>
          ))}

          {/* Typing indicator */}
          {(isSending || isTyping) && (
            <div className="flex justify-start">
              <div className="rounded-2xl bg-muted px-4 py-3 flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:0ms]" />
                <span className="h-2 w-2 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:150ms]" />
                <span className="h-2 w-2 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:300ms]" />
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

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input — pinned to bottom */}
      <div className="shrink-0 border-t bg-card px-4 py-3 z-10">
        <div className="mx-auto max-w-2xl">
          {isInterviewDone ? (
            <div className="flex items-center justify-center py-2">
              <p className="text-sm text-muted-foreground">
                Interview completed — thank you for your time!
              </p>
            </div>
          ) : (
            <div className="flex items-end gap-2 rounded-xl border bg-background p-2 shadow-sm focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary/50 transition-all">
              <Textarea
                placeholder="Type your response…"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                onPaste={() => { wasPastedRef.current = true; }}
                rows={1}
                className="resize-none border-0 shadow-none focus-visible:ring-0 p-1 min-h-9 max-h-30"
                disabled={isSending || isTyping}
              />
              <Button
                size="icon"
                onClick={handleSend}
                disabled={isSending || isTyping || !inputMessage.trim()}
                className="shrink-0 h-9 w-9 rounded-lg"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
