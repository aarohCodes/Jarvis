import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from services import briefing_service
from services import canvas_ical
from chat import chat_service
from services import course_schedule
from services import preferences_service
from services import reminders_service
from services import schedule_import_service
import scheduler
from services import syllabus_service
from services import tasks_service
from services import weather_service
from database import engine, get_db
from models import Task
from schemas import (
    ChatRequest,
    CourseManualCreate,
    CourseUpdate,
    PreferenceSet,
    ReminderCreate,
    ReminderUpdate,
    TaskCreate,
    TaskUpdate,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Personal Assistant Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # no auth/cookies in this personal, local-only project — safe to be permissive
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL = os.getenv("REDIS_URL")
redis_client = redis.from_url(REDIS_URL) if REDIS_URL else None


@app.get("/")
def root():
    return {"status": "ok", "service": "personal-assistant-backend"}


@app.get("/health")
def health():
    db_ok = False
    redis_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    if redis_client is not None:
        try:
            redis_client.ping()
            redis_ok = True
        except Exception:
            redis_ok = False
    return {"database": db_ok, "redis": redis_ok}


@app.post("/debug/tasks/test")
def create_test_task(db: Session = Depends(get_db)):
    task = Task(
        title="Test task from /debug/tasks/test",
        due_at=datetime.now(timezone.utc),
        priority="normal",
        status="open",
        source="manual",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"written_id": task.id, "title": task.title}


# ---------- Tasks ----------

def _task_out(t: Task) -> dict:
    return {
        "id": t.id, "title": t.title, "notes": t.notes,
        "due_at": t.due_at, "priority": t.priority, "status": t.status,
        "source": t.source, "created_at": t.created_at, "completed_at": t.completed_at,
    }


@app.post("/tasks")
def create_task(body: TaskCreate, db: Session = Depends(get_db)):
    task = tasks_service.create_task(db, body.title, body.notes, body.due_at, body.priority, body.source)
    return _task_out(task)


@app.get("/tasks")
def list_tasks(status: str | None = None, db: Session = Depends(get_db)):
    return [_task_out(t) for t in tasks_service.list_tasks(db, status)]


@app.get("/tasks/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = tasks_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return _task_out(task)


@app.put("/tasks/{task_id}")
def update_task(task_id: str, body: TaskUpdate, db: Session = Depends(get_db)):
    task = tasks_service.update_task(db, task_id, **body.model_dump(exclude_unset=True))
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return _task_out(task)


@app.delete("/tasks/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    if not tasks_service.delete_task(db, task_id):
        raise HTTPException(status_code=404, detail="Task not found.")
    return {"deleted": task_id}


# ---------- Reminders ----------

def _reminder_out(r) -> dict:
    return {
        "id": r.id, "text": r.text, "remind_at": r.remind_at,
        "recurrence_rule": r.recurrence_rule, "delivery_channel": r.delivery_channel,
        "status": r.status, "created_at": r.created_at, "fired_at": r.fired_at,
    }


@app.post("/reminders")
def create_reminder(body: ReminderCreate, db: Session = Depends(get_db)):
    reminder = reminders_service.create_reminder(db, body.text, body.remind_at, body.recurrence_rule, body.delivery_channel)
    return _reminder_out(reminder)


@app.get("/reminders")
def list_reminders(status: str | None = None, db: Session = Depends(get_db)):
    return [_reminder_out(r) for r in reminders_service.list_reminders(db, status)]


@app.get("/reminders/{reminder_id}")
def get_reminder(reminder_id: str, db: Session = Depends(get_db)):
    reminder = reminders_service.get_reminder(db, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found.")
    return _reminder_out(reminder)


@app.put("/reminders/{reminder_id}")
def update_reminder(reminder_id: str, body: ReminderUpdate, db: Session = Depends(get_db)):
    reminder = reminders_service.update_reminder(db, reminder_id, **body.model_dump(exclude_unset=True))
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found.")
    return _reminder_out(reminder)


@app.delete("/reminders/{reminder_id}")
def delete_reminder(reminder_id: str, db: Session = Depends(get_db)):
    if not reminders_service.delete_reminder(db, reminder_id):
        raise HTTPException(status_code=404, detail="Reminder not found.")
    return {"deleted": reminder_id}


# ---------- Preferences (home location, wake time, timezone, etc.) ----------

@app.get("/preferences")
def list_preferences(db: Session = Depends(get_db)):
    return [{"key": p.key, "value": p.value, "updated_at": p.updated_at} for p in preferences_service.list_preferences(db)]


@app.get("/preferences/{key}")
def get_preference(key: str, db: Session = Depends(get_db)):
    value = preferences_service.get_preference(db, key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"No preference set for '{key}'.")
    return {"key": key, "value": value}


@app.put("/preferences/{key}")
def set_preference(key: str, body: PreferenceSet, db: Session = Depends(get_db)):
    row = preferences_service.set_preference(db, key, body.value)
    return {"key": row.key, "value": row.value, "updated_at": row.updated_at}


@app.delete("/preferences/{key}")
def delete_preference(key: str, db: Session = Depends(get_db)):
    if not preferences_service.delete_preference(db, key):
        raise HTTPException(status_code=404, detail=f"No preference set for '{key}'.")
    return {"deleted": key}


# ---------- Course schedule (CourseBook + manual entry) ----------

def _course_out(c) -> dict:
    return {
        "id": c.id, "term": c.term, "course_code": c.course_code, "section": c.section,
        "title": c.course_title, "instructor": c.instructor, "days": c.days,
        "start_time": c.start_time, "end_time": c.end_time, "location": c.location,
        "synced_at": c.synced_at,
    }


@app.post("/courses/add")
def add_course(term: str, course_code: str, section: str, db: Session = Depends(get_db)):
    """
    Attempts a live CourseBook lookup. As of 2026-08, CourseBook's search is
    unvalidated for anonymous/programmatic access (see course_schedule.py) —
    use POST /courses/manual instead until that's resolved.
    """
    try:
        row = course_schedule.add_or_update_course(db, term, course_code, section)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CourseBook lookup failed: {e}")
    return _course_out(row)


@app.post("/courses/manual")
def add_course_manual(body: CourseManualCreate, db: Session = Depends(get_db)):
    row = course_schedule.create_manual_course(db, **body.model_dump())
    return _course_out(row)


@app.get("/courses/schedule")
def get_schedule(db: Session = Depends(get_db)):
    return [_course_out(c) for c in course_schedule.get_all_courses(db)]


@app.post("/courses/import-image")
async def import_course_image(
    term: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a photo/screenshot of one or more class schedule entries (course
    catalog screenshot, printed schedule, syllabus header, etc). Uses
    Gemini's vision + structured output to extract each class and adds it
    the same way POST /courses/manual does.
    """
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=422, detail=f"Expected an image file, got {file.content_type}.")
    image_bytes = await file.read()
    try:
        rows = schedule_import_service.import_classes_from_image(db, term, image_bytes, file.content_type)
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Schedule image import failed: {e}")
    return {"imported": len(rows), "classes": [_course_out(r) for r in rows]}


@app.put("/courses/{course_id}")
def update_course(course_id: str, body: CourseUpdate, db: Session = Depends(get_db)):
    row = course_schedule.update_course(db, course_id, **body.model_dump(exclude_unset=True))
    if row is None:
        raise HTTPException(status_code=404, detail="Course section not found.")
    return _course_out(row)


@app.delete("/courses/{course_id}")
def delete_course(course_id: str, db: Session = Depends(get_db)):
    if not course_schedule.delete_course(db, course_id):
        raise HTTPException(status_code=404, detail="Course section not found.")
    return {"deleted": course_id}


@app.get("/courses/next")
def get_next_class(db: Session = Depends(get_db)):
    row = course_schedule.get_next_class(db)
    if not row:
        raise HTTPException(status_code=404, detail="No class found for today.")
    return _course_out(row)


# ---------- Assignments (Canvas iCal feed) ----------

@app.post("/assignments/sync")
def sync_assignments(db: Session = Depends(get_db)):
    try:
        count = canvas_ical.sync_assignments(db)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Canvas iCal sync failed: {e}")
    return {"synced": count}


@app.get("/assignments/due-this-week")
def due_this_week(db: Session = Depends(get_db)):
    rows = canvas_ical.get_due_this_week(db)
    return [{"title": r.title, "course": r.course_name, "due_at": r.due_at} for r in rows]


@app.get("/assignments/due-today")
def due_today(db: Session = Depends(get_db)):
    rows = canvas_ical.get_due_today(db)
    return [{"title": r.title, "course": r.course_name, "due_at": r.due_at} for r in rows]


# ---------- Syllabus upload + Q&A ----------

@app.post("/syllabus/upload")
async def upload_syllabus(
    course_code: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Accepts either a PDF (extracted with pypdf) or a photo/screenshot of
    a syllabus (extracted with Gemini vision — see syllabus_service.py)."""
    content_type = file.content_type or ""
    file_bytes = await file.read()
    try:
        if content_type == "application/pdf":
            row = syllabus_service.store_syllabus(db, course_code, file.filename, file_bytes)
        elif content_type.startswith("image/"):
            row = syllabus_service.store_syllabus_from_image(db, course_code, file.filename, file_bytes, content_type)
        else:
            raise HTTPException(status_code=422, detail=f"Unsupported file type '{content_type}' — upload a PDF or an image.")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Syllabus import failed: {e}")
    return {"course_code": row.course_code, "file_name": row.file_name, "characters_extracted": len(row.raw_text)}


@app.get("/syllabus")
def list_syllabi(db: Session = Depends(get_db)):
    return [
        {"course_code": s.course_code, "file_name": s.file_name, "uploaded_at": s.uploaded_at, "characters": len(s.raw_text)}
        for s in syllabus_service.list_syllabi(db)
    ]


@app.delete("/syllabus/{course_code}")
def delete_syllabus(course_code: str, db: Session = Depends(get_db)):
    if not syllabus_service.delete_syllabus(db, course_code):
        raise HTTPException(status_code=404, detail=f"No syllabus uploaded for {course_code}.")
    return {"deleted": course_code}


@app.get("/syllabus/ask")
def ask_syllabus(course_code: str, question: str, db: Session = Depends(get_db)):
    raw_text = syllabus_service.get_syllabus_text(db, course_code)
    if not raw_text:
        raise HTTPException(status_code=404, detail=f"No syllabus uploaded yet for {course_code}.")
    answer = syllabus_service.naive_keyword_search(raw_text, question)
    return {"course_code": course_code, "question": question, "answer": answer}


# ---------- Weather ----------

@app.get("/weather")
def get_weather(db: Session = Depends(get_db)):
    try:
        return weather_service.get_current_weather(db)
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Weather lookup failed: {e}")


# ---------- Morning briefing ----------

@app.get("/briefing/morning")
def get_morning_briefing(db: Session = Depends(get_db)):
    return briefing_service.get_morning_briefing(db)


# ---------- Chat (Stage 5: LLM + tool-calling) ----------

@app.post("/chat")
def chat(body: ChatRequest, db: Session = Depends(get_db)):
    try:
        reply = chat_service.send_message(db, body.session_id, body.message)
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"session_id": body.session_id, "reply": reply}


@app.get("/chat/history")
def chat_history(session_id: str = "default", db: Session = Depends(get_db)):
    rows = chat_service.get_history(db, session_id)
    return [
        {"role": r.role, "content": r.content, "tool_name": r.tool_name, "created_at": r.created_at}
        for r in rows
        if r.role in ("user", "assistant") and r.content
    ]
