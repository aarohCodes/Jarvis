from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from models import Preference


def get_preference(db: Session, key: str) -> Any | None:
    row = db.query(Preference).filter(Preference.key == key).first()
    return row.value if row else None


def list_preferences(db: Session) -> list[Preference]:
    return db.query(Preference).order_by(Preference.key).all()


def set_preference(db: Session, key: str, value: Any) -> Preference:
    row = db.query(Preference).filter(Preference.key == key).first()
    if row is None:
        row = Preference(key=key, value=value)
        db.add(row)
    else:
        row.value = value
        row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


def delete_preference(db: Session, key: str) -> bool:
    row = db.query(Preference).filter(Preference.key == key).first()
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True
