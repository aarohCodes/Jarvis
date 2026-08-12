import os
from datetime import datetime, timezone

import redis
from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import engine, get_db
from models import Task

app = FastAPI(title="Personal Assistant Backend")

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
    """Writes a task then reads it back, to confirm read/write against Postgres."""
    task = Task(
        title="Test task from /debug/tasks/test",
        notes="Created to verify DB read/write works",
        due_at=datetime.now(timezone.utc),
        priority="normal",
        status="open",
        source="manual",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    fetched = db.query(Task).filter(Task.id == task.id).first()

    return {
        "written_id": task.id,
        "read_back_title": fetched.title if fetched else None,
        "read_back_status": fetched.status if fetched else None,
    }


@app.get("/debug/tasks")
def list_tasks(db: Session = Depends(get_db)):
    tasks = db.query(Task).order_by(Task.created_at.desc()).limit(20).all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "status": t.status,
            "due_at": t.due_at,
            "created_at": t.created_at,
        }
        for t in tasks
    ]