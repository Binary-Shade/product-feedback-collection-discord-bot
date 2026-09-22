from typing import Literal, Optional
from pydantic import BaseModel, Field


class FeedbackIn(BaseModel):
    type: Literal["bug", "feedback", "feature"]
    message: str = Field(min_length=1, max_length=4000)
    app_version: Optional[str] = None
    platform: Optional[str] = None
    device: Optional[str] = None
    language: Optional[str] = None
    user_id: Optional[str] = None


class FeedbackOut(BaseModel):
    success: bool
    message: str
