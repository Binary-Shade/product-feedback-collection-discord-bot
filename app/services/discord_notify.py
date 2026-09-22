import datetime as dt
import httpx

from app.models import GuildConfig, App, Feedback

TYPE_META = {
    "bug": {"emoji": "🐛", "label": "BUG REPORT", "color": 0xE74C3C, "field": "bugs_webhook_url"},
    "feature": {"emoji": "💡", "label": "FEATURE REQUEST", "color": 0xF1C40F, "field": "features_webhook_url"},
    "feedback": {"emoji": "🌱", "label": "GENERAL FEEDBACK", "color": 0x2ECC71, "field": "feedback_webhook_url"},
}


def _build_embed(app: App, feedback: Feedback) -> dict:
    meta = TYPE_META[feedback.type]

    fields = [{"name": "📦 App", "value": app.name, "inline": True}]
    if feedback.app_version:
        fields.append({"name": "📱 App Version", "value": feedback.app_version, "inline": True})
    if feedback.platform:
        fields.append({"name": "🤖 Platform", "value": feedback.platform, "inline": True})
    if feedback.device:
        fields.append({"name": "📲 Device", "value": feedback.device, "inline": True})
    if feedback.language:
        fields.append({"name": "🌐 Language", "value": feedback.language, "inline": True})
    fields.append({"name": "👤 User", "value": feedback.user_id or "Anonymous", "inline": True})

    return {
        "embeds": [
            {
                "title": f"{meta['emoji']} {meta['label']}",
                "description": feedback.message,
                "color": meta["color"],
                "fields": fields,
                "footer": {"text": f"Submitted {feedback.submitted_at.strftime('%d %b %Y, %I:%M %p UTC')}"},
            }
        ]
    }


async def notify_discord(guild_config: GuildConfig, app: App, feedback: Feedback) -> bool:
    """Posts the feedback to the correct channel's webhook for this guild.
    Returns True on success. Never raises — a Discord outage shouldn't fail
    the feedback submission, since it's already saved in the database."""
    meta = TYPE_META[feedback.type]
    webhook_url = getattr(guild_config, meta["field"])
    if not webhook_url:
        return False

    payload = _build_embed(app, feedback)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json=payload)
            return resp.status_code in (200, 204)
    except httpx.HTTPError:
        return False
