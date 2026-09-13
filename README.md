# PVP Chat — Telegram random chat bot

18+ Telegram random-chat bot with Uzbek, Russian, and English language selection; anonymous/open modes, match filters, profile onboarding, referral rewards, Premium/Gold countdowns, moderation reports, and a protected admin dashboard.

## Launch

1. Copy `.env.example` as `.env` and set a real `BOT_TOKEN`, a public bot username, and a strong admin password.
2. Start the services with `docker compose up --build`.
3. Open `http://localhost:8000` for the admin dashboard (HTTP Basic login from `.env`).

If you previously started the bot with an older database, add the `language` column through a database migration before deploying this update. A brand-new database gets it automatically.

## Railway

The Docker image starts the FastAPI dashboard on Railway's `PORT` and launches
Telegram polling from the dashboard startup hook. Deploy this repository as one
service, set the environment variables from `.env.example`, and use the
Postgres service's values for `DATABASE_URL`. The public Railway domain now
responds with the password-protected admin dashboard instead of an application
failure page.

## Product rules implemented

- A user accepts safety/privacy terms, provides date of birth (18+), city, and optional photo before accessing chat. A default avatar is used when the photo is skipped.
- Random matching supports anonymous and visible-profile modes, city and age filters, reciprocal filter checking, a VS reveal, leave/next/report controls, and media-safe `copy_message` relay (the partner does not receive the sender identity in anonymous mode).
- A referral only counts after the invited person completes registration; it cannot be replayed. At exactly 5 completed referrals, 30 days Premium is granted; at 50, 30 days Gold is granted. Referral-link sharing is limited to 15 requests per user per day while lifetime referral rewards still remain attainable.
- Profile displays Premium and Gold days remaining. The leaderboard reports Top 10 referrers. `POST /leaderboard/reward` gives all current Top 10 the monthly 30-day Gold award.
- Admin capabilities: verify checkmark, grant Premium/Gold, ban/unban, inspect users and reports. Protect the dashboard in production behind HTTPS and a stronger identity provider.

## Important production checklist

- Use a managed PostgreSQL database, Redis queue/locks for multiple bot replicas, migrations (Alembic), structured audit logs, backups, rate limits, and monitoring.
- Store the terms acceptance version and timestamp (already modelled). Have Uzbek legal counsel write/review the final Uzbek offer, privacy policy, data-retention schedule, and moderation/escalation process. A checkbox is not a substitute for criminal-law procedure.
- Add automated content/rate-abuse controls and an admin review workflow before public release.
