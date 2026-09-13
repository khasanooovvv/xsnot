import ast
from pathlib import Path
from types import SimpleNamespace as Obj
import unittest
from unittest.mock import AsyncMock

class Session:
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def commit(self): pass

class LanguageFlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user=Obj(is_registered=True, language='uz')
        source=ast.parse(Path('app/bot.py').read_text(encoding='utf-8'))
        functions=[n for n in source.body if isinstance(n,ast.AsyncFunctionDef) and n.name in ('start','set_language')]
        for f in functions:
            f.decorator_list=[]
            for arg in f.args.args: arg.annotation=None
        self.scope=dict(cfg=Obj(webapp_url='https://example.com'),SessionLocal=Session,
            get_or_create=AsyncMock(return_value=self.user), language_menu=lambda:'LANGUAGE_CHOICES',
            tr=lambda lang,key:lang+':'+key,InlineKeyboardMarkup=Obj,InlineKeyboardButton=Obj,WebAppInfo=Obj)
        exec(compile(ast.Module(body=functions,type_ignores=[]),'<actual bot handlers>','exec'),self.scope)
        self.sender=Obj(id=6322372175,username='tester',full_name='Tester')

    async def test_start_shows_languages_even_for_registered_user_and_preserves_referral(self):
        message=Obj(text='/start ref_42',from_user=self.sender,answer=AsyncMock())
        state=Obj(clear=AsyncMock())
        await self.scope['start'](message,state)
        self.assertEqual(message.answer.call_args.kwargs['reply_markup'],'LANGUAGE_CHOICES')
        self.assertEqual(self.scope['get_or_create'].call_args.args[-1],42)

    async def test_each_language_is_saved_before_localized_launch(self):
        for lang in ('uz','ru','en'):
            q=Obj(data='lang:'+lang,from_user=self.sender,answer=AsyncMock(),message=Obj(edit_text=AsyncMock()))
            await self.scope['set_language'](q,Obj(clear=AsyncMock()))
            self.assertEqual(self.user.language,lang)
            self.assertEqual(q.message.edit_text.call_args.args[0],lang+':welcome')
            buttons=q.message.edit_text.call_args.kwargs['reply_markup'].inline_keyboard
            self.assertEqual(buttons[0][0].web_app.url,'https://example.com')
            q.answer.assert_awaited_once()

    async def test_invalid_language_does_not_change_profile(self):
        q=Obj(data='lang:invalid',answer=AsyncMock())
        await self.scope['set_language'](q,Obj())
        self.scope['get_or_create'].assert_not_awaited()
