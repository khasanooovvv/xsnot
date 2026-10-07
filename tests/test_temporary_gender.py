import os
os.environ.setdefault('BOT_TOKEN', '123:test')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///:memory:')
import unittest
from fastapi import HTTPException
from pydantic import ValidationError
from app.miniapp import ProfileEdit, edit_profile

class TemporaryGenderTests(unittest.IsolatedAsyncioTestCase):
    def test_gender_validation(self):
        self.assertEqual(ProfileEdit(name='Test', gender='male').gender, 'male')
        self.assertEqual(ProfileEdit(name='Test', gender='female').gender, 'female')
        self.assertIsNone(ProfileEdit(name='Test').gender)
        with self.assertRaises(ValidationError):
            ProfileEdit(name='Test', gender='invalid')

    async def test_other_account_cannot_change_gender(self):
        with self.assertRaises(HTTPException) as caught:
            await edit_profile(ProfileEdit(name='Test', gender='male'), uid=1)
        self.assertEqual(caught.exception.status_code, 403)
