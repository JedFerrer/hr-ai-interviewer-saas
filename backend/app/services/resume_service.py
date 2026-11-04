"""Resume service: file parsing (PDF/DOCX) + LLM extraction."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pdfplumber
from docx import Document as DocxDocument
from openai import AsyncOpenAI, OpenAI

from app.config import get_settings
from app.services.llm_utils import strip_code_fences
from app.services.prompts import RESUME_EXTRACTION_PROMPT

_settings = get_settings()

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def extract_text_from_bytes(content: bytes, filename: str) -> str:
    """Extract text from resume file bytes. Supports PDF and DOCX.

    Raises ValueError if format unsupported or no text extracted.
    """
    from app.utils.storage import validate_resume_file, validate_resume_content
    validate_resume_file(filename, len(content))
    validate_resume_content(filename, content)
    env = {k: v for k, v in os.environ.items() if k.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH"}}
    env.update(PYTHONPATH=str(Path(__file__).resolve().parents[2]), PYTHONUTF8="1")
    with tempfile.TemporaryDirectory(prefix="hr-parser-", dir=os.environ.get("HR_DEMO_TEMP")) as owned:
        try:
            result = subprocess.run([sys.executable, "-m", "app.utils.resume_worker", Path(filename).suffix.lower()],
                input=content, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                env=env, cwd=owned, timeout=12, check=False)
        except subprocess.TimeoutExpired:
            raise ValueError("Resume parsing exceeded its time limit") from None
    if result.returncode != 0 or len(result.stdout) > 400_000:
        raise ValueError("Resume is malformed, empty, or exceeds parser limits")
    return result.stdout.decode("utf-8")


def _extract_pdf(content: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber."""
    pages: list[str] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        if len(pdf.pages) > 30:
            raise ValueError("PDF exceeds 30 pages")
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
                if sum(map(len, pages)) > 100_000:
                    raise ValueError("Resume text exceeds 100,000 characters")

    if not pages:
        raise ValueError("No text could be extracted from PDF. Is this a scanned/image PDF?")
    return "\n\n".join(pages)


def _extract_docx(content: bytes) -> str:
    """Extract text from DOCX bytes using python-docx."""
    doc = DocxDocument(io.BytesIO(content))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    if not paragraphs:
        raise ValueError("No text could be extracted from DOCX. Is the document empty?")
    text = "\n\n".join(paragraphs)
    if len(text) > 100_000:
        raise ValueError("Resume text exceeds 100,000 characters")
    return text


def parse_resume_with_llm(
    client: OpenAI, resume_text: str
) -> tuple[dict, int, int]:
    """Send resume text to LLM, return (structured_data, prompt_tokens, completion_tokens)."""
    if _settings.portfolio_demo:
        raise ValueError("Synchronous provider operation has no demo adapter")
    prompt = RESUME_EXTRACTION_PROMPT.format(resume_text=resume_text)
    response = client.chat.completions.create(
        model=_settings.active_llm_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    raw = response.choices[0].message.content or ""
    cleaned = strip_code_fences(raw)
    data = json.loads(cleaned)

    pt = response.usage.prompt_tokens if response.usage else 0
    ct = response.usage.completion_tokens if response.usage else 0
    return data, pt, ct


async def parse_resume_with_llm_async(
    client: AsyncOpenAI, resume_text: str
) -> tuple[dict, int, int]:
    """Async version: send resume text to LLM with provider fallback.

    Returns (validated_resume_dict, prompt_tokens, completion_tokens).

    The raw LLM JSON is validated through `ResumeData` so callers always get a
    normalized shape; invalid payloads raise ValueError (caught upstream).
    """
    from app.schemas.resume import ResumeData
    from app.services.llm_client import llm_chat_completion

    prompt = RESUME_EXTRACTION_PROMPT.format(resume_text=resume_text)
    response, _model = await llm_chat_completion(
        operation="parse", demo_context={"text": resume_text},
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        json_mode=True,
    )
    raw = response.choices[0].message.content or ""
    cleaned = strip_code_fences(raw)
    raw_data = json.loads(cleaned)
    if not isinstance(raw_data, dict):
        raise ValueError("LLM did not return a JSON object for resume data")

    try:
        validated = ResumeData.model_validate(raw_data)
    except Exception as exc:  # ValidationError -> normalize to ValueError
        raise ValueError(f"Resume data failed validation: {exc}") from exc
    data = validated.model_dump()

    pt = response.usage.prompt_tokens if response.usage else 0
    ct = response.usage.completion_tokens if response.usage else 0
    return data, pt, ct


