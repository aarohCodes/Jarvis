"""
Syllabus storage and placeholder Q&A. Canvas's file API sits behind the same
restricted student API token as assignments, and CourseBook's own search is
blocked by reCAPTCHA-gated bot detection (confirmed against a real headless
browser session, not just raw HTTP), so syllabus PDFs can't be auto-fetched
from either source — the user uploads them manually once per course, either
as a PDF or as a photo/screenshot (extracted via Gemini vision, same pattern
as schedule_import_service.py). Text is extracted at upload time and stored
so the LLM layer can use it as context. naive_keyword_search() is a stopgap
until the chat layer answers these questions directly.
"""

import base64
import io
import os
import re
from datetime import datetime

from pypdf import PdfReader
from sqlalchemy.orm import Session

from models import Syllabus


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages).strip()


def _extract_text_from_image(image_bytes: bytes, mime_type: str) -> str:
    if os.getenv("LLM_PROVIDER", "").lower().strip() != "gemini":
        raise RuntimeError(
            "Syllabus photo import needs LLM_PROVIDER=gemini (with GEMINI_API_KEY) — "
            "that's the only provider this feature is wired up for so far. "
            "Upload a PDF instead, or switch LLM_PROVIDER to gemini."
        )
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("LLM_PROVIDER=gemini but GEMINI_API_KEY is not set.")

    from google import genai

    model = os.getenv("LLM_MODEL") or "gemini-3.6-flash"
    client = genai.Client(api_key=api_key)
    contents = [{
        "role": "user",
        "parts": [
            {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode("ascii")}},
            {"text": (
                "Transcribe the full text content of this syllabus image as plain text. "
                "Preserve the section/paragraph structure with a blank line between distinct "
                "sections (headings, policies, schedule entries, etc). Don't summarize, "
                "paraphrase, or omit anything — this text will be used later to answer "
                "detailed questions about the course."
            )},
        ],
    }]
    response = client.models.generate_content(model=model, contents=contents)
    return (response.text or "").strip()


def _upsert_syllabus(db: Session, course_code: str, file_name: str, raw_text: str) -> Syllabus:
    course_code = course_code.lower().strip()
    row = db.query(Syllabus).filter(Syllabus.course_code == course_code).first()
    if row is None:
        row = Syllabus(course_code=course_code)
        db.add(row)

    row.file_name = file_name
    row.raw_text = raw_text
    row.uploaded_at = datetime.utcnow()

    db.commit()
    db.refresh(row)
    return row


def store_syllabus(db: Session, course_code: str, file_name: str, file_bytes: bytes) -> Syllabus:
    raw_text = _extract_text_from_pdf(file_bytes)
    if not raw_text:
        raise ValueError("No extractable text found in the uploaded PDF.")
    return _upsert_syllabus(db, course_code, file_name, raw_text)


def store_syllabus_from_image(db: Session, course_code: str, file_name: str, image_bytes: bytes, mime_type: str) -> Syllabus:
    raw_text = _extract_text_from_image(image_bytes, mime_type)
    if not raw_text:
        raise ValueError("Gemini couldn't read any text from that image.")
    return _upsert_syllabus(db, course_code, file_name, raw_text)


def list_syllabi(db: Session) -> list[Syllabus]:
    return db.query(Syllabus).order_by(Syllabus.course_code).all()


def delete_syllabus(db: Session, course_code: str) -> bool:
    row = db.query(Syllabus).filter(Syllabus.course_code == course_code.lower().strip()).first()
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def get_syllabus_text(db: Session, course_code: str) -> str | None:
    row = db.query(Syllabus).filter(Syllabus.course_code == course_code.lower().strip()).first()
    return row.raw_text if row else None


def naive_keyword_search(raw_text: str, question: str, top_n: int = 1) -> str:
    """
    Crude paragraph-relevance match: splits the syllabus into paragraphs,
    scores each by overlap with the question's significant words, and
    returns the best-matching paragraph(s). Placeholder until Stage 5's LLM
    layer can answer using the full stored text as context.
    """
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "of", "to", "in", "on",
        "for", "and", "or", "what", "when", "where", "how", "do", "does",
        "my", "will", "be", "this", "that", "with", "class", "course",
    }
    question_words = {
        w for w in re.findall(r"[a-z0-9']+", question.lower()) if w not in stopwords
    }
    if not question_words:
        return "Couldn't extract any meaningful keywords from that question."

    paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
    if not paragraphs:
        return "No content available to search."

    scored = []
    for paragraph in paragraphs:
        paragraph_words = set(re.findall(r"[a-z0-9']+", paragraph.lower()))
        overlap = len(question_words & paragraph_words)
        if overlap:
            scored.append((overlap, paragraph))

    if not scored:
        return "Couldn't find anything in the syllabus matching that question."

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return "\n\n---\n\n".join(p for _, p in scored[:top_n])
