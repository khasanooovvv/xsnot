"""Exercise the actual chat response with each pair of privacy choices."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock


def load_function(path, name, namespace):
    tree = ast.parse(Path(path).read_text(encoding='utf-8'))
    fn = next(node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name)
    fn.decorator_list = []
    fn.args.defaults = []
    for arg in fn.args.args:
        arg.annotation = None
    fn.returns = None
    exec(compile(ast.Module(body=[fn], type_ignores=[]), path, 'exec'), namespace)
    return namespace[name]


class Query:
    def __gt__(self, other): return self
    def __eq__(self, other): return self
    def where(self, *args): return self
    def order_by(self, *args): return self
    def limit(self, *args): return self


class Session:
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def execute(self, query): pass
    async def get(self, model, uid): return SimpleNamespace(telegram_id=uid)
    async def scalars(self, query): return SimpleNamespace(all=lambda: [])


class PrivacyTests(unittest.IsolatedAsyncioTestCase):
    def test_toggle_preserves_partners_choice(self):
        ns = {}
        anonymous = load_function('app/services/matching.py', 'is_anonymous', ns)
        change = load_function('app/services/matching.py', 'set_anonymous', ns)
        match = SimpleNamespace(mode='mini_aa',user_one_id=1,user_two_id=2)
        change(match,1,False)
        self.assertFalse(anonymous(match,1))
        self.assertTrue(anonymous(match,2))
        change(match,2,False)
        self.assertFalse(anonymous(match,1))
        self.assertFalse(anonymous(match,2))
        change(match,1,True)
        self.assertTrue(anonymous(match,1))
        self.assertFalse(anonymous(match,2))

    async def test_each_participants_choice_is_enforced(self):
        anonymous = load_function('app/services/matching.py', 'is_anonymous', {})
        for mode, flags in [('mini_aa',(True,True)), ('mini_ao',(True,False)), ('mini_oa',(False,True)), ('mini_oo',(False,False)), ('mini_anonymous',(True,True)), ('mini_open',(False,False))]:
            match = SimpleNamespace(id=9, mode=mode, user_one_id=1, user_two_id=2)
            for uid in (1, 2):
                with self.subTest(mode=mode, viewer=uid):
                    profile = AsyncMock(return_value=dict(name='Private name',avatar='private-photo',age=23,city='Toshkent',verified=False,silver=False,gold=0))
                    ns = dict(SessionLocal=Session, sql=lambda x:x, active_match=AsyncMock(return_value=match), is_anonymous=anonymous, profile=profile, User=object,
                              MiniMessage=SimpleNamespace(match_id=Query(),id=Query()),select=lambda *args: Query())
                    chat = load_function('app/miniapp.py','chat',ns)
                    response = await chat(0,uid)
                    self.assertEqual(response['own_anonymous'],flags[uid-1])
                    if flags[2-uid]:
                        self.assertEqual(response['partner'],{'name':'Anonim','avatar':None,'anonymous':True})
                        profile.assert_not_awaited()
                    else:
                        self.assertEqual(response['partner']['name'],'Private name')
                        profile.assert_awaited_once()


if __name__ == '__main__': unittest.main()
