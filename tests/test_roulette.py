"""Selection authorization and privacy checks against the actual endpoint functions."""
import hashlib
import hmac
import secrets
import time
import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace as Obj
from unittest.mock import AsyncMock
from test_chat_privacy import load_function, Query


class HttpError(Exception):
    def __init__(self, status, detail):
        self.status_code = status


class Session:
    def __init__(self, own):
        self.own = own
        self.matches = []
        self.commit = AsyncMock()
        self.execute = AsyncMock()
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def get(self, model, uid): return self.own
    def add(self, match): self.matches.append(match)


class RouletteTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.own = Obj(user_id=10, mode='mini_ro', archive_consent=True)
        self.partner = Obj(user_id=20, mode='mini_ra', archive_consent=True)
        self.session = Session(self.own)
        self.ns = dict(hmac=hmac, hashlib=hashlib, time=time, secrets=secrets,
                       datetime=datetime, UTC=UTC, timedelta=timedelta, HTTPException=HttpError,
                       settings=lambda: Obj(bot_token='test-secret', archive_channel_id=123),
                       SessionLocal=lambda: self.session, MatchQueue=object, User=object,
                       Match=lambda **kwargs: Obj(**kwargs), sql=lambda x:x,
                       active_match=AsyncMock(return_value=None),
                       pending_invitation=AsyncMock(return_value=None),
                       invitation_payload=AsyncMock(return_value={'id':'invite','direction':'outgoing'}),
                       ChatInvitation=type('Invitation',(),{'expires_at':type('Expiry',(),{'__le__':lambda self,other:True})(),'__init__':lambda self,**kw:self.__dict__.update(kw)}),
                       delete=lambda *args:Query(),
                       roulette_candidates=AsyncMock(return_value=[self.partner]),
                       leave_queue=AsyncMock(), profile=AsyncMock())
        self.ticket = load_function('app/miniapp.py', 'roulette_ticket', self.ns)
        self.choose = load_function('app/miniapp.py', 'roulette_choose', self.ns)
        self.spin = load_function('app/miniapp.py', 'roulette_spin', self.ns)

    def choice(self, uid=10, expires=None):
        return Obj(ticket=self.ticket(uid, self.partner, expires or int(time.time()) + 60))

    async def test_spin_does_not_match_or_disclose_anonymous_profile(self):
        result = await self.spin(10)
        self.assertEqual(result['items'], [{'name':'Anonim', 'avatar':None, 'anonymous':True}])
        self.ns['profile'].assert_not_awaited()
        self.assertEqual(self.session.matches, [])
        self.assertIsNotNone(result['ticket'])

    async def test_selected_avatar_only_invites_without_starting_chat(self):
        result=await self.choose(self.choice(), 10)
        invitation = self.session.matches[0]
        self.assertEqual((invitation.sender_id,invitation.recipient_id),(10,20))
        self.assertFalse(hasattr(invitation,'mode'))
        self.assertEqual(result['invitation']['direction'],'outgoing')
        self.ns['leave_queue'].assert_not_awaited()
        self.session.commit.assert_awaited_once()

    async def test_pending_invitation_blocks_another_selection(self):
        self.ns['pending_invitation'].return_value=Obj(id='pending')
        with self.assertRaises(HttpError): await self.choose(self.choice(),10)
        self.assertFalse(self.session.matches)

    async def test_ticket_cannot_be_used_by_another_viewer(self):
        with self.assertRaises(HttpError): await self.choose(self.choice(uid=99), 10)
        self.assertFalse(self.session.matches)

    async def test_expired_choice_rejected(self):
        with self.assertRaises(HttpError): await self.choose(self.choice(expires=int(time.time())-1), 10)
        self.assertFalse(self.session.matches)

    async def test_busy_or_departed_partner_rejected(self):
        self.ns['roulette_candidates'].return_value = []
        with self.assertRaises(HttpError): await self.choose(self.choice(), 10)
        self.assertFalse(self.session.matches)

    async def test_changed_privacy_invalidates_preview(self):
        choice = self.choice()
        self.partner.mode = 'mini_ro'
        with self.assertRaises(HttpError): await self.choose(choice, 10)

    async def test_existing_match_prevents_second_match(self):
        self.ns['active_match'].return_value = Obj(id=123)
        with self.assertRaises(HttpError): await self.choose(self.choice(), 10)
        self.assertFalse(self.session.matches)

    async def test_archive_consent_required_for_both(self):
        self.partner.archive_consent = False
        with self.assertRaises(HttpError): await self.choose(self.choice(), 10)
        self.assertFalse(self.session.matches)

    async def test_empty_queue_returns_no_selection(self):
        self.ns['roulette_candidates'].return_value = []
        result = await self.spin(10)
        self.assertEqual(result, {'items': [], 'selected': None, 'ticket': None})


if __name__ == '__main__': unittest.main()
