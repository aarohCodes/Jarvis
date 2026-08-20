from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import Task


def create_task(db: Session, title: str, notes: str | None, due_at, priority: str, source: str) -> Task:
    task = Task(title=title, notes=notes, due_at=due_at, priority=priority, status="open", source=source)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_tasks(db: Session, status: Optional[str] = None) -> list[Task]:
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    return query.order_by(Task.due_at.is_(None), Task.due_at).all()


def get_task(db: Session, task_id: str) -> Task | None:
    return db.query(Task).filter(Task.id == task_id).first()


def update_task(db: Session, task_id: str, **fields) -> Task | None:
    task = get_task(db, task_id)
    if task is None:
        return None
    for key, value in fields.items():
        if value is not None:
            setattr(task, key, value)
    if fields.get("status") == "completed" and task.completed_at is None:
        task.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task_id: str) -> bool:
    task = get_task(db, task_id)
    if task is None:
        return False
    db.delete(task)
    db.commit()
    return True
