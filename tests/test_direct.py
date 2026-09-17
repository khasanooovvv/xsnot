"""Private-chat integration tests against an isolated SQLite database."""
import os
os.environ['BOT_TOKEN'] = '123:test'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///:memory:'
import unittest
from datetime import timedelta
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from fastapi import FastAPI
import httpx
from app import direct, miniapp
from app.models import Base, User, UserUsername
from app.direct_models import UserPresence


class DirectTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with self.engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.old_direct, self.old_mini = direct.SessionLocal, miniapp.SessionLocal
        direct.SessionLocal = miniapp.SessionLocal = self.sessions
        async with self.sessions() as s:
            s.add_all([User(telegram_id=i, display_name=f'User {i}', app_username=f'user{i}', is_registered=True) for i in (1,2,3)])
            s.add(UserUsername(user_id=1, username='aliasone', position=1))
            await s.commit()
        app = FastAPI()
        app.include_router(direct.router)
        app.include_router(miniapp.router)
        self.uid = 1
        app.dependency_overrides[miniapp.registered] = lambda: self.uid
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test')

    async def asyncTearDown(self):
        await self.client.aclose()
        direct.SessionLocal, miniapp.SessionLocal = self.old_direct, self.old_mini
        await self.engine.dispose()

    async def call(self, method, path, body=None, status=200):
        r = await self.client.request(method, '/api/direct'+path, **({'json':body} if body is not None else {}))
        self.assertEqual(r.status_code, status, r.text)
        return r.json()

    async def test_lightweight_refresh_and_thumbnail(self):
        import base64, io
        from PIL import Image
        from app.models import MiniAvatar
        from sqlalchemy import event
        raw = io.BytesIO()
        Image.new('RGB', (1024, 1024), 'blue').save(raw, format='PNG')
        async with self.sessions() as s:
            s.add(MiniAvatar(user_id=2, data='data:image/png;base64,'+base64.b64encode(raw.getvalue()).decode()))
            await s.commit()
        cid = (await self.call('POST', '/chats/with/2'))['chat_id']
        await self.call('POST', '/chats/with/3')
        statements = []
        def record(conn, cursor, statement, parameters, context, many):
            statements.append(statement)
        event.listen(self.engine.sync_engine, 'before_cursor_execute', record)
        try:
            data = await self.call('GET', '/chats?include_avatar=false')
        finally:
            event.remove(self.engine.sync_engine, 'before_cursor_execute', record)
        self.assertEqual(len(statements), 5)
        self.assertTrue(all('avatar' not in c['partner'] for c in data['chats']))
        full = await self.call('GET', '/chats')
        photo = next(c['partner']['avatar'] for c in full['chats'] if c['partner']['id'] == 2)
        with Image.open(io.BytesIO(base64.b64decode(photo.split(',')[1]))) as thumb:
            self.assertEqual(thumb.size, (128,128))
        delta = await self.call('GET', f'/chats/{cid}/messages?since_revision=0&include_avatar=false')
        self.assertNotIn('avatar', delta['partner'])

    async def test_delivery_edits_deletes_history_and_permissions(self):
        cid = (await self.call('POST','/chats/with/2'))['chat_id']
        self.assertEqual((await self.call('POST','/chats/with/2'))['chat_id'],cid)
        msg = await self.call('POST',f'/chats/{cid}/messages',{'text':'hello'})
        self.uid = 2
        rows = await self.call('GET','/chats')
        self.assertEqual(rows['chats'][0]['unread'],1)
        page = await self.call('GET',f'/chats/{cid}/messages')
        self.assertEqual(page['messages'][0]['text'],'hello')
        await self.call('PATCH',f'/chats/{cid}/messages/{msg["id"]}',{'text':'stolen'},403)
        await self.call('DELETE',f'/chats/{cid}/messages/{msg["id"]}',status=403)
        self.uid = 1
        await self.call('PATCH',f'/chats/{cid}/messages/{msg["id"]}',{'text':'edited'})
        self.uid = 2
        changes = await self.call('GET',f'/chats/{cid}/messages?since_revision={page["revision"]}')
        self.assertTrue(changes['messages'][0]['is_edited'])
        self.assertEqual(changes['messages'][0]['text'],'edited')
        await self.call('POST',f'/chats/{cid}/read',{'message_id':msg['id']})
        self.assertEqual((await self.call('GET','/chats'))['chats'][0]['unread'],0)
        self.uid = 1
        await self.call('DELETE',f'/chats/{cid}/messages/{msg["id"]}')
        self.uid = 2
        changes = await self.call('GET',f'/chats/{cid}/messages?since_revision={changes["revision"]}')
        self.assertTrue(changes['messages'][0]['is_deleted'])
        self.assertEqual(changes['messages'][0]['text'],'')
        self.uid = 3
        await self.call('GET',f'/chats/{cid}/messages',status=404)
        await self.call('POST',f'/chats/{cid}/messages',{'text':'intruder'},404)

    async def test_independent_deletion_reappearance_and_sort(self):
        c = (await self.call('POST','/chats/with/2'))['chat_id']
        await self.call('POST',f'/chats/{c}/messages',{'text':'first'})
        await self.call('DELETE',f'/chats/{c}')
        self.assertEqual((await self.call('GET','/chats'))['chats'],[])
        self.uid=2
        self.assertEqual(len((await self.call('GET','/chats'))['chats']),1)
        await self.call('DELETE',f'/chats/{c}')
        self.assertEqual((await self.call('GET','/chats'))['chats'],[])
        await self.call('POST',f'/chats/{c}/messages',{'text':'back'})
        self.assertEqual(len((await self.call('GET','/chats'))['chats']),1)
        self.uid=1
        self.assertEqual(len((await self.call('GET','/chats'))['chats']),1)
        c2=(await self.call('POST','/chats/with/3'))['chat_id']
        await self.call('POST',f'/chats/{c2}/messages',{'text':'newest'})
        self.assertEqual((await self.call('GET','/chats'))['chats'][0]['id'],c2)
        await self.call('POST',f'/chats/{c}/messages',{'text':'latest'})
        self.assertEqual((await self.call('GET','/chats'))['chats'][0]['id'],c)

    async def test_block_search_unblock_presence(self):
        c=(await self.call('POST','/chats/with/2'))['chat_id']
        await self.call('POST','/presence',{'online':True})
        self.uid=2
        self.assertTrue((await self.call('GET',f'/chats/{c}/messages'))['partner']['online'])
        self.assertEqual(len((await self.client.get('/api/users/search?q=aliasone')).json()),1)
        self.uid=1
        await self.call('POST','/blocks/2')
        await self.call('POST',f'/chats/{c}/messages',{'text':'blocked'},403)
        self.uid=2
        await self.call('POST',f'/chats/{c}/messages',{'text':'blocked'},403)
        self.assertEqual((await self.client.get('/api/users/search?q=aliasone')).json(),[])
        self.assertEqual((await self.client.get('/api/users/search?q=user1')).json(),[])
        await self.call('DELETE','/blocks/1')
        await self.call('POST',f'/chats/{c}/messages',{'text':'still blocked'},403)
        self.uid=1
        await self.call('DELETE','/blocks/2')
        async with self.sessions() as s:
            p=await s.get(UserPresence,1)
            p.last_seen_at=direct.now()-timedelta(seconds=31)
            await s.commit()
        self.uid=2
        self.assertFalse((await self.call('GET',f'/chats/{c}/messages'))['partner']['online'])
        await self.call('POST',f'/chats/{c}/messages',{'text':'unblocked'})

    async def test_history_and_change_pagination(self):
        from app.direct_models import DirectChat, DirectMessage
        cid=(await self.call('POST','/chats/with/2'))['chat_id']
        async with self.sessions() as s:
            c=await s.get(DirectChat,cid)
            c.revision=105
            s.add_all([DirectMessage(chat_id=cid,sender_id=1,text=str(i),created_at=direct.now(),updated_at=direct.now(),revision=i) for i in range(1,106)])
            await s.commit()
        self.uid=2
        latest=await self.call('GET',f'/chats/{cid}/messages')
        self.assertEqual(len(latest['messages']),100)
        older=await self.call('GET',f'/chats/{cid}/messages?before_id={latest["before_id"]}')
        self.assertEqual(len(older['messages']),5)
        first=await self.call('GET',f'/chats/{cid}/messages?since_revision=0')
        self.assertTrue(first['more'])
        second=await self.call('GET',f'/chats/{cid}/messages?since_revision={first["revision"]}')
        self.assertEqual(len(second['messages']),5)
        self.assertFalse(second['more'])

if __name__ == '__main__':
    unittest.main()
