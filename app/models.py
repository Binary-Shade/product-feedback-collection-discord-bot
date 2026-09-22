import secrets
import datetime as dt

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base


def generate_api_key() -> str:
    return f"fb_{secrets.token_urlsafe(32)}"


class GuildConfig(Base):
    """One row per Discord server the bot has been set up in.
    Holds the channel + webhook the bot posts each feedback type into."""
    __tablename__ = "guild_configs"

    id = Column(Integer, primary_key=True)
    guild_id = Column(String, unique=True, nullable=False, index=True)
    category_id = Column(String, nullable=True)

    bugs_channel_id = Column(String, nullable=True)
    bugs_webhook_url = Column(String, nullable=True)

    feedback_channel_id = Column(String, nullable=True)
    feedback_webhook_url = Column(String, nullable=True)

    features_channel_id = Column(String, nullable=True)
    features_webhook_url = Column(String, nullable=True)

    created_at = Column(DateTime, default=dt.datetime.utcnow)

    apps = relationship("App", back_populates="guild")


class App(Base):
    """A registered application allowed to submit feedback. Each app has its
    own API key and is tied to the Discord guild whose channels it posts into."""
    __tablename__ = "apps"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    api_key = Column(String, unique=True, nullable=False, default=generate_api_key, index=True)
    guild_id = Column(String, ForeignKey("guild_configs.guild_id"), nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    guild = relationship("GuildConfig", back_populates="apps")
    feedback_items = relationship("Feedback", back_populates="app")


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True)
    app_id = Column(Integer, ForeignKey("apps.id"), nullable=False)
    type = Column(String, nullable=False)  # bug | feedback | feature
    message = Column(Text, nullable=False)

    app_version = Column(String, nullable=True)
    platform = Column(String, nullable=True)
    device = Column(String, nullable=True)
    language = Column(String, nullable=True)
    user_id = Column(String, nullable=True)

    submitted_at = Column(DateTime, default=dt.datetime.utcnow)

    app = relationship("App", back_populates="feedback_items")
