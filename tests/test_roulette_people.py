import unittest
from datetime import UTC, datetime, timedelta
from tests import test_direct as fixtures
from app.models import MatchQueue


class RoulettePeopleTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.DirectTests.asyncSetUp
    asyncTearDown = fixtures.DirectTests.asyncTearDown

    async def test_only_recent_open_searchers_are_previewed(self):
        async with self.sessions() as s:
            s.add(MatchQueue(user_id=2, mode='mini_open', queued_at=datetime.now(UTC)-timedelta(minutes=2)))
            s.add(MatchQueue(user_id=3, mode='mini_anonymous', queued_at=datetime.now(UTC)))
            await s.commit()
        response=await self.client.get('/api/roulette/people')
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json(),[])
        async with self.sessions() as s:
            (await s.get(MatchQueue,2)).queued_at=datetime.now(UTC)
            await s.commit()
        response=await self.client.get('/api/roulette/people')
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual([row['id'] for row in response.json()],[2])
