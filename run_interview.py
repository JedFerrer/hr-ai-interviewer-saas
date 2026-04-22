"""CLI entry point: Run a full screening interview.

Usage:
    python run_interview.py --resume data/resumes/candidate.pdf --jd data/job_descriptions/role.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.question_generator import generate_questions
from src.resume_parser import extract_text_from_resume, parse_resume
from src.interview_engine import InterviewEngine
from src.utils import get_cost_summary, get_openai_client


def main() -> None:
    parser = argparse.ArgumentParser(description="AI HR Interviewer — Screening Interview")
    parser.add_argument("--resume", required=True, help="Path to candidate resume (PDF or DOCX)")
    parser.add_argument("--jd", required=True, help="Path to job description text file")
    parser.add_argument("--output", default="output/transcripts", help="Output directory for transcripts")
    parser.add_argument("--questions", type=int, default=7, help="Number of questions to generate (default: 7)")
    args = parser.parse_args()

    # Validate inputs
    resume_path = Path(args.resume)
    jd_path = Path(args.jd)
    if not resume_path.exists():
        print(f"Error: Resume not found: {resume_path}")
        sys.exit(1)
    if not jd_path.exists():
        print(f"Error: Job description not found: {jd_path}")
        sys.exit(1)

    # Initialize
    client = get_openai_client()

    # Step 1: Parse resume
    print("[1/3] Parsing resume...")
    resume_text = extract_text_from_resume(resume_path)
    resume_data = parse_resume(client, resume_text)
    print(f"  Candidate: {resume_data.name}")
    print(f"  Skills: {', '.join(resume_data.skills[:8])}{'...' if len(resume_data.skills) > 8 else ''}")

    # Step 2: Generate questions
    print(f"[2/3] Generating {args.questions} interview questions...")
    jd_text = jd_path.read_text(encoding="utf-8")
    questions = generate_questions(client, resume_data, jd_text, num_questions=args.questions)
    for i, q in enumerate(questions):
        print(f"  Q{i + 1} [{q.category.value}]: {q.question[:80]}...")

    # Extract job title from first line of JD or filename
    job_title = jd_text.strip().split("\n")[0].strip().rstrip(":")
    if len(job_title) > 100:
        job_title = jd_path.stem.replace("_", " ").title()

    # Step 3: Run interview
    print("[3/3] Starting interview...\n")
    engine = InterviewEngine(
        client=client,
        resume_data=resume_data,
        questions=questions,
        job_title=job_title,
        jd_summary=jd_text[:500],
    )
    engine.run()

    # Save transcript
    output_dir = Path(args.output)
    safe_name = resume_data.name.replace(" ", "_").lower() or "candidate"
    transcript_path = engine.save_transcript(output_dir / f"{safe_name}_transcript.json")
    print(f"Transcript saved: {transcript_path}")

    # Print cost summary
    cost = get_cost_summary()
    print(f"\nAPI Cost Summary:")
    print(f"  Total calls: {cost['calls']}")
    print(f"  Total tokens: {cost['total_tokens']:,}")
    print(f"  Estimated cost: ${cost['total_cost_usd']:.4f}")


if __name__ == "__main__":
    main()
