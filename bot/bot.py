import discord
from discord import app_commands
from discord.ext import commands

from app.config import settings
from app.database import init_db, SessionLocal
from app.models import GuildConfig, App

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


def is_admin(user_id: int) -> bool:
    # If no admins were configured, fall back to "anyone can admin" so the
    # bot is usable out of the box — but you should set ADMIN_DISCORD_IDS.
    if not settings.ADMIN_DISCORD_IDS:
        return True
    return user_id in settings.ADMIN_DISCORD_IDS


def admin_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not is_admin(interaction.user.id):
            await interaction.response.send_message(
                "🚫 You're not allowed to run admin commands on this bot.", ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)


@bot.event
async def on_ready():
    init_db()
    try:
        synced = await tree.sync()
        print(f"Logged in as {bot.user}. Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Slash command sync failed: {e}")


# ---------------------------------------------------------------------------
# /setup — creates (or reuses) the Feedback category + #bugs / #feedback /
# #features channels for this server, and a webhook for each channel.
# ---------------------------------------------------------------------------
@tree.command(name="setup", description="Set up this server's feedback channels (admin only)")
@admin_only()
async def setup_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    guild = interaction.guild
    if guild is None:
        await interaction.followup.send("This command must be run inside a server.")
        return

    db = SessionLocal()
    try:
        config = db.query(GuildConfig).filter(GuildConfig.guild_id == str(guild.id)).first()
        if config is None:
            config = GuildConfig(guild_id=str(guild.id))
            db.add(config)
            db.commit()
            db.refresh(config)

        category = None
        if config.category_id:
            category = guild.get_channel(int(config.category_id))
        if category is None:
            category = await guild.create_category("📥 FEEDBACK")
            config.category_id = str(category.id)

        channel_defs = [
            ("bugs_channel_id", "bugs_webhook_url", "bugs", "🐛"),
            ("feedback_channel_id", "feedback_webhook_url", "user-feedback", "🌱"),
            ("features_channel_id", "features_webhook_url", "feature-requests", "💡"),
        ]

        created = []
        for chan_field, webhook_field, chan_name, emoji in channel_defs:
            channel_id = getattr(config, chan_field)
            channel = guild.get_channel(int(channel_id)) if channel_id else None

            if channel is None:
                channel = await guild.create_text_channel(chan_name, category=category)
                setattr(config, chan_field, str(channel.id))
                created.append(f"{emoji} #{channel.name}")

            if not getattr(config, webhook_field):
                webhook = await channel.create_webhook(name="Feedback Bot")
                setattr(config, webhook_field, webhook.url)

        db.commit()

        summary = (
            f"✅ Feedback channels are ready under **{category.name}**:\n"
            f"🐛 <#{config.bugs_channel_id}>\n"
            f"🌱 <#{config.feedback_channel_id}>\n"
            f"💡 <#{config.features_channel_id}>\n\n"
            f"Next, register an app with `/register-app name:<YourAppName>` to get an API key."
        )
        await interaction.followup.send(summary)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# /register-app — creates a new app tied to this guild and issues an API key
# ---------------------------------------------------------------------------
@tree.command(name="register-app", description="Register a new app and get its feedback API key (admin only)")
@app_commands.describe(name="The app's display name, e.g. Saple")
@admin_only()
async def register_app_cmd(interaction: discord.Interaction, name: str):
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("This command must be run inside a server.", ephemeral=True)
        return

    db = SessionLocal()
    try:
        config = db.query(GuildConfig).filter(GuildConfig.guild_id == str(guild.id)).first()
        if config is None or not config.bugs_webhook_url:
            await interaction.response.send_message(
                "⚠️ Run `/setup` first so this server has feedback channels configured.", ephemeral=True
            )
            return

        new_app = App(name=name, guild_id=str(guild.id))
        db.add(new_app)
        db.commit()
        db.refresh(new_app)

        # Send the key ephemerally so it isn't posted publicly in the channel.
        await interaction.response.send_message(
            f"✅ Registered **{name}**.\n\n"
            f"API key (keep this secret, put it server-side only):\n"
            f"```\n{new_app.api_key}\n```\n"
            f"Have the app POST to `/api/v1/feedback` with header `X-API-Key: {new_app.api_key}`.",
            ephemeral=True,
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# /apps — list registered apps for this server
# ---------------------------------------------------------------------------
@tree.command(name="apps", description="List apps registered for this server (admin only)")
@admin_only()
async def apps_cmd(interaction: discord.Interaction):
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("This command must be run inside a server.", ephemeral=True)
        return

    db = SessionLocal()
    try:
        apps = db.query(App).filter(App.guild_id == str(guild.id)).all()
        if not apps:
            await interaction.response.send_message("No apps registered yet. Use `/register-app`.", ephemeral=True)
            return

        lines = [
            f"{'🟢' if a.active else '🔴'} **{a.name}** — id {a.id} — {'active' if a.active else 'revoked'}"
            for a in apps
        ]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# /revoke-app — deactivates an app's API key
# ---------------------------------------------------------------------------
@tree.command(name="revoke-app", description="Revoke an app's API key by its app id (admin only)")
@app_commands.describe(app_id="The numeric app id shown in /apps")
@admin_only()
async def revoke_app_cmd(interaction: discord.Interaction, app_id: int):
    db = SessionLocal()
    try:
        app_row = db.query(App).filter(App.id == app_id).first()
        if not app_row or app_row.guild_id != str(interaction.guild_id):
            await interaction.response.send_message("No app with that id in this server.", ephemeral=True)
            return
        app_row.active = False
        db.commit()
        await interaction.response.send_message(f"🔴 Revoked API key for **{app_row.name}**.", ephemeral=True)
    finally:
        db.close()


def run():
    if not settings.DISCORD_BOT_TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")
    bot.run(settings.DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    run()
