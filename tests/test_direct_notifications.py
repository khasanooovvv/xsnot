import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.parse import urlsplit, parse_qs
from app.services.direct_notifications import notify_direct_message

class NotificationTests(unittest.IsolatedAsyncioTestCase):
    async def test_name_username_and_chat_button(self):
        bot=SimpleNamespace(send_message=AsyncMock())
        with patch('app.services.direct_notifications.settings', return_value=SimpleNamespace(webapp_url='https://example.org/?v=1')):
            await notify_direct_message(bot, 22, 99, 'Sherzod', 'sherzod', 'uz')
        args=bot.send_message.call_args
        self.assertEqual(args.args[0],22)
        self.assertIn('Sherzod sizga xabar yozdi.',args.args[1])
        self.assertNotIn('@sherzod',args.args[1])
        button=args.kwargs['reply_markup'].inline_keyboard[0][0]
        self.assertIn('Xabarni o‘qish',button.text)
        self.assertEqual(parse_qs(urlsplit(button.web_app.url).query),{'v':['1'],'dm_chat':['99']})

    async def test_delivery_failure_does_not_fail_message(self):
        bot=SimpleNamespace(send_message=AsyncMock(side_effect=OSError('offline')))
        with patch('app.services.direct_notifications.settings', return_value=SimpleNamespace(webapp_url='https://example.org')):
            await notify_direct_message(bot,22,99,'Sherzod',None,'uz')
        self.assertIn('Sherzod sizga',bot.send_message.call_args.args[1])
