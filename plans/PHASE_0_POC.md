# Phase 0: Proof of Concept — Weeks 1–3

> **Status:** `DONE`
> **Depends on:** Nothing — start here
> **Unlocks:** [Phase 1A Backend](./PHASE_1A_BACKEND.md)
> **Tracker:** [MVP_TRACKER.md](./MVP_TRACKER.md)

---

## Goal

Validate that an LLM can conduct a screening interview from a resume + job description and produce evaluation output that an HR person finds useful. **No UI. No database. No framework. Just Python scripts.**

## Exit Criteria

- [ ] Generated questions are relevant to the resume + JD
- [ ] Follow-up questions adapt based on answer quality
- [ ] Evaluation scores align with human judgment (±1 point)
- [ ] AI summary is useful to an HR person (feedback from 2+ people)
- [ ] Cost per interview is under $0.20
- [ ] Full interview takes <50K tokens

**If these pass → proceed to Phase 1A. If not → iterate on prompts before building anything else.**

---

## Tech Stack (POC only)

| Component | Tool | Install Command | Cost |
|-----------|------|----------------|------|
| Language | Python 3.12 | Already installed | $0 |
| LLM | OpenAI GPT-4.1-mini | `pip install openai` | ~$0.10–0.15/interview |
| Resume parsing | pdfplumber + python-docx | `pip install pdfplumber python-docx` | $0 |
| Env vars | python-dotenv | `pip install python-dotenv` | $0 |
| Output | JSON to console | Built-in | $0 |

```bash
# Setup (Day 1, 5 minutes)
mkdir hr-ai-interviewer && cd hr-ai-interviewer
python -m venv venv
venv\Scripts\activate          # Windows
pip install openai pdfplumber python-docx python-dotenv
```

Create `.env`:
```
OPENAI_API_KEY=sk-your-key-here
```

Create `.gitignore`:
```
venv/
.env
__pycache__/
*.pyc
```

---

## Project Structure (POC)

```
hr-ai-interviewer/
├── .env
├── .gitignore
├── data/
│   ├── sample_resumes/          # 5 test PDFs/DOCXs
│   │   ├── software_engineer.pdf
│   │   ├── marketing_manager.docx
│   │   ├── sales_rep.pdf
│   │   ├── data_analyst.docx
│   │   └── hr_coordinator.pdf
│   └── job_descriptions/        # Matching JDs as .txt
│       ├── software_engineer.txt
│       ├── marketing_manager.txt
│       ├── sales_rep.txt
│       ├── data_analyst.txt
│       └── hr_coordinator.txt
├── src/
│   ├── __init__.py
│   ├── resume_parser.py         # Week 1: PDF/DOCX → structured data
│   ├── question_generator.py    # Week 1: Resume + JD → questions
│   ├── interview_engine.py      # Week 2: Conversational loop
│   ├── evaluator.py             # Week 3: Transcript → scores
│   ├── prompts.py               # All LLM prompts centralized
│   └── utils.py                 # Token counting, cost tracking
├── run_interview.py             # Main CLI entry point
└── run_evaluation.py            # Evaluate a saved transcript
```

---

## Week 1: Resume Parsing + Question Generation

**Status:** `NOT_STARTED`

### Task 1.1: Resume Parser
- [ ] Create `src/resume_parser.py`
- [ ] Extract text from PDF/DOCX using pdfplumber + python-docx
- [ ] Send raw text to GPT-4.1-mini to extract structured data
- [ ] Return structured dict: name, email, experience[], skills[], education[], summary

**File: `src/resume_parser.py`**

```python
# Key function signatures to implement:

def extract_text_from_resume(file_path: str) -> str:
    """Extract raw text from PDF/DOCX."""
    pass

def parse_resume(file_path: str) -> dict:
    """Parse PDF/DOCX resume into structured data using LLM."""
    # 1. Extract raw text
    # 2. Send to GPT-4.1-mini with extraction prompt
    # 3. Parse JSON response
    # 4. Return structured dict
    pass
```

**Expected output:**
```json
{
  "name": "John Smith",
  "email": "john@example.com",
  "phone": "+1-555-0123",
  "years_experience": 5,
  "current_role": "Senior Marketing Manager",
  "current_company": "Acme Corp",
  "skills": ["SEO", "Content Strategy", "Google Analytics", "Team Management"],
  "experience": [
    {
      "company": "Acme Corp",
      "role": "Senior Marketing Manager",
      "duration": "2021–present",
      "highlights": ["Led team of 8", "Increased organic traffic 150%"]
    }
  ],
  "education": [
    {
      "institution": "State University",
      "degree": "BS Marketing",
      "year": 2018
    }
  ],
  "summary": "5 years in digital marketing with focus on SEO and content strategy."
}
```

### Task 1.2: Question Generator
- [ ] Create `src/question_generator.py`
- [ ] Build prompt: resume_data + JD text → 5–8 screening questions
- [ ] Questions in 3 categories: resume verification (2), skills (2–3), behavioral (2)
- [ ] Each question references specific resume/JD details
- [ ] Test with all 5 sample resumes

**File: `src/question_generator.py`**

```python
def generate_questions(resume_data: dict, job_description: str) -> list[dict]:
    """Generate interview questions from resume + JD.
    
    Returns list of:
    {
        "question": "You mentioned leading a team of 8 at Acme Corp...",
        "category": "resume_verification",
        "intent": "Verify leadership experience claim",
        "follow_up_if_vague": "Can you give a specific example of a challenge you faced managing that team?"
    }
    """
    pass
```

### Task 1.3: Centralized Prompts
- [ ] Create `src/prompts.py`
- [ ] Store all system/user prompts as constants
- [ ] Makes it easy to iterate on prompt engineering

**Prompts to define:**

```python
RESUME_EXTRACTION_PROMPT = """
You are an expert resume parser. Extract structured information from the 
following resume text. Return valid JSON only.

Fields to extract:
- name, email, phone
- years_experience (integer)
- current_role, current_company
- skills (list of strings)
- experience (list of {company, role, duration, highlights})
- education (list of {institution, degree, year})
- summary (1-2 sentence overview)

Resume text:
{resume_text}
"""

QUESTION_GENERATION_PROMPT = """
You are an expert HR interviewer. Generate screening interview questions
for a candidate based on their resume and the job description.

Generate exactly {num_questions} questions in these categories:
1. Resume Verification (2 questions) — reference specific claims from resume
2. Role-Specific Skills (2-3 questions) — assess skills required by JD
3. Behavioral/Situational (2 questions) — predict job performance

Rules:
- Reference specific details from the resume (company names, numbers, claims)
- Questions must be open-ended (not yes/no)
- Difficulty should match the seniority level in the JD
- Include a follow-up question for each (used if answer is vague)

Resume data:
{resume_data}

Job description:
{job_description}

Return as JSON array of objects with fields: question, category, intent, follow_up_if_vague
"""

INTERVIEW_SYSTEM_PROMPT = """
You are conducting a screening interview for the role of {job_title}.
You are professional, friendly, and thorough. 

Your job:
1. Ask the planned questions one at a time
2. Listen to the candidate's response
3. If the response is vague (< 30 words or generic), ask a follow-up probing for specifics
4. If the response contradicts their resume, ask a clarification question
5. If the response is detailed and relevant, acknowledge briefly and move to the next question
6. After all questions, thank the candidate and end the interview

Resume summary: {resume_summary}
Job description summary: {jd_summary}

Planned questions:
{questions}

Rules:
- Never reveal the scoring criteria
- Never argue with the candidate
- Keep your responses under 50 words (you're an interviewer, not a lecturer)
- Reference specific details the candidate mentioned in previous answers
- Be conversational, not robotic
"""

EVALUATION_PROMPT = """
You are an expert HR evaluator. Analyze this interview transcript and 
produce a structured evaluation.

Job title: {job_title}
Job description: {job_description}
Candidate resume: {resume_summary}

Interview transcript:
{transcript}

Evaluate on these dimensions (score 1-10):
1. skill_match — Does the candidate have the skills required by the JD?
2. communication — Are answers clear, structured, and professional?
3. problem_solving — Does the candidate demonstrate analytical thinking?
4. cultural_fit — Does the candidate show alignment with role expectations?

Also provide:
- overall_score (weighted average: skill 40%, communication 20%, problem_solving 20%, cultural_fit 20%)
- summary (3-4 sentences)
- strengths (list of 2-4)
- gaps (list of 0-3)
- red_flags (list of 0-3, empty if none)
- recommendation: "strong_yes" | "yes" | "maybe" | "no" | "strong_no"

Return valid JSON only.
"""

FOLLOW_UP_DECISION_PROMPT = """
Analyze the candidate's latest response to the interview question.

Question asked: {question}
Candidate's answer: {answer}
Word count: {word_count}

Classify the answer quality:
- "vague": Answer is generic, lacks specifics, or under 30 words
- "contradictory": Answer contradicts information from their resume
- "detailed": Answer is specific, relevant, and adequately detailed

If "vague", generate a follow-up question probing for specifics.
If "contradictory", generate a clarification question referencing the resume.
If "detailed", respond with "NEXT" to proceed to the next planned question.

Resume context: {resume_summary}

Return JSON: {"quality": "vague|contradictory|detailed", "follow_up": "question text or NEXT"}
"""
```

### Week 1 Validation
- [ ] Parse all 5 sample resumes successfully
- [ ] Generated questions reference specific resume details
- [ ] Questions cover all 3 categories
- [ ] No hallucinated information in questions
- [ ] Token usage: <5K tokens per resume parse, <3K per question generation

---

## Week 2: Interview Simulation + Adaptive Follow-ups

**Status:** `NOT_STARTED`

### Task 2.1: Interview Engine (CLI)
- [ ] Create `src/interview_engine.py`
- [ ] Load resume data + generated questions
- [ ] Start conversational loop: AI asks → user types → AI evaluates → next question or follow-up
- [ ] Maintain conversation history (full transcript)
- [ ] Implement sliding window for context (last 5 exchanges to LLM, full history saved)

**File: `src/interview_engine.py`**

```python
class InterviewEngine:
    """Manages the interview conversation flow."""
    
    def __init__(self, resume_data: dict, job_description: str, questions: list[dict]):
        self.resume_data = resume_data
        self.job_description = job_description
        self.questions = questions
        self.transcript: list[dict] = []  # {"role": "interviewer"|"candidate", "content": "..."}
        self.current_question_index = 0
        self.follow_up_count = 0
        self.max_follow_ups_per_question = 2
        self.token_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    
    def get_next_action(self, candidate_response: str) -> dict:
        """Decide: follow-up on current question or move to next.
        Returns: {"action": "follow_up"|"next_question"|"end", "message": "AI response"}
        """
        pass
    
    def run_cli(self):
        """Run the full interview in terminal."""
        pass
```

### Task 2.2: Follow-up Logic
- [ ] After each candidate answer, classify quality: vague / contradictory / detailed
- [ ] If vague → ask follow-up probing for specifics (max 2 follow-ups per question)
- [ ] If contradictory → ask clarification referencing resume
- [ ] If detailed → acknowledge briefly, move to next question
- [ ] Track follow-up count per question (don't get stuck in loops)

**Decision tree:**
```
Candidate answers question
  │
  ├── Word count < 30?  → VAGUE → follow-up (if < 2 follow-ups already)
  │
  ├── Contradicts resume? → CONTRADICTORY → clarification question
  │
  ├── Detailed enough? → DETAILED → "Thanks. Next question..."
  │
  └── Max follow-ups hit? → Move to next question regardless
```

### Task 2.3: Conversation History Management
- [ ] Save full transcript as list of {role, content, timestamp}
- [ ] For LLM context: send system prompt + last 5 exchanges (sliding window)
- [ ] This keeps token usage manageable (~800 tokens/turn)
- [ ] Save complete transcript to JSON file for later evaluation

### Task 2.4: Main Entry Point
- [ ] Create `run_interview.py` — CLI that ties everything together
- [ ] Usage: `python run_interview.py --resume data/sample_resumes/marketing_manager.pdf --jd data/job_descriptions/marketing_manager.txt`
- [ ] Saves transcript to `output/transcripts/{timestamp}.json`

### Week 2 Validation
- [ ] Complete full interview with all 5 sample resumes
- [ ] Follow-ups trigger on vague answers (test with one-word answers)
- [ ] Follow-ups do NOT trigger on detailed answers
- [ ] Contradictions are caught when you intentionally lie
- [ ] Interview feels conversational, not robotic
- [ ] Token usage per full interview: <50K tokens
- [ ] Transcript JSON saved correctly

---

## Week 3: Evaluation + Scoring Output

**Status:** `NOT_STARTED`

### Task 3.1: Evaluation Engine
- [ ] Create `src/evaluator.py`
- [ ] Take full transcript + resume + JD → produce structured evaluation
- [ ] Scoring: skill_match, communication, problem_solving, cultural_fit (1–10)
- [ ] Overall score: weighted average (skill 40%, comm 20%, problem 20%, culture 20%)
- [ ] Summary: 3–4 sentences
- [ ] Strengths, gaps, red_flags as lists
- [ ] Recommendation: strong_yes / yes / maybe / no / strong_no

```python
def evaluate_interview(transcript: list[dict], resume_data: dict, job_description: str) -> dict:
    """Evaluate completed interview transcript.
    
    Returns:
    {
        "overall_score": 7.8,
        "scores": {"skill_match": 8, "communication": 7, "problem_solving": 8, "cultural_fit": 7},
        "summary": "Strong technical candidate with...",
        "strengths": ["Deep SEO knowledge", "Strategic thinking"],
        "gaps": ["Limited B2B experience"],
        "red_flags": [],
        "recommendation": "yes",
        "token_usage": {"prompt_tokens": 3200, "completion_tokens": 800},
        "cost_usd": 0.018
    }
    """
    pass
```

### Task 3.2: Cost Tracker Utility
- [ ] Create `src/utils.py`
- [ ] Track token usage across all API calls (parse + questions + interview + evaluation)
- [ ] Calculate USD cost using GPT-4.1-mini pricing
- [ ] Print cost summary at end of interview

```python
# GPT-4.1-mini pricing (as of 2026)
PRICING = {
    "gpt-4.1-mini": {
        "input": 0.40 / 1_000_000,   # $0.40 per 1M input tokens
        "output": 1.60 / 1_000_000,  # $1.60 per 1M output tokens
    }
}

def calculate_cost(prompt_tokens: int, completion_tokens: int, model: str = "gpt-4.1-mini") -> float:
    """Calculate USD cost from token counts."""
    pass

def print_cost_summary(usage_log: list[dict]) -> None:
    """Print formatted cost breakdown."""
    pass
```

### Task 3.3: Evaluation Runner
- [ ] Create `run_evaluation.py`
- [ ] Usage: `python run_evaluation.py --transcript output/transcripts/2026-01-15.json`
- [ ] Saves evaluation to `output/evaluations/{timestamp}.json`
- [ ] Prints summary to console

### Task 3.4: HR Feedback Collection
- [ ] Run 3 complete mock interviews (play as candidate yourself)
- [ ] Generate evaluations for each
- [ ] Share evaluation JSONs with 2–3 HR people (can be friends in recruiting)
- [ ] Ask: "Would this report be useful to you? What's missing?"
- [ ] Document feedback in `output/feedback_notes.md`

### Week 3 Validation & POC Sign-off
- [ ] 3 complete interviews with evaluations
- [ ] Scores feel reasonable (±1 point vs your own judgment)
- [ ] Summary captures key strengths and gaps accurately
- [ ] Red flags catch obvious issues (contradiction, evasiveness)
- [ ] Total cost per interview: <$0.20
- [ ] 2+ HR people say evaluation is useful
- [ ] All code committed to Git, clean project structure

**POC COMPLETE → Decision gate: proceed to Phase 1A or iterate on prompts**

---

## Artifacts Produced by Phase 0

These carry forward into Phase 1A:

| Artifact | Location | Used In Phase 1A |
|----------|----------|-----------------|
| Resume parser | `src/resume_parser.py` | Integrated into `/interview/start` endpoint |
| Question generator | `src/question_generator.py` | Called when interview begins |
| Interview engine | `src/interview_engine.py` | Refactored into `InterviewService` class |
| Evaluator | `src/evaluator.py` | Called on interview completion |
| All prompts | `src/prompts.py` | Moved to `app/services/prompts.py` |
| Cost tracker | `src/utils.py` | Integrated into usage tracking |
| Sample transcripts | `output/transcripts/` | Used for integration testing |
| Evaluation schema | JSON structure above | Becomes `Evaluation` DB model |

---

## Decisions to Make During POC

| Decision | Options | Default | Notes |
|----------|---------|---------|-------|
| Number of questions | 5 / 8 / 10 | 8 | Test what feels right during mock interviews |
| Max follow-ups per Q | 1 / 2 / 3 | 2 | >2 feels like interrogation |
| Sliding window size | 3 / 5 / 8 exchanges | 5 | Balance context vs cost |
| Scoring weights | Configurable | 40/20/20/20 | May adjust after HR feedback |
| Model | GPT-4.1-mini / GPT-4.1 | mini | Only upgrade if quality is bad |
