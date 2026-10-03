import ast
import hashlib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock


class Query:
    def __getattr__(self, name):
        return lambda *args, **kwargs: self


class LeadersTests(unittest.IsolatedAsyncioTestCase):
    async def render(self, avatar):
        query = Query()
        user = SimpleNamespace(telegram_id=42, display_name='Leader')
        session = SimpleNamespace(
            execute=AsyncMock(return_value=SimpleNamespace(all=lambda: [(user, 12)])),
            get=AsyncMock(return_value=avatar),
        )

        class Context:
            async def __aenter__(self):
                return session

            async def __aexit__(self, *args):
                pass

        tree = ast.parse(Path('app/miniapp.py').read_text(encoding='utf-8'))
        function = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'leaders')
        function.decorator_list = []
        function.args.defaults = []
        namespace = dict(
            SessionLocal=Context, select=lambda *args: query,
            User=SimpleNamespace(telegram_id=42, display_name='Leader'),
            ReferralHistory=SimpleNamespace(id=1, referrer_id=42, active=query),
            func=SimpleNamespace(count=lambda *args: query), MiniAvatar=object,
            hashlib=hashlib, badge_status=lambda user: {'gold': 0},
        )
        exec(compile(ast.Module(body=[function], type_ignores=[]), '<leaders>', 'exec'), namespace)
        return await namespace['leaders'](42)

    async def test_avatar_without_updated_at(self):
        result = await self.render(SimpleNamespace(data='photo-data'))
        version = hashlib.sha256(b'photo-data').hexdigest()[:12]
        self.assertEqual(result[0]['avatar'], f'/api/avatar/42?v={version}')
        self.assertEqual(result[0]['count'], 12)

    async def test_no_avatar(self):
        self.assertIsNone((await self.render(None))[0]['avatar'])
