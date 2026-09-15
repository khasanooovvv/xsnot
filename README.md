# PVP Chat — Telegram random chat bot

18+ Telegram random-chat bot with Uzbek, Russian, and English language selection; anonymous/open modes, match filters, profile onboarding, referral rewards, Silver/Gold countdowns, moderation reports, and a protected admin dashboard.

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
- A referral only counts after the invited person completes registration; it cannot be replayed. At exactly 5 completed referrals, 30 days Silver is granted; at 50, 30 days Gold is granted. Referral-link sharing is limited to 15 requests per user per day while lifetime referral rewards still remain attainable.
- Profile displays Silver and Gold days remaining. The leaderboard reports Top 10 referrers. `POST /leaderboard/reward` gives all current Top 10 the monthly 30-day Gold award.
- Admin capabilities: verify checkmark, grant Silver/Gold, ban/unban, inspect users and reports. Protect the dashboard in production behind HTTPS and a stronger identity provider.

## Important production checklist

- Use a managed PostgreSQL database, Redis queue/locks for multiple bot replicas, migrations (Alembic), structured audit logs, backups, rate limits, and monitoring.
- Store the terms acceptance version and timestamp (already modelled). Have Uzbek legal counsel write/review the final Uzbek offer, privacy policy, data-retention schedule, and moderation/escalation process. A checkbox is not a substitute for criminal-law procedure.
- Add automated content/rate-abuse controls and an admin review workflow before public release.

## Telegram Mini App

The public `/` route now serves the Mini App. `/admin` remains the protected administrator dashboard.
Set `MINI_APP_URL` to the deployed HTTPS origin (or use Railway's `RAILWAY_PUBLIC_DOMAIN`). Restart/redeploy the service; `/start` and the bot menu then open the Mini App. If BotFather already has a Main Mini App URL, point it to the same origin.

The app validates Telegram initData on every API request. It includes registration with optional photo, age/city filters, anonymous/open matching, VS reveal, text messaging, reports, profile reward countdowns, referrals, and leaderboard. New avatar/message tables are created at startup; existing User table migrations still apply. Mini App queues are separate from legacy bot queues. PostgreSQL advisory locks serialize Mini App matching and referral awards. Waiting clients expire after 30 seconds without polling. Anonymous responses omit partner identity and photo.

Deploy before testing in Telegram: local source changes do not update Railway automatically. Test with two separate Telegram accounts, including anonymous identity hiding, stop/next, and report handling. The current Mini App supports text messages; media messaging remains in the legacy bot. The existing admin dashboard uses its protected API for moderation and grants.

### Telegram ID overflow fix

Telegram identity columns use BIGINT. On startup, PostgreSQL deployments upgrade existing INTEGER identity columns and all application references in one transaction, preserving rows and constraints. An advisory lock serializes concurrent startup upgrades; already upgraded columns are skipped. Deploy this version to apply the upgrade before bot polling starts. Table locks may briefly delay requests during the first upgrade.

## Silver, Gold and verification

Silver replaces the public Premium name. Existing `premium_until` data and referral thresholds are retained, so current subscriptions keep their expiry dates. Admin grants accept `silver` (the old `premium` API value remains compatible). Gold takes precedence over Silver beside a name; the administrator's blue verification seal is independent. Badges appear beside names in profiles, open chats, the leaderboard and admin users. Anonymous partners expose no badges. Public screens contain no blue-verification application or instructions; only the protected admin verification endpoint can change it.

Checks: `python -m unittest discover -s tests -v`, `node tests/test_badges.cjs`, `node tests/test_admin_frontend.cjs`, `node tests/test_mini_frontend.cjs`.

## Human video verification (current Silver policy)

Silver now requires administrator video approval and has no expiry. Registration or the old 5-referral reward does not grant Silver. Legacy subscription dates remain stored but no longer award a Silver badge. Gold referral rewards and admin-only blue verification remain separate. Approved Silver users can request 30 referral links daily; others get 15 (configurable).

Users consent and directly upload a short MP4/WebM video (15 MB maximum); administrators compare the visible face and profile photo where available. This is human review, not automated inference of sex or gender. The pending video is stored in PostgreSQL and served only behind admin authentication, with no-store caching. Approval grants Silver, rejection allows resubmission; both delete the video bytes while retaining the decision and consent timestamps. Pending submissions remain until reviewed. The video container signature is checked; administrators must reject unplayable or unsuitable content.

Startup creates the submissions table and adds `users.silver_verified` if absent. Deploy before using the new screens. Gold can be revoked independently from the protected admin panel. Full PostgreSQL and Telegram end-to-end tests are still required in the deployment environment.

## Private archive channel

`ARCHIVE_CHANNEL_ID=-1004388937618` selects the archive channel. Give this bot channel administrator permission to post messages and files. An explicitly empty value disables new archive jobs. No old conversations or verification videos are backfilled: updated chat and video consent must be accepted before a new item is archived. Anonymous chat identity is hidden from the partner, but disclosed to archive administrators; the updated consent explicitly explains this.

When a Mini App chat ends (Stop, Next, report, or account deletion), a ZIP contains `chat.txt` and `messages.jsonl`, both participant display names, their @username or Telegram ID, and ordered messages. Very long chats are split into numbered ZIP parts. Message IDs preserve order; historical messages have no individual timestamps, so the archive only gives session start/end timestamps. MP4 verification recordings are sent as videos with the submitter's identity in the caption. WebM recordings are sent as original document attachments, which Telegram supports without lossy conversion.

The transaction saves an archive outbox job before completing the operation. A background worker uploads it and retries temporary failures with backoff. After every chat part is delivered, the ZIP outbox rows and source `mini_messages` are deleted; after a verification upload succeeds, its temporary archive outbox row and payload are deleted. A crash after Telegram accepted a file but before the database commit can produce a duplicate; the event and part identifiers identify it. No exactly-once guarantee is claimed. Delivery failures log only event IDs and exception types, not private content or credentials.

Review removes the verification bytes from the review table, while the channel archive remains until an administrator manually deletes it. Account deletion does not remove channel copies or already queued archive deliveries. This retention behavior is disclosed before chat, video submission, and account deletion. Only authorized admins should have access to the private channel.

Run `python -m unittest tests.test_archive -v` in an environment with the project dependencies and `aiosqlite` installed. Tests use synthetic users and mock Telegram delivery; they never publish real data.
