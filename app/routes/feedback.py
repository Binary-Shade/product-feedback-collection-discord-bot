from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import get_current_app
from app.schemas import FeedbackIn, FeedbackOut
from app.models import Feedback, GuildConfig, App
from app.services.discord_notify import notify_discord

router = APIRouter(prefix="/api/v1", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackOut)
async def submit_feedback(
    payload: FeedbackIn,
    current_app: App = Depends(get_current_app),
    db: Session = Depends(get_db),
):
    feedback = Feedback(
        app_id=current_app.id,
        type=payload.type,
        message=payload.message,
        app_version=payload.app_version,
        platform=payload.platform,
        device=payload.device,
        language=payload.language,
        user_id=payload.user_id,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    guild_config = db.query(GuildConfig).filter(GuildConfig.guild_id == current_app.guild_id).first()
    if guild_config:
        # Fire-and-forget-ish: we still await it, but failures never block success.
        await notify_discord(guild_config, current_app, feedback)

    return FeedbackOut(success=True, message="Feedback received")
