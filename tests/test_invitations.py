"""Exercise real invitation queries on SQLite, emulating the PostgreSQL transaction lock."""
import asyncio
import hashlib
import hmac
import secrets
import time
import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace as Obj
from test_chat_privacy import load_function
from test_roulette import HttpError

try:
    from sqlalchemy import create_engine, delete, or_, select, text
    from sqlalchemy.orm import Session
    from app.models import Base, ChatInvitation, Match, MatchQueue, User
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, 'SQLAlchemy required for database integration tests')
class InvitationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_engine('sqlite://')
        Base.metadata.create_all(self.engine)
        self.lock = asyncio.Lock()
        engine, lock = self.engine, self.lock

        def utc(row):
            for name in ('queued_at', 'expires_at'):
                value = getattr(row, name, None)
                if value is not None and value.tzinfo is None:
                    setattr(row, name, value.replace(tzinfo=UTC))
            return row

        class Adapter:
            def __init__(self):
                self.db = Session(engine, expire_on_commit=False)
                self.locked = False
            async def __aenter__(self): return self
            async def __aexit__(self, *args):
                self.db.close()
                if self.locked: lock.release()
            async def execute(self, query):
                if 'pg_advisory_xact_lock' in str(query):
                    await lock.acquire()
                    self.locked = True
                else: return self.db.execute(query)
            async def get(self, model, key): return utc(self.db.get(model,key))
            async def scalar(self, query): return utc(self.db.scalar(query))
            async def scalars(self, query):
                rows=[utc(row) for row in self.db.scalars(query).all()]
                return Obj(all=lambda:rows)
            async def delete(self, row): self.db.delete(row)
            async def commit(self): self.db.commit()
            def add(self, row): self.db.add(row)

        async def profile(session,user,**kwargs): return {'name':user.display_name,'avatar':None}
        self.ns = dict(datetime=datetime,UTC=UTC,timedelta=timedelta,time=time,hmac=hmac,hashlib=hashlib,secrets=secrets,
                       select=select,delete=delete,or_=or_,sql=text,Match=Match,MatchQueue=MatchQueue,User=User,
                       ChatInvitation=ChatInvitation,SessionLocal=Adapter,HTTPException=HttpError,profile=profile,
                       settings=lambda:Obj(bot_token='test-key',archive_channel_id=123))
        for name in ('active_match','leave_queue'):
            load_function('app/services/matching.py',name,self.ns)
        for name in ('roulette_ticket','pending_invitation','invitation_payload','roulette_candidates','roulette_spin','roulette_choose','respond_invitation'):
            load_function('app/miniapp.py',name,self.ns)
        with Session(engine) as s:
            s.add_all([User(telegram_id=i,display_name=f'User {i}',is_registered=True) for i in (1,2,3,4)])
            s.flush()
            s.add_all([MatchQueue(user_id=i,mode='mini_ra' if i==2 else 'mini_ro',archive_consent=True,queued_at=datetime.now(UTC)) for i in (1,2,3,4)])
            s.commit()

    async def asyncTearDown(self): self.engine.dispose()

    def ticket(self, sender, target):
        with Session(self.engine) as s:
            return Obj(ticket=self.ns['roulette_ticket'](sender,s.get(MatchQueue,target),int(time.time())+60))

    async def invite(self,sender=1,target=2):
        return (await self.ns['roulette_choose'](self.ticket(sender,target),sender))['invitation']['id']

    async def respond(self,identifier,uid=2,action='accept'):
        return await self.ns['respond_invitation'](Obj(invitation_id=identifier,action=action),uid)

    def matches(self):
        with Session(self.engine) as s: return s.scalars(select(Match)).all()

    async def test_sender_waits_until_recipient_accepts(self):
        identifier=await self.invite()
        self.assertEqual(self.matches(),[])
        with Session(self.engine) as s: self.assertEqual(len(s.scalars(select(MatchQueue)).all()),4)
        await self.respond(identifier)
        match=self.matches()[0]
        self.assertEqual((match.user_one_id,match.user_two_id,match.mode),(1,2,'mini_oa'))
        with Session(self.engine) as s:
            self.assertIsNone(s.get(MatchQueue,1))
            self.assertIsNone(s.get(MatchQueue,2))
            self.assertIsNone(s.get(ChatInvitation,identifier))

    async def test_competing_chain_reserves_both_people(self):
        requests=[(1,2),(2,3),(3,2)]
        choices=[self.ticket(a,b) for a,b in requests]
        results=await asyncio.gather(*(self.ns['roulette_choose'](body,a) for body,(a,b) in zip(choices,requests)),return_exceptions=True)
        self.assertEqual(sum(isinstance(result,dict) for result in results),1)
        self.assertEqual(self.matches(),[])
        async with self.ns['SessionLocal']() as s:
            candidates=await self.ns['roulette_candidates'](s,4)
            self.assertEqual([row.user_id for row in candidates],[3])

    async def test_sender_cannot_accept_own_invitation_or_third_party_accept(self):
        identifier=await self.invite()
        for uid in (1,3):
            with self.assertRaises(HttpError): await self.respond(identifier,uid)
        self.assertEqual(self.matches(),[])

    async def test_reject_and_cancel_release_both(self):
        for uid,action in ((2,'reject'),(1,'cancel')):
            identifier=await self.invite()
            await self.respond(identifier,uid,action)
            with Session(self.engine) as s:
                self.assertIsNone(s.get(ChatInvitation,identifier))
                self.assertIsNotNone(s.get(MatchQueue,1))
                self.assertIsNotNone(s.get(MatchQueue,2))
        self.assertEqual(self.matches(),[])

    async def test_expired_invitation_cannot_start_chat(self):
        identifier=await self.invite()
        with Session(self.engine) as s:
            s.get(ChatInvitation,identifier).expires_at=datetime.now(UTC)-timedelta(seconds=1)
            s.commit()
        with self.assertRaises(HttpError): await self.respond(identifier)
        self.assertEqual(self.matches(),[])
        await self.invite(3,2)

    async def test_leaving_queue_cancels_invitation(self):
        identifier=await self.invite()
        async with self.ns['SessionLocal']() as s:
            await self.ns['leave_queue'](s,1)
            await s.commit()
        with self.assertRaises(HttpError): await self.respond(identifier)
        self.assertEqual(self.matches(),[])

    async def test_duplicate_accept_creates_only_one_match(self):
        identifier=await self.invite()
        results=await asyncio.gather(self.respond(identifier),self.respond(identifier),return_exceptions=True)
        self.assertEqual(len(self.matches()),1)
        self.assertEqual(sum(isinstance(result,HttpError) for result in results),1)

    async def test_disconnected_or_banned_sender_cannot_be_accepted(self):
        identifier=await self.invite()
        with Session(self.engine) as s:
            s.get(MatchQueue,1).queued_at=datetime.now(UTC)-timedelta(seconds=35)
            s.commit()
        with self.assertRaises(HttpError): await self.respond(identifier)
        self.assertEqual(self.matches(),[])

    async def test_incoming_anonymous_identity_is_hidden(self):
        identifier=await self.invite(2,1)
        async with self.ns['SessionLocal']() as s:
            pending=await self.ns['pending_invitation'](s,1)
            result=await self.ns['invitation_payload'](s,pending,1)
        self.assertEqual(result['direction'],'incoming')
        self.assertEqual(result['person'],{'name':'Anonim','avatar':None,'anonymous':True})
