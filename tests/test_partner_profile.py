import unittest
from types import SimpleNamespace as Obj
from unittest.mock import AsyncMock
from test_chat_privacy import load_function
from test_roulette import HttpError, Session


class PartnerProfileTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.session = Session(Obj(is_registered=True,is_banned=False))
        self.session.get = AsyncMock(return_value=self.session.own)
        self.match = Obj(id=5,user_one_id=10,user_two_id=20,mode='mini_oo')
        self.public = dict(name='Partner',avatar=None,app_username='partner',bio='Hello',age=25,city='Toshkent',verified=False,silver=False,gold=0)
        self.ns = dict(SessionLocal=lambda:self.session, User=object, HTTPException=HttpError,
                       active_match=AsyncMock(return_value=self.match),is_anonymous=lambda m,uid:False,
                       profile=AsyncMock(return_value={**self.public,'id':20,'username':'private_telegram','birthday':'2000-01-01','referrals':42}))
        self.fetch = load_function('app/miniapp.py','partner_profile',self.ns)

    async def test_only_public_fields_and_correct_partner(self):
        result=await self.fetch(5,10)
        self.assertEqual(result,{'match':5,'partner':{**self.public,'anonymous':False}})
        self.session.get.assert_awaited_once_with(object,20)

    async def test_other_participant_sees_opposite_profile(self):
        await self.fetch(5,20)
        self.session.get.assert_awaited_once_with(object,10)

    async def test_anonymous_profile_never_loaded(self):
        self.ns['is_anonymous']=lambda m,uid:True
        result=await self.fetch(5,10)
        self.assertEqual(result['partner'],{'name':'Anonim','avatar':None,'anonymous':True})
        self.ns['profile'].assert_not_awaited()
        self.session.get.assert_not_awaited()

    async def test_wrong_match_rejected(self):
        with self.assertRaises(HttpError): await self.fetch(99,10)
        self.ns['profile'].assert_not_awaited()

    async def test_ended_chat_rejected(self):
        self.ns['active_match'].return_value=None
        with self.assertRaises(HttpError): await self.fetch(5,10)

    async def test_banned_profile_rejected(self):
        self.session.own.is_banned=True
        with self.assertRaises(HttpError): await self.fetch(5,10)
