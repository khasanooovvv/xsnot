import ast
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace as Obj
import unittest

class HTTPException(Exception):
    def __init__(self,status_code,detail):self.status_code=status_code

class VideoReviewTests(unittest.IsolatedAsyncioTestCase):
    def setup_review(self):
        user=Obj(silver_verified=False,is_verified=False,gold_until='existing gold')
        row=Obj(status='pending',video=b'private video',media_type='video/mp4')
        class Session:
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            async def get(self,model,uid,**kwargs):return user if model=='User' else row
            async def commit(self):pass
        tree=ast.parse(Path('app/verification.py').read_text(encoding='utf-8-sig'))
        fn=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='review')
        fn.decorator_list=[]
        for arg in fn.args.args:arg.annotation=None
        scope=dict(SessionLocal=Session,User='User',VideoVerification='Video',HTTPException=HTTPException,datetime=datetime,UTC=UTC)
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'<actual review>','exec'),scope)
        return scope['review'],user,row

    async def test_approval_grants_silver_and_erases_video_only(self):
        review,user,row=self.setup_review()
        self.assertEqual(await review(1,Obj(approved=True,reason='')),{'status':'approved'})
        self.assertTrue(user.silver_verified);self.assertFalse(user.is_verified)
        self.assertEqual(user.gold_until,'existing gold');self.assertIsNone(row.video)
        with self.assertRaises(HTTPException):await review(1,Obj(approved=True,reason=''))

    async def test_rejection_preserves_reason_and_erases_video(self):
        review,user,row=self.setup_review()
        await review(1,Obj(approved=False,reason='Code not audible'))
        self.assertFalse(user.silver_verified);self.assertIsNone(row.video)
        self.assertEqual(row.reason,'Code not audible');self.assertEqual(row.status,'rejected')

    async def test_empty_rejection_reason_is_not_accepted(self):
        review,user,row=self.setup_review()
        with self.assertRaises(HTTPException):await review(1,Obj(approved=False,reason=' '))
        self.assertEqual(row.status,'pending');self.assertIsNotNone(row.video)

    def test_admin_router_has_auth_dependency(self):
        tree=ast.parse(Path('app/admin.py').read_text(encoding='utf-8'))
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='include_router']
        mount=next(n for n in calls if n.args and ast.unparse(n.args[0])=='verification_admin_router')
        self.assertTrue(any(k.arg=='dependencies' and ast.unparse(k.value)=='[Depends(admin)]' for k in mount.keywords))

class DirectVideoUploadTests(unittest.IsolatedAsyncioTestCase):
    async def test_upload_needs_no_code_and_prevents_pending_replacement(self):
        user=Obj(silver_verified=False)
        records=[]
        class Session:
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            async def get(self,model,uid,**kwargs):return user if model=='User' else records[0] if records else None
            def add(self,row):records.append(row)
            async def commit(self):pass
        class Upload:
            async def read(self,limit):return b'\x00\x00\x00\x18ftypisom'+b'\x00'*20
            async def close(self):pass
        tree=ast.parse(Path('app/verification.py').read_text(encoding='utf-8-sig'))
        fn=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='submit')
        self.assertNotIn('code',[a.arg for a in fn.args.args])
        fn.decorator_list=[];fn.args.defaults=[]
        for arg in fn.args.args:arg.annotation=None
        scope=dict(SessionLocal=Session,User='User',VideoVerification=Obj,HTTPException=HTTPException,datetime=datetime,UTC=UTC,MAX_VIDEO_BYTES=15*1024*1024)
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'<actual submit>','exec'),scope)
        self.assertEqual(await scope['submit'](Upload(),True,123),{'status':'pending'})
        self.assertTrue(records[0].video)
        with self.assertRaises(HTTPException):await scope['submit'](Upload(),True,123)
        records[0].status='rejected'
        self.assertEqual(await scope['submit'](Upload(),True,123),{'status':'pending'})
