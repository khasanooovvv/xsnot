import ast
from pathlib import Path
from types import SimpleNamespace as Obj
import unittest
from unittest.mock import AsyncMock

class Session:
    bind=Obj(dialect=Obj(name='sqlite'))
    def __init__(self): self.users={7:Obj(telegram_id=7)}
    async def get(self, model, uid): return self.users.get(uid)
    async def scalar(self, query): return None
    def add(self,user): self.users[user.telegram_id]=user
    async def flush(self): pass

class ReferralStartTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        tree=ast.parse(Path('app/services/users.py').read_text(encoding='utf-8'))
        fn=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='get_or_create')
        for arg in fn.args.args: arg.annotation=None
        class Query:
            def where(self, *args): return self
        class UserModel:
            def __init__(self, **kwargs):
                kwargs.setdefault('is_registered', False)
                self.__dict__.update(kwargs)
        scope={'User':UserModel, 'ReferralHistory':Obj(id=Obj(), referred_id=Obj()), 'select':lambda *args: Query()};exec(compile(ast.Module(body=[fn],type_ignores=[]),'<actual get_or_create>','exec'),scope)
        self.create=scope['get_or_create'];self.session=Session()

    async def test_only_first_valid_invite_triggers_notification(self):
        u=await self.create(self.session,99,'tester','Test',7)
        self.assertTrue(u._new_referral);self.assertEqual(u.referred_by_id,7)
        u=await self.create(self.session,99,'tester','Test',7)
        self.assertFalse(u._new_referral);self.assertEqual(u.referred_by_id,7)

    async def test_invalid_self_or_existing_users_do_not_count(self):
        for ref in (99,123456,None,2**64,-1):
            session=Session();u=await self.create(session,99,'test','Test',ref)
            self.assertFalse(u._new_referral)
        u=await self.create(self.session,99,'test','Test',None)
        u=await self.create(self.session,99,'test','Test',7)
        self.assertFalse(u._new_referral);self.assertIsNone(u.referred_by_id)

    async def test_start_calls_notification_after_commit(self):
        tree=ast.parse(Path('app/bot.py').read_text(encoding='utf-8'))
        fn=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='start')
        fn.decorator_list=[]
        for arg in fn.args.args:arg.annotation=None
        events=[]
        class Context:
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            async def get(self,*args):return Obj(telegram_id=7,language='uz')
            async def commit(self):events.append('commit')
        async def notify(*args, **kwargs):events.append('notify')
        user=Obj(is_registered=False,_new_referral=True,referred_by_id=7,display_name='Test')
        scope=dict(SessionLocal=Context,get_or_create=AsyncMock(return_value=user),User=Obj,send_referral_started=notify,cfg=Obj(webapp_url='https://example.com'),language_menu=lambda:None)
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'<actual start>','exec'),scope)
        await scope['start'](Obj(text='/start ref_7',from_user=Obj(id=99,username='test',full_name='Test'),bot=Obj(),answer=AsyncMock()),Obj(clear=AsyncMock()))
        self.assertEqual(events,['commit','notify'])
