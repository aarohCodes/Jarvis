"""
Syllabus storage and placeholder Q&A. Canvas's file API sits behind the same
restricted student API token as assignments, so syllabus PDFs can't be
auto-fetched — the user uploads them manually once per course. Text is
extracted at upload time and stored so the LLM layer (Stage 5) can use it as
context later. naive_keyword_search() is a stopgap until then.
"""

import io
import re
from datetime import datetime

from pypdf import PdfReader
from sqlalchemy.orm import Session

from models import Syllabus


def _extract_text(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages).strip()


def store_syllabus(db: Session, course_code: str, file_name: str, file_bytes: bytes) -> Syllabus:
    course_code = course_code.lower().strip()
    raw_text = _extract_text(file_bytes)
    if not raw_text:
        raise ValueError("No extractable text found in the uploaded PDF.")

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
