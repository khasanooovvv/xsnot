# Private chat backend (stage 3)

All `/api/direct` routes require the existing Telegram authentication header and a registered, non-banned user. Roulette endpoints and UI are unchanged.

New tables are registered by `app.database` and created idempotently by the existing startup `init_db` migration under its PostgreSQL advisory lock. No existing chat data is transformed or removed. Private messages do not enter the roulette archive cleanup.

## Frontend contract for stage 4

- `POST /api/direct/chats/with/{user_id}` opens/reuses one conversation per pair.
- `GET /api/direct/chats?offset=0` returns 50 rows, newest activity first, with partner, last message and unread count.
- `GET /api/direct/chats/{id}/messages` returns the latest 100 messages in ascending order; `before_id` loads older history.
- Poll `GET /api/direct/chats/{id}/messages?since_revision=N` approximately every second while visible. Apply messages by ID, including edit/deletion flags; store returned revision. When `more=true`, drain changes immediately. History-page revisions must not replace the active polling cursor.
- `POST /api/direct/chats/{id}/messages` with `text` sends; `PATCH .../messages/{message_id}` edits; `DELETE .../messages/{message_id}` replaces the content with a tombstone for both sides. Only the author may mutate a message. Edits do not reorder the chat list.
- `POST /api/direct/chats/{id}/read` with `message_id` marks through the last displayed message. Reading a list or polling alone never marks messages read.
- `DELETE /api/direct/chats/{id}` hides only the caller's list row. History is retained. A new message restores visibility for both participants; editing an old message does not.
- `POST /api/direct/presence` with `online:true` every 10 seconds while the app is visible. Best-effort `online:false` on hide. Heartbeats expire after 30 seconds. This represents app activity, not Telegram account presence.
- `POST /api/direct/blocks/{user_id}`, `DELETE /api/direct/blocks/{user_id}`, `GET /api/direct/blocks` manage the caller's block list. Either side's block prevents both sending and editing. The blocked user cannot find the blocker by primary or additional username. Existing history remains accessible so unblocking remains possible.

Stage 4 connects the isolated `direct.js` / `direct.css` interface to search results and the first tab. Production PostgreSQL concurrency and two-device delivery require a deployment test; local integration tests use isolated SQLite. The browser interaction test uses a mocked API and Microsoft Edge (`node tests/test_direct_browser.cjs`).

Run tests: `python -m pip install -r requirements-test.txt`, then `python -m unittest tests.test_direct -v`.
