import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import App
from app.config import settings

# very simple in-memory sliding-window rate limiter, keyed by api key.
# fine for a single-process VPS deployment; swap for redis if you scale out.
_request_log: dict[str, deque] = defaultdict(deque)


def _check_rate_limit(api_key: str):
    now = time.time()
    window = 60.0
    log = _request_log[api_key]
    while log and now - log[0] > window:
        log.popleft()
    if len(log) >= settings.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Too many requests. Slow down.")
    log.append(now)


def get_current_app(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> App:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    app_row = db.query(App).filter(App.api_key == x_api_key).first()
    if not app_row:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if not app_row.active:
        raise HTTPException(status_code=403, detail="This app's API key has been revoked")

    _check_rate_limit(x_api_key)
    return app_row
