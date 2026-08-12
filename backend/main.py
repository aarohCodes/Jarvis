import os
import redis
from fastapi import FastAPI
from sqlalchemy import create_engine, text

app = FastAPI(title="Personal Assistant Backend")

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

engine = create_engine(DATABASE_URL) if DATABASE_URL else None
redis_client = redis.from_url(REDIS_URL) if REDIS_URL else None


@app.get("/")
def root():
    return {"status": "ok", "service": "personal-assistant-backend"}


@app.get("/health")
def health():
    db_ok = False
    redis_ok = False

    if engine is not None:
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