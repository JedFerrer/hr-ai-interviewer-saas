"""Interview engine: Manages the conversational interview loop via CLI."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

from src.prompts import FOLLOW_UP_DECISION_PROMPT, INTERVIEW_SYSTEM_PROMPT
from src.schemas import (
    AnswerQuality,
    FollowUpDecision,
    InterviewQuestion,
    ResumeData,
    TranscriptMessage,
)
from src.utils import chat_completion, chat_completion_json


class InterviewEngine:
    """Runs a multi-turn screening interview in the terminal.

    Manages conversation history, follow-up decisions (via LLM),
    and transcript recording.
    """

    MAX_FOLLOW_UPS_PER_QUESTION = 2
    CONTEXT_WINDOW_MESSAGES = 10  # Sliding window for LLM context

    def __init__(
        self,
        client: OpenAI,
        resume_data: ResumeData,
        questions: list[InterviewQuestion],
        job_title: str,
        jd_summary: str,
    ) -> None:
        self.client = client
        self.resume_data = resume_data
        self.questions = questions
        self.job_title = job_title
        self.jd_summary = jd_summary

        self.transcript: list[TranscriptMessage] = []
        self._conversation_history: list[dict[str, str]] = []

        # Build system prompt
        questions_text = "\n".join(
            f"{i + 1}. [{q.category.value}] {q.question}" for i, q in enumerate(questions)
        )
        self._system_prompt = INTERVIEW_SYSTEM_PROMPT.format(
            job_title=job_title,
            resume_summary=resume_data.summary,
            jd_summary=jd_summary,
            questions=questions_text,
        )

    def run(self) -> list[TranscriptMessage]:
        """Execute the full interview loop and return the transcript."""
        print(f"\n{'='*60}")
        print(f"  SCREENING INTERVIEW — {self.job_title}")
        print(f"{'='*60}")
        print(f"  Candidate: {self.resume_data.name}")
        print(f"  Questions: {len(self.questions)}")
        print(f"{'='*60}\n")

        # Opening greeting
        greeting = self._get_interviewer_response(
            "Begin the interview with a brief greeting and ask the first question."
        )
        self._record("interviewer", greeting)
        print(f"Interviewer: {greeting}\n")

        for i, question in enumerate(self.questions):
            follow_up_count = 0

            while True:
                # Get candidate input
                answer = input("You: ").strip()
                if not answer:
                    print("  (Please type your answer)")
                    continue
                if answer.lower() in ("quit", "exit", "q"):
                    print("\n[Interview ended early by candidate]\n")
                    self._record("candidate", "[ended interview early]")
                    return self.transcript

                self._record("candidate", answer)

                # Decide: follow-up or next question
                decision = self._evaluate_answer(question, answer)

                if (
                    decision.quality != AnswerQuality.DETAILED
                    and follow_up_count < self.MAX_FOLLOW_UPS_PER_QUESTION
                ):
                    # Ask follow-up
                    follow_up_response = self._get_interviewer_response(
                        f"The candidate's answer was {decision.quality.value}. "
                        f"Ask this follow-up: {decision.follow_up}"
                    )
                    self._record("interviewer", follow_up_response)
                    print(f"\nInterviewer: {follow_up_response}\n")
                    follow_up_count += 1
                else:
                    # Move to next question
                    if i < len(self.questions) - 1:
                        transition = self._get_interviewer_response(
                            f"Briefly acknowledge the answer and ask question #{i + 2}: "
                            f"{self.questions[i + 1].question}"
                        )
                    else:
                        transition = self._get_interviewer_response(
                            "This was the last question. Thank the candidate and wrap up the interview."
                        )
                    self._record("interviewer", transition)
                    print(f"\nInterviewer: {transition}\n")
                    break

        print(f"\n{'='*60}")
        print("  Interview complete. Transcript saved.")
        print(f"{'='*60}\n")
        return self.transcript

    def _evaluate_answer(
        self, question: InterviewQuestion, answer: str
    ) -> FollowUpDecision:
        """Use LLM to decide if the answer needs a follow-up."""
        prompt = FOLLOW_UP_DECISION_PROMPT.format(
            question=question.question,
            answer=answer,
            word_count=len(answer.split()),
            resume_summary=self.resume_data.summary,
        )
        data = chat_completion_json(
            self.client,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            operation="follow_up_decision",
        )
        return FollowUpDecision.model_validate(data)

    def _get_interviewer_response(self, instruction: str) -> str:
        """Get the interviewer's next statement from the LLM."""
        # Build messages with sliding window
        messages: list[dict[str, str]] = [{"role": "system", "content": self._system_prompt}]

        # Add recent conversation history (sliding window)
        recent = self._conversation_history[-self.CONTEXT_WINDOW_MESSAGES :]
        messages.extend(recent)

        # Add the instruction as the latest user message
        messages.append({"role": "user", "content": instruction})

        response = chat_completion(
            self.client,
            messages=messages,
            temperature=0.5,
            operation="interviewer_response",
        )

        # Track in conversation history
        self._conversation_history.append({"role": "assistant", "content": response})
        return response

    def _record(self, role: str, content: str) -> None:
        """Add a message to the transcript and conversation history."""
        msg = TranscriptMessage(
            role=role,
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.transcript.append(msg)

        # Map to OpenAI roles for context
        openai_role = "assistant" if role == "interviewer" else "user"
        self._conversation_history.append({"role": openai_role, "content": content})

    def save_transcript(self, output_path: str | Path) -> Path:
        """Save the transcript to a JSON file. Returns the file path."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "job_title": self.job_title,
            "candidate_name": self.resume_data.name,
            "date": datetime.now(timezone.utc).isoformat(),
            "questions_count": len(self.questions),
            "transcript": [m.model_dump() for m in self.transcript],
            "resume_summary": self.resume_data.summary,
            "jd_summary": self.jd_summary,
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path
