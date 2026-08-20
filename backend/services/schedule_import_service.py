"""
Class schedule import from a photo/screenshot, using Gemini's vision +
structured JSON output — no separate OCR service needed. This is
Gemini-specific for now (unlike chat_service/llm_provider, which are
provider-agnostic): image handling differs enough across providers that
it wasn't worth generalizing before there's a second provider that needs it.
"""

import base64
import json
import os

from sqlalchemy.orm import Session

from services import course_schedule

_SCHEDULE_SCHEMA = {
    "type": "object",
    "properties": {
        "classes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "course_code": {"type": "string", "description": "e.g. cs3345, lowercase, no spaces"},
                    "section": {"type": "string", "description": "e.g. 004"},
                    "course_title": {"type": "string"},
                    "instructor": {"type": "string"},
                    "days": {"type": "string", "description": "day letters concatenated with no separator, e.g. MW, TTh, MWF"},
                    "start_time": {"type": "string", "description": "e.g. 10:00 am"},
                    "end_time": {"type": "string", "description": "e.g. 11:15 am"},
                    "location": {"type": "string", "description": "building + room, e.g. ECSS 2.311"},
                },
                "required": ["course_code", "section"],
            },
        },
    },
    "required": ["classes"],
}

_PROMPT = (
    "This image shows one or more university class schedule entries — it "
    "could be a screenshot of a course catalog/registration portal, a photo "
    "of a printed schedule, or a syllabus header. Extract every distinct "
    "class section visible in the image. If a field isn't visible or can't "
    "be determined confidently, omit it rather than guessing."
)


def _get_gemini_client_and_model():
    if os.getenv("LLM_PROVIDER", "").lower().strip() != "gemini":
        raise RuntimeError(
            "Schedule image import needs LLM_PROVIDER=gemini (with GEMINI_API_KEY) — "
            "that's the only provider this feature is wired up for so far."
        )
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("LLM_PROVIDER=gemini but GEMINI_API_KEY is not set.")

    from google import genai

    model = os.getenv("LLM_MODEL") or "gemini-3.6-flash"
    return genai.Client(api_key=api_key), model


def extract_classes_from_image(image_bytes: bytes, mime_type: str) -> list[dict]:
    client, model = _get_gemini_client_and_model()

    from google.genai import types

    contents = [{
        "role": "user",
        "parts": [
            {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode("ascii")}},
            {"text": _PROMPT},
        ],
    }]
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=_SCHEDULE_SCHEMA,
        ),
    )
    payload = json.loads(response.text)
    return payload.get("classes", [])


def import_classes_from_image(db: Session, term: str, image_bytes: bytes, mime_type: str) -> list:
    classes = extract_classes_from_image(image_bytes, mime_type)
    rows = []
    for entry in classes:
        course_code = (entry.get("course_code") or "").strip()
        section = (entry.get("section") or "").strip()
        if not course_code or not section:
            continue
        row = course_schedule.create_manual_course(
            db,
            term=term,
            course_code=course_code,
            section=section,
            course_title=entry.get("course_title"),
            instructor=entry.get("instructor"),
            days=entry.get("days"),
            start_time=entry.get("start_time"),
            end_time=entry.get("end_time"),
            location=entry.get("location"),
        )
        rows.append(row)
    return rows
