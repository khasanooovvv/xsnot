import unittest
from sqlalchemy import select
from tests import test_direct as fixtures
from app.models import User, UserUsername


class ProfileSaveTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.DirectTests.asyncSetUp
    asyncTearDown = fixtures.DirectTests.asyncTearDown

    async def test_save_username_list_and_reorder(self):
        for handles in [['sdsdsdsd', 'aliasone'], ['aliasone', 'sdsdsdsd']]:
            response = await self.client.post('/api/profile', json={
                'name': 'xss', 'app_username': handles[0], 'usernames': handles, 'bio': ''})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['usernames'], handles)
            async with self.sessions() as s:
                self.assertEqual((await s.get(User, 1)).app_username, handles[0])
                extras = (await s.scalars(select(UserUsername.username).where(
                    UserUsername.user_id == 1))).all()
                self.assertEqual(extras, handles[1:])
