"""Dependency-free checks of the actual Telegram authentication function."""
import ast
import hashlib
import hmac
import json
from pathlib import Path
import time
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock
from urllib.parse import parse_qsl, urlencode

class HTTPException(Exception):
    def __init__(self, status_code, detail): self.status_code = status_code

class Session:
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def commit(self): pass

class AuthTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        tree = ast.parse(Path('app/miniapp.py').read_text(encoding='utf-8'))
        function = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'identity')
        self.create = AsyncMock(return_value=SimpleNamespace(is_banned=False))
        scope = dict(hmac=hmac, hashlib=hashlib, json=json, time=time, parse_qsl=parse_qsl,
            Header=lambda **kw:'', HTTPException=HTTPException,
            settings=lambda:SimpleNamespace(bot_token='test-token'), SessionLocal=Session, get_or_create=self.create)
        exec(compile(ast.Module(body=[function], type_ignores=[]), '<actual identity>', 'exec'), scope)
        self.identity = scope['identity']

    def signed(self, age=0):
        data = {'auth_date':str(int(time.time())-age), 'user':json.dumps({'id':123, 'first_name':'Tester'})}
        secret = hmac.new(b'WebAppData', b'test-token', hashlib.sha256).digest()
        data['hash'] = hmac.new(secret, '\n'.join(f'{k}={v}' for k,v in sorted(data.items())).encode(), hashlib.sha256).hexdigest()
        return urlencode(data)

    async def test_valid_signed_identity(self):
        self.assertEqual(await self.identity(self.signed()), 123)

    async def test_reject_unsigned_tampered_expired_and_duplicate(self):
        for value in ['', self.signed().replace('Tester','Attacker'), self.signed(90000), self.signed()+'&auth_date=1']:
            with self.subTest(value=value):
                with self.assertRaises(HTTPException) as error: await self.identity(value)
                self.assertEqual(error.exception.status_code, 401)
        self.create.assert_not_awaited()

    async def test_banned_user_cannot_access(self):
        self.create.return_value = SimpleNamespace(is_banned=True)
        with self.assertRaises(HTTPException) as error: await self.identity(self.signed())
        self.assertEqual(error.exception.status_code, 403)

if __name__ == '__main__': unittest.main()
