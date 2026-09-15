import base64
import io
import re
from PIL import Image, ImageOps
import unittest
from datetime import date
from types import SimpleNamespace as Obj
from unittest.mock import AsyncMock
from test_chat_privacy import load_function, Query
from test_roulette import HttpError, Session


class ProfileEditTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = Obj(display_name='Old', username='telegram_name', app_username=None, bio='', city='Toshkent', birth_date=date(2000,1,1), gender='male', gold_until='unchanged')
        self.session = Session(self.user)
        self.session.get = AsyncMock(return_value=self.user)
        self.session.scalar = AsyncMock(return_value=None)
        self.ns = dict(HTTPException=HttpError, re=re, sql=lambda s:s, select=lambda *args:Query(),
                       SessionLocal=lambda:self.session, User=Obj(telegram_id=Query(),app_username=Query()), MiniAvatar=object,
                       profile=AsyncMock(return_value={'name':'New','avatar':None}), base64=base64, io=io, Image=Image, ImageOps=ImageOps)
        self.edit = load_function('app/miniapp.py', 'edit_profile', self.ns)
        self.body = Obj(name=' New ', app_username='@New_User', bio=' Hello! ', avatar=None)

    async def test_save_only_editable_fields(self):
        await self.edit(self.body, 123)
        self.assertEqual((self.user.display_name,self.user.app_username,self.user.bio),('New','new_user','Hello!'))
        self.assertEqual((self.user.city,self.user.gender,self.user.birth_date),('Toshkent','male',date(2000,1,1)))
        self.assertEqual(self.user.username,'telegram_name')
        self.assertEqual(self.user.gold_until,'unchanged')
        self.session.get.assert_awaited_once_with(self.ns['User'],123,with_for_update=True)
        self.session.commit.assert_awaited_once()

    async def test_whitespace_rejected(self):
        self.body.name='  '
        with self.assertRaises(HttpError): await self.edit(self.body,123)
        self.session.commit.assert_not_awaited()

    async def test_invalid_username_rejected(self):
        self.body.app_username='no spaces!'
        with self.assertRaises(HttpError): await self.edit(self.body,123)
        self.session.commit.assert_not_awaited()

    async def test_taken_username_rejected_without_changes(self):
        self.session.scalar.return_value=456
        with self.assertRaises(HttpError) as error: await self.edit(self.body,123)
        self.assertEqual(error.exception.status_code,409)
        self.assertEqual(self.user.display_name,'Old')
        self.session.commit.assert_not_awaited()

    async def test_own_username_can_be_kept(self):
        self.session.scalar.return_value=123
        await self.edit(self.body,123)
        self.session.commit.assert_awaited_once()

    async def test_blank_fields_clear_bio_and_username(self):
        self.body.app_username=''
        self.body.bio=''
        await self.edit(self.body,123)
        self.assertIsNone(self.user.app_username)
        self.assertEqual(self.user.bio,'')

    async def test_invalid_avatar_does_not_partially_save(self):
        self.body.avatar='invalid'
        with self.assertRaises(HttpError): await self.edit(self.body,123)
        self.session.commit.assert_not_awaited()
        self.assertEqual(self.user.display_name,'Old')

    async def test_photo_is_saved_as_normalized_square(self):
        output=io.BytesIO()
        Image.new('RGB',(20,10)).save(output,format='PNG')
        self.body.avatar='data:image/png;base64,'+base64.b64encode(output.getvalue()).decode()
        avatar=Obj(data='old-photo')
        self.session.get.side_effect=[self.user,avatar]
        await self.edit(self.body,123)
        with Image.open(io.BytesIO(base64.b64decode(avatar.data.split(',')[1]))) as image:
            self.assertEqual(image.size,(512,512))
            self.assertEqual(image.format,'JPEG')
        self.session.commit.assert_awaited_once()
