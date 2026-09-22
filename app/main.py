from fastapi import FastAPI

from app.database import init_db
from app.routes import feedback

app = FastAPI(title="Universal Feedback Bot API", version="1.0.0")

app.include_router(feedback.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
