# Universal Feedback Bot

A self-hosted feedback pipeline for any number of apps: your apps POST feedback
to a small FastAPI server, which files it into your Discord server as
🐛 bugs / 🌱 general feedback / 💡 feature requests — routed by **type**, not
by app (the app's name just shows up as a field inside the message).

```
Your App(s)  --HTTPS POST-->  FastAPI  --DB-->  SQLite
                                  |
                                  v
                          Discord Webhook
                                  |
                          #bugs / #user-feedback / #feature-requests
```

## 1. Create the Discord bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) → New Application.
2. Bot tab → Add Bot → copy the **Token**.
3. OAuth2 → URL Generator → scopes `bot` + `applications.commands` → permissions
   `Manage Channels`, `Manage Webhooks`, `Send Messages`. Use the generated URL
   to invite the bot to your server.

## 2. Configure

```bash
cp .env.example .env
```

Fill in:
- `DISCORD_BOT_TOKEN` — from step 1
- `ADMIN_DISCORD_IDS` — your Discord user ID(s), comma-separated. Only these
  users can run `/setup`, `/register-app`, `/apps`, `/revoke-app`. Leave blank
  during local testing to allow anyone (not recommended for production).

## 3. Run it

### Locally
```bash
pip install -r requirements.txt
python run_bot.py     # in one terminal
python run_api.py     # in another
```

### With Docker
```bash
docker compose up -d --build
```

Both the API and the bot read/write the same `feedback.db` SQLite file, so
run them on the same host (or point `DATABASE_URL` at Postgres and run them
anywhere).

## 4. Set up your server

In your Discord server, run:

```
/setup
```

This creates a **📥 FEEDBACK** category with `#bugs`, `#user-feedback`, and
`#feature-requests`, and a webhook behind each one.

## 5. Register an app

```
/register-app name:Saple
```

The bot replies (privately) with an API key like `fb_XXXXXXXXXXXXXXXX`. Keep
it on your backend only — **never** ship it inside a mobile app or website
bundle, since it could be extracted and used to spam your Discord. If you're
submitting feedback from a client app, proxy the request through your own
backend rather than calling this API directly from the client.

Manage apps with `/apps` (list) and `/revoke-app app_id:<id>` (disable a key).

## 6. Submit feedback

```
POST /api/v1/feedback
Header: X-API-Key: fb_XXXXXXXXXXXXXXXX
Content-Type: application/json

{
  "type": "feature",
  "message": "Add a home screen widget",
  "app_version": "1.0.3",
  "platform": "android",
  "device": "Pixel 8",
  "language": "en-IN",
  "user_id": "anonymous_8f3a"
}
```

`type` must be one of `bug`, `feedback`, `feature`. Every field except `type`
and `message` is optional. Response:

```json
{ "success": true, "message": "Feedback received" }
```

A basic per-API-key rate limit (`RATE_LIMIT_PER_MINUTE`, default 10/min) is
built in. Feedback is always saved to the database even if the Discord post
fails, so nothing is lost during a Discord outage.

## Adding a second, third, tenth app

Just run `/register-app` again with a new name — no new channels, no new
setup. Every app in the server shares the same `#bugs` / `#user-feedback` /
`#feature-requests` channels; each message's **📦 App** field shows which app
it came from.

## Multiple Discord servers

`/setup` is per-server, so you *can* run this bot in more than one server
(e.g. separate servers for separate teams/clients) — each gets its own three
channels, and apps registered with `/register-app` in that server post only
to that server's channels.

## Project layout

```
feedback-bot/
├── app/
│   ├── main.py              FastAPI app + startup
│   ├── config.py             env settings
│   ├── database.py            SQLAlchemy engine/session (shared with the bot)
│   ├── models.py               GuildConfig, App, Feedback
│   ├── schemas.py               request/response models
│   ├── security.py              API-key auth + rate limiting
│   ├── routes/feedback.py        POST /api/v1/feedback
│   └── services/discord_notify.py  posts the embed to the right webhook
├── bot/bot.py                 slash commands: /setup /register-app /apps /revoke-app
├── run_api.py / run_bot.py     entrypoints
├── Dockerfile / docker-compose.yml
└── .env.example
```

## Notes / next steps

- **Not built yet, on purpose (MVP):** an admin web dashboard. It wasn't asked
  for — everything currently lives in Discord itself. Since it reads the same
  SQLite/Postgres database, a `/admin` dashboard can be bolted on later
  without touching how apps submit feedback.
- Swap `DATABASE_URL` to Postgres for production (`postgresql://...`) — no
  code changes needed, SQLAlchemy handles both.
- The in-memory rate limiter resets if the API process restarts and doesn't
  work across multiple API instances — fine for a single VPS, swap for Redis
  if you ever run more than one API replica.
# product-feedback-collection-discord-bot
