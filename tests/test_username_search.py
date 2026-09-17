import unittest
from datetime import datetime, UTC, timedelta
from unittest.mock import patch
from tests import test_direct as fixtures
from app.models import User, UserUsername
from app import miniapp

class SearchTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.DirectTests.asyncSetUp
    asyncTearDown = fixtures.DirectTests.asyncTearDown

    async def test_visibility_matrix_and_no_mutations(self):
        now = datetime.now(UTC)
        async with self.sessions() as s:
            s.add_all([
                User(telegram_id=10, display_name='Ordinary', app_username='ordinary', is_registered=True),
                User(telegram_id=11, display_name='Active hidden', gold_until=now+timedelta(days=5), gold_hidden_username='alive', gold_hidden_username_until=now-timedelta(days=1), is_registered=True),
                User(telegram_id=12, display_name='Former owner', gold_until=now-timedelta(days=5), gold_hidden_username='taken', gold_hidden_username_until=now-timedelta(days=2), is_registered=True),
                User(telegram_id=13, display_name='New owner', app_username='taken', is_registered=True),
                User(telegram_id=14, display_name='Available', gold_until=now-timedelta(days=5), gold_hidden_username='freed', gold_hidden_username_until=now-timedelta(days=2), is_registered=True),
                User(telegram_id=15, display_name='Reserved', gold_until=now-timedelta(days=1), gold_hidden_username='heldx', gold_hidden_username_until=now+timedelta(days=2), is_registered=True),
            ])
            s.add(UserUsername(user_id=10, username='ordinary_alias', position=1))
            await s.commit()
        with patch.object(miniapp, 'normalize_gold_usernames', side_effect=AssertionError('Search must not mutate usernames')):
            for query, expected in [('ordinary',[10]),('ordinary_alias',[10]),('alive',[11]),('taken',[13]),('freed',[]),('heldx',[15]),('@ORDINARY',[10])]:
                with self.subTest(query=query):
                    response=await self.client.get('/api/users/search',params={'q':query})
                    self.assertEqual(response.status_code,200,response.text)
                    self.assertEqual([r['id'] for r in response.json()],expected)
                    if expected:
                        self.assertEqual(response.json()[0]['app_username'],query.lstrip('@').lower())
        async with self.sessions() as s:
            self.assertEqual((await s.get(User,14)).gold_hidden_username,'freed')
            self.assertIsNone((await s.get(User,11)).app_username)

    async def test_hidden_additional_names(self):
        now=datetime.now(UTC)
        async with self.sessions() as s:
            user=await s.get(User,2)
            user.gold_until=now-timedelta(days=5)
            s.add_all([
                UserUsername(user_id=2,username='hidden_free',position=1,hidden_until=now-timedelta(days=1)),
                UserUsername(user_id=2,username='hidden_reserved',position=2,hidden_until=now+timedelta(days=1)),
                UserUsername(user_id=2,username='normal_extra',position=3),
            ])
            await s.commit()
        for name,expected in [('hidden_free',[]),('hidden_reserved',[2]),('normal_extra',[2])]:
            response=await self.client.get('/api/users/search',params={'q':name})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual([r['id'] for r in response.json()],expected)
