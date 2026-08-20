"""
Push notification delivery via ntfy.sh (https://ntfy.sh) — free, no account
or API key required. Set NTFY_TOPIC in .env to a private, hard-to-guess
topic name (anyone who knows the topic name can read from or post to it, so
treat it like a shared secret, not a public label) and install the ntfy app
(iOS/Android), subscribing to that same topic name. Once set, the scheduler
actually reaches out instead of only logging to action_log/stdout.

If NTFY_TOPIC isn't set, send_notification() just returns False — the
scheduler still runs and logs normally, this only gates the extra push.
"""

import os

import requests

def send_notification(title: str, message: str, priority: str = "default") -> bool:
    topic = os.getenv("NTFY_TOPIC")
    if not topic:
        return False
    # os.getenv(key, default) only falls back when the var is absent — .env
    # sets NTFY_SERVER="" (present, empty) when left blank, so `or` is
    # required here too (same class of bug fixed in llm_provider.py earlier).
    base = (os.getenv("NTFY_SERVER") or "https://ntfy.sh").rstrip("/")
    try:
        requests.post(
            f"{base}/{topic}",
            data=message.encode("utf-8"),
            headers={"Title": title, "Priority": priority},
            timeout=10,
        )
        return True
    except requests.RequestException:
        return False
