from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import Reminder


def create_reminder(db: Session, text: str, remind_at, recurrence_rule: str | None, delivery_channel: str) -> Reminder:
    reminder = Reminder(
        text=text,
        remind_at=remind_at,
        recurrence_rule=recurrence_rule,
        delivery_channel=delivery_channel,
        status="pending",
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


def list_reminders(db: Session, status: Optional[str] = None) -> list[Reminder]:
    query = db.query(Reminder)
    if status:
        query = query.filter(Reminder.status == status)
    return query.order_by(Reminder.remind_at).all()


def get_reminder(db: Session, reminder_id: str) -> Reminder | None:
    return db.query(Reminder).filter(Reminder.id == reminder_id).first()


def update_reminder(db: Session, reminder_id: str, **fields) -> Reminder | None:
    reminder = get_reminder(db, reminder_id)
    if reminder is None:
        return None
    for key, value in fields.items():
        if value is not None:
            setattr(reminder, key, value)
    db.commit()
    db.refresh(reminder)
    return reminder


def delete_reminder(db: Session, reminder_id: str) -> bool:
    reminder = get_reminder(db, reminder_id)
    if reminder is None:
        return False
    db.delete(reminder)
    db.commit()
    return True


def get_due_reminders(db: Session, as_of: datetime | None = None) -> list[Reminder]:
    as_of = as_of or datetime.now(timezone.utc)
    return (
        db.query(Reminder)
        .filter(Reminder.status == "pending")
        .filter(Reminder.remind_at <= as_of)
        .all()
    )


def mark_fired(db: Session, reminder: Reminder) -> None:
    reminder.status = "fired"
    reminder.fired_at = datetime.now(timezone.utc)
    db.commit()
