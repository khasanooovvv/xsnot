import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace as Obj
from unittest.mock import AsyncMock, Mock
from test_chat_privacy import load_function, Query


class HttpError(Exception):
    def __init__(self, status, detail):
        self.status_code = status
        self.detail = detail


class SearchQuotaTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_checks_and_consumes_daily_quota(self):
        for limit in (10, 15, 20, 100):
            for exhausted in (False, True):
                with self.subTest(limit=limit, exhausted=exhausted):
                    usage = Obj(count=limit if exhausted else limit - 1)
                    session = Obj(execute=AsyncMock(), commit=AsyncMock(),
                                  get=AsyncMock(return_value=Obj(archive_consent_at=True)),
                                  scalar=AsyncMock(return_value=usage), add=Mock())
                    class Context:
                        async def __aenter__(self): return session
                        async def __aexit__(self, *args): pass
                    class SearchQuery(Query):
                        def __lt__(self, other): return self
                    query = SearchQuery()
                    queue = Obj(mode=Obj(in_=lambda values: query), queued_at=query)
                    ns = dict(SessionLocal=Context, sql=lambda value: value, User=object,
                              settings=lambda: Obj(archive_channel_id=None), datetime=datetime,
                              UTC=UTC, timedelta=timedelta, delete=lambda model: query,
                              MatchQueue=queue, active_match=AsyncMock(return_value=None),
                              find_or_queue=AsyncMock(), select=lambda model: query,
                              RouletteUsage=Obj(user_id=query, usage_day=query),
                              limits=lambda user: {'roulette': limit}, HTTPException=HttpError)
                    search = load_function('app/miniapp.py', 'search', ns)
                    body = Obj(roulette=True, mode='open', archive_consent=False)
                    if exhausted:
                        with self.assertRaises(HttpError) as caught:
                            await search(body, 1)
                        self.assertEqual(caught.exception.status_code, 429)
                        ns['find_or_queue'].assert_not_awaited()
                        session.commit.assert_not_awaited()
                    else:
                        self.assertEqual(await search(body, 1), {'ok': True})
                        self.assertEqual(usage.count, limit)
                        ns['find_or_queue'].assert_awaited_once()
