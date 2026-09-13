import ast
from pathlib import Path
from types import SimpleNamespace as Obj
import unittest
from unittest.mock import AsyncMock

class GoldRevokeTests(unittest.IsolatedAsyncioTestCase):
    async def test_revoke_preserves_silver_and_blue_and_can_repeat(self):
        user=Obj(gold_until='active',premium_until='unchanged',is_verified=True)
        class Session:
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            get=AsyncMock(return_value=user)
            commit=AsyncMock()
        tree=ast.parse(Path('app/admin.py').read_text(encoding='utf-8'))
        fn=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='revoke_gold')
        self.assertTrue(any('Depends(admin)' in ast.unparse(d) for d in fn.decorator_list))
        fn.decorator_list=[]
        scope=dict(SessionLocal=Session,User=Obj)
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'<actual revoke_gold>','exec'),scope)
        for _ in range(2):
            self.assertEqual(await scope['revoke_gold'](123),{'ok':True,'gold':0})
            self.assertIsNone(user.gold_until)
            self.assertEqual(user.premium_until,'unchanged')
            self.assertTrue(user.is_verified)
        self.assertEqual(Session.commit.await_count,2)
