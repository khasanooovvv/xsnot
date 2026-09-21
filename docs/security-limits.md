# API protection

These controls run before database access and before reading API upload bodies.
Authentication and chat membership checks still run in the existing endpoints.

## Per verified Telegram account

Limits use rolling windows, shared by all tabs and chat IDs, with no badge exemptions.

| Operation | Limit |
|---|---|
| All API calls combined | 30 / 2 seconds and 900 / minute |
| Send text (anonymous and direct combined) | 10 / 5 seconds and 60 / minute |
| Send image | 6 / minute |
| Prepare photo | 6 / minute |
| Username search | 60 / minute |
| Match search / roulette spin combined | 20 / minute |
| Open direct chat | 20 / minute |
| Save profile / register | 10 / minute |
| Verification video | 3 / 5 minutes |
| Presence / read receipts combined | 180 / minute |
| Read API | 600 / minute per normalized endpoint |
| Other writes combined | 60 / minute |
| Parallel uploads / profile submissions | 2 |

Invalid Telegram authentication: 30 failures per minute per IP, then 5-minute cooldown
on invalid requests. Valid signed requests can still proceed from that shared IP.
Admin authentication: 10 failures in 15 minutes, then 15-minute IP cooldown across
all admin routes, including `/users/*`, `/reports` and `/leaderboard/reward`.
No blanket low IP ceiling is imposed on legitimate mobile carrier users.

## Resources and responses

- Text request bodies: 64 KiB. Profile/register JSON: 3 MiB, avatar field: 2,000,000 characters.
- Multipart transport caps include overhead: photo preparation 21 MiB, chat image 11 MiB,
  verification video 16 MiB. Actual file limits remain 20 / 10 / 15 MiB respectively.
- Image pixel cap: 40 million. Registration crop exports JPEG at up to 1024 x 1024.
- Prepared photos are resized to fit 2048 x 2048; stored registration avatars to 1024 x 1024.
- SECURITY_MAX_UPLOADS=4 bounds concurrent heavy requests per process in addition to the
  per-account limit of 2; excess requests receive 503 with a short retry delay.
- Body limits count actual streamed bytes, including requests without Content-Length.
- Requests: 15 seconds, or 60 seconds for uploads/profile submissions, including body receipt.
- Database statement timeout: 5 seconds; schema initialization exempt. This also affects
  bot/admin queries on the shared engine. Increase DB_STATEMENT_TIMEOUT_MS if measured
  legitimate queries require it; tune expensive queries rather than disabling globally.
- SECURITY_MAX_CONCURRENT=100 bounds active protected requests per process, returning 503
  with Retry-After: 3 when full. This is a starting value, not a measured capacity claim.
- Rate limits return 429 with Retry-After and X-RateLimit-Scope. The web client observes
  cooldowns and never automatically resends writes. Anonymous chat polls every second.
- A timeout is not proof that a write failed: refresh state before manually resending.

## Deployment and limitations

Set REDIS_URL to a reachable private Redis instance. Lua operations atomically enforce
shared rolling windows and upload leases. Redis errors emit warnings and temporarily
use bounded per-process memory for 30 seconds. During an outage/restart these local
limits are weaker and are not shared across replicas. Upload Redis leases expire after
120 seconds to recover from worker crashes. Monitor Redis availability and 429/503 rates.

Docker Compose binds database/Redis host ports to loopback; admin connects to Redis over
the private Compose network. Keep Redis and Postgres inaccessible from the public internet.

Railway documents `X-Real-IP` as the remote client IP:
https://docs.railway.com/networking/public-networking/specs-and-limits
When Railway supplies RAILWAY_ENVIRONMENT_ID, the app accepts exactly one valid X-Real-IP
only from an exact peer in SECURITY_TRUSTED_PROXY_IPS. Defaults are the explicit peers
observed in this deployment's access logs, not an official Railway IP range. Other
peers, missing/duplicate/malformed headers fall back to the socket peer. IPv6 and mapped
IPv4 addresses are normalized. X-Forwarded-For and client-supplied Railway markers do
not establish trust. Outside Railway, forwarded client IP headers are ignored.

Docker and Compose start Uvicorn with --no-proxy-headers: this is required to preserve
the original socket peer. Keep that flag in any custom start command; do not replace
it with FORWARDED_ALLOW_IPS=*. Private-service peers must not be added to the trusted
list. The deployment relies on Railway replacing X-Real-IP at its edge. Verify that
assumption with an external forged-header probe after deploy. New Railway proxy peers
must be verified and added explicitly; an unlisted peer fails closed to socket identity,
which can weaken per-client limiting and group unrelated clients. No broad private or
carrier-grade NAT range is implicitly trusted.

Cloudflare/WAF, origin firewall restrictions, external attack alerts, and load testing
are deployment tasks: they are NOT configured by these code changes. Origin-specific
configuration requires the actual domain and hosting access. Application limits cannot
stop a bandwidth-saturating DDoS. Static files are outside account limits; serve them
through an edge cache, never cache authenticated API responses publicly.
