import base64
import io
from PIL import Image, ImageOps
import unittest
from datetime import date
from types import SimpleNamespace as Obj
from unittest.mock import AsyncMock
from test_chat_privacy import load_function
from test_roulette import HttpError, Session


class ProfileEditTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = Obj(display_name='Old', city='Toshkent', birth_date=date(2000,1,1), gender='male', gold_until='unchanged')
        self.session = Session(self.user)
        self.session.get = AsyncMock(return_value=self.user)
        self.ns = dict(HTTPException=HttpError, age_on=lambda d: 26 if d.year==2000 else 10,
                       SessionLocal=lambda:self.session, User=object, MiniAvatar=object,
                       profile=AsyncMock(return_value={'name':'New','avatar':None}), base64=base64, io=io, Image=Image, ImageOps=ImageOps)
        self.edit = load_function('app/miniapp.py', 'edit_profile', self.ns)
        self.body = Obj(name=' New ', city=' Samarqand ', birthday=date(2000,1,1), gender='female', avatar=None)

    async def test_save_only_editable_fields(self):
        await self.edit(self.body, 123)
        self.assertEqual((self.user.display_name,self.user.city,self.user.gender),('New','Samarqand','female'))
        self.assertEqual(self.user.gold_until,'unchanged')
        self.session.get.assert_awaited_once_with(object,123,with_for_update=True)
        self.session.commit.assert_awaited_once()

    async def test_whitespace_rejected(self):
        self.body.name='  '
        with self.assertRaises(HttpError): await self.edit(self.body,123)
        self.session.commit.assert_not_awaited()

    async def test_underage_rejected(self):
        self.body.birthday=date(2016,1,1)
        with self.assertRaises(HttpError): await self.edit(self.body,123)
        self.session.commit.assert_not_awaited()

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
