import os
os.environ.setdefault('BOT_TOKEN', '123:test')
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///:memory:'
import base64
import io
import unittest
import httpx
from fastapi import FastAPI
from PIL import Image
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app import dating, miniapp
from app.models import Base, User
from app.direct_models import BlockedUser
from app.dating_models import DatingProfile
from datetime import UTC, datetime

class DatingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine=create_async_engine('sqlite+aiosqlite:///:memory:')
        async with self.engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)
        self.sessions=async_sessionmaker(self.engine,expire_on_commit=False)
        self.previous=dating.SessionLocal;dating.SessionLocal=self.sessions
        async with self.sessions() as s:
            s.add_all([User(telegram_id=i,display_name=str(i),is_registered=True,gender=g) for i,g in [(1,'male'),(2,'female'),(3,'male'),(4,'female')]])
            await s.commit()
        app=FastAPI();app.include_router(dating.router);self.uid=1
        app.dependency_overrides[miniapp.registered]=lambda:self.uid
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test')
        output=io.BytesIO();Image.new('RGB',(20,30),'white').save(output,'PNG')
        self.photo='data:image/png;base64,'+base64.b64encode(output.getvalue()).decode()

    async def asyncTearDown(self):
        await self.client.aclose();dating.SessionLocal=self.previous;await self.engine.dispose()

    async def save(self,uid,photos=None):
        self.uid=uid
        r=await self.client.post('/api/dating/me',json={'bio':' Dating bio ','photos':[self.photo] if photos is None else photos})
        self.assertEqual(r.status_code,200,r.text)
        return r.json()

    async def test_persistence_limits_and_separate_profile(self):
        row=await self.save(1,[self.photo]*6)
        self.assertEqual(len(row['photos']),6);self.assertEqual(row['bio'],'Dating bio')
        async with self.sessions() as s:
            self.assertIsNone((await s.get(User,1)).bio)
        r=await self.client.post('/api/dating/me',json={'photos':[self.photo]*7})
        self.assertEqual(r.status_code,422)
        r=await self.client.post('/api/dating/me',json={'photos':['data:image/png;base64,broken']})
        self.assertEqual(r.status_code,422)
        self.assertEqual(len((await self.client.get('/api/dating/me')).json()['photos']),6)

    async def test_filter_mutual_like_and_blocks(self):
        for uid in (1,2,3,4):await self.save(uid)
        self.uid=1
        self.assertEqual([p['id'] for p in (await self.client.get('/api/dating/cards')).json()],[2,4])
        r=await self.client.post('/api/dating/vote/3',json={'liked':True});self.assertEqual(r.status_code,404)
        self.assertFalse((await self.client.post('/api/dating/vote/2',json={'liked':True})).json()['matched'])
        self.uid=2
        self.assertTrue((await self.client.post('/api/dating/vote/1',json={'liked':True})).json()['matched'])
        self.assertEqual([p['id'] for p in (await self.client.get('/api/dating/matches')).json()],[1])
        async with self.sessions() as s:
            s.add(BlockedUser(blocker_id=1,blocked_id=2,created_at=datetime.now(UTC)));await s.commit()
        self.assertEqual((await self.client.get('/api/dating/matches')).json(),[])
        r=await self.client.post('/api/dating/vote/1',json={'liked':True});self.assertEqual(r.status_code,404)

    async def test_last_photo_removal_unpublishes(self):
        await self.save(1);await self.save(2);await self.save(2,[])
        self.uid=1
        self.assertEqual((await self.client.get('/api/dating/cards')).json(),[])

    async def test_undo_like_is_scoped_to_owner(self):
        for uid in (1,2,3):await self.save(uid)
        self.uid=1
        await self.client.post('/api/dating/vote/2',json={'liked':True})
        self.uid=2
        await self.client.post('/api/dating/vote/1',json={'liked':True})
        self.uid=3
        self.assertEqual((await self.client.post('/api/dating/undo/2')).status_code,404)
        self.uid=1
        self.assertEqual([p['id'] for p in (await self.client.get('/api/dating/likes')).json()],[2])
        self.assertEqual((await self.client.post('/api/dating/undo/2')).status_code,200)
        self.assertEqual((await self.client.get('/api/dating/matches')).json(),[])
        self.assertEqual([p['id'] for p in (await self.client.get('/api/dating/cards')).json()],[2])
        self.assertEqual((await self.client.post('/api/dating/undo/2')).status_code,404)
        self.uid=2
        self.assertEqual([p['id'] for p in (await self.client.get('/api/dating/likes')).json()],[1])

    async def test_undo_skip_and_history(self):
        for uid in (1,2,4):await self.save(uid)
        self.uid=1
        await self.client.post('/api/dating/vote/2',json={'liked':False})
        await self.client.post('/api/dating/vote/4',json={'liked':True})
        self.assertEqual([(p['id'],p['liked']) for p in (await self.client.get('/api/dating/history')).json()],[(2,False),(4,True)])
        self.uid=4
        self.assertEqual((await self.client.get('/api/dating/history')).json(),[])
        self.assertEqual((await self.client.post('/api/dating/undo/2')).status_code,404)
        self.uid=1
        self.assertEqual((await self.client.post('/api/dating/undo/2')).status_code,200)
        self.assertEqual([p['id'] for p in (await self.client.get('/api/dating/cards')).json()],[2])
        self.assertEqual([p['id'] for p in (await self.client.get('/api/dating/history')).json()],[4])
