"""Early API abuse protection. Redis shares limits across workers/replicas."""
import asyncio
import hashlib
import hmac
import ipaddress
import json
import logging
import math
import re
import time
import uuid
from collections import OrderedDict
from tempfile import SpooledTemporaryFile
from urllib.parse import parse_qsl

from redis.asyncio import Redis
from redis.exceptions import RedisError
from starlette.responses import JSONResponse

log = logging.getLogger(__name__)
MB = 1024 * 1024


def canonical_ip(value):
    """Reject lists, ports, zone IDs, hostnames and ambiguous header values."""
    if '%' in value:
        raise ValueError('Scoped IP is not a client identity')
    address = ipaddress.ip_address(value)
    return str(address.ipv4_mapped or address) if isinstance(address, ipaddress.IPv6Address) else str(address)


def client_ip(scope, railway_edge=False):
    # Railway's HTTP edge always overwrites X-Real-IP. This is a deployment
    # trust boundary, not a header-controlled flag or a guessed proxy subnet.
    if railway_edge:
        values = [value for name, value in scope.get('headers', []) if name.lower() == b'x-real-ip']
        if len(values) != 1:
            raise ValueError('Missing or duplicate edge client IP')
        try:
            return canonical_ip(values[0].decode('ascii').strip())
        except UnicodeDecodeError as exc:
            raise ValueError('Invalid edge client IP') from exc
    # Outside that deployment boundary ignore all client-supplied IP headers.
    peer = (scope.get('client') or ('unknown',))[0]
    try:
        return canonical_ip(peer)
    except ValueError:
        return 'unknown'

# Atomic rolling windows: denied attempts do not extend the window.
WINDOW = """
local t = redis.call('TIME')
local now = tonumber(t[1]) + tonumber(t[2]) / 1000000
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - tonumber(ARGV[2]))
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then
 local first = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
 return math.max(1, math.ceil(tonumber(first[2]) + tonumber(ARGV[2]) - now))
end
if ARGV[3] ~= '' then
 redis.call('ZADD', KEYS[1], now, ARGV[3])
 redis.call('EXPIRE', KEYS[1], math.ceil(tonumber(ARGV[2])))
end
return 0
"""
LEASE = """
local t = redis.call('TIME')
local now = tonumber(t[1])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then return 0 end
redis.call('ZADD', KEYS[1], now + 120, ARGV[2])
redis.call('EXPIRE', KEYS[1], 120)
return 1
"""


class LimitStore:
    def __init__(self, url):
        self.redis = Redis.from_url(url, socket_connect_timeout=0.2, socket_timeout=0.2)
        self.offline_until = 0
        self.local = OrderedDict()
        self.leases = {}

    async def remote(self, operation, *args):
        if time.monotonic() < self.offline_until:
            return None
        try:
            return await operation(*args)
        except (RedisError, OSError):
            self.offline_until = time.monotonic() + 30
            log.warning('Security Redis unavailable; using bounded per-process limits for 30s')
            return None

    async def window(self, key, count, seconds, consume=True):
        key = 'security:v1:' + key
        result = await self.remote(self.redis.eval, WINDOW, 1, key, count, seconds,
                                   uuid.uuid4().hex if consume else '')
        if result is not None:
            return int(result)
        now = time.monotonic()
        events = [t for t in self.local.pop(key, []) if t > now - seconds]
        wait = max(1, math.ceil(events[0] + seconds - now)) if len(events) >= count else 0
        if consume and not wait:
            events.append(now)
        self.local[key] = events
        while len(self.local) > 10000:
            self.local.popitem(last=False)
        return wait

    async def acquire(self, uid):
        key, token = f'security:v1:upload:{uid}', uuid.uuid4().hex
        result = await self.remote(self.redis.eval, LEASE, 1, key, 2, token)
        if result is not None:
            return (key, token, True) if result else None
        if self.leases.get(key, 0) >= 2:
            return None
        self.leases[key] = self.leases.get(key, 0) + 1
        return key, token, False

    async def release(self, lease):
        key, token, remote = lease
        if remote:
            await self.remote(self.redis.zrem, key, token)
        else:
            self.leases[key] -= 1
            if not self.leases[key]:
                del self.leases[key]


def verified_uid(value, token):
    """Verify before accessing the database or accepting an upload body."""
    try:
        if len(value) > 16384:
            return None
        pairs = parse_qsl(value, strict_parsing=True)
        data = dict(pairs)
        if len(pairs) != len(data):
            return None
        signature = data.pop('hash')
        check = '\n'.join(f'{k}={v}' for k, v in sorted(data.items()))
        secret = hmac.new(b'WebAppData', token.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        if not -30 <= time.time() - int(data['auth_date']) <= 86400:
            return None
        uid = int(json.loads(data['user'])['id'])
        return uid if uid > 0 else None
    except (ValueError, KeyError, TypeError, OverflowError):
        return None


def policy(path, method):
    if method == 'GET':
        if path == '/api/users/search':
            return 'user-search', [(60, 60)]
        # Normalize IDs: opening many chats cannot multiply the read budget.
        normalized = re.sub(r'/\d+(?=/|$)', '/:id', path)
        known = {'/api/me', '/api/me/avatar', '/api/me/gold', '/api/avatar/:id',
                 '/api/chat', '/api/chat/partner', '/api/leaders', '/api/verification',
                 '/api/direct/chats', '/api/direct/chats/:id/messages', '/api/direct/blocks'}
        return 'read:' + (normalized if normalized in known else 'other'), [(600, 60)]
    if path == '/api/message' or re.fullmatch(r'/api/direct/chats/\d+/messages', path):
        return 'message', [(10, 5), (60, 60)]
    if path == '/api/message/image':
        return 'image', [(6, 60)]
    if path == '/api/photo/prepare':
        return 'photo', [(6, 60)]
    if path in ('/api/search', '/api/roulette/spin'):
        return 'match-search', [(20, 60)]
    if path.startswith('/api/direct/chats/with/'):
        return 'open-chat', [(20, 60)]
    if path in ('/api/profile', '/api/profile/name', '/api/register'):
        return 'profile', [(10, 60)]
    if path == '/api/verification/submit':
        return 'video', [(3, 300)]
    if path == '/api/direct/presence' or path.endswith('/read'):
        return 'presence-read', [(180, 60)]
    return 'other-write', [(60, 60)]


def body_limit(path):
    return {'/api/photo/prepare': 21 * MB, '/api/message/image': 11 * MB,
            '/api/verification/submit': 16 * MB, '/api/profile': 3 * MB,
            '/api/register': 3 * MB}.get(path, 64 * 1024)


class SecurityMiddleware:
    def __init__(self, app, config, store=None):
        self.app, self.config = app, config
        self.store = store or LimitStore(config.redis_url)
        self.active = 0
        self.uploads = 0
        self.railway_edge = bool(getattr(config, 'security_trust_railway_edge', True)
                                 and getattr(config, 'railway_environment_id', '')
                                 and getattr(config, 'railway_public_domain', ''))
        if self.railway_edge and getattr(config, 'railway_tcp_proxy_domain', ''):
            raise ValueError('Railway HTTP client-IP trust requires no TCP proxy on this service')

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            if scope['type'] == 'lifespan':
                async def lifespan_send(message):
                    if message['type'] == 'lifespan.shutdown.complete':
                        await self.store.redis.aclose()
                    await send(message)
                return await self.app(scope, receive, lifespan_send)
            return await self.app(scope, receive, send)
        path = scope['path'].rstrip('/') or '/'
        api = path.startswith('/api/')
        admin = (path == '/admin' or path.startswith('/admin/') or path.startswith('/users/')
                 or path == '/reports' or path == '/leaderboard/reward')
        if not api and not admin:
            return await self.app(scope, receive, send)

        async def reject(status, detail, wait=None, group='request'):
            headers = {'Cache-Control': 'no-store'}
            if wait:
                headers.update({'Retry-After': str(wait), 'X-RateLimit-Scope': group})
            await JSONResponse({'detail': detail}, status_code=status, headers=headers)(scope, receive, send)

        async def limited(wait, group):
            await reject(429, f'Juda ko‘p urinish. {wait} soniyadan keyin qayta urinib ko‘ring.', wait, group)

        if self.active >= self.config.security_max_concurrent:
            return await reject(503, 'Server band. Birozdan keyin qayta urinib ko‘ring.', 3)
        self.active += 1
        lease = None
        upload_slot = False
        started = False
        try:
            headers = dict(scope.get('headers', []))
            try:
                ip = client_ip(scope, self.railway_edge)
            except ValueError:
                return await reject(400, 'So‘rov manzili aniqlanmadi. Qayta urinib ko‘ring.')
            ip_key = hashlib.sha256(ip.encode()).hexdigest()
            if api:
                uid = verified_uid(headers.get(b'x-telegram-init-data', b'').decode('latin1'), self.config.bot_token)
                if uid is None:
                    blocked = await self.store.window('auth-block:' + ip_key, 1, 300, False)
                    if blocked:
                        return await limited(blocked, 'auth')
                    wait = await self.store.window('auth-fail:' + ip_key, 30, 60)
                    if wait:
                        await self.store.window('auth-block:' + ip_key, 1, 300)
                        return await limited(300, 'auth')
                    return await reject(401, 'Mini App’ni Telegram bot ichidan qayta oching.')
                group, rules = policy(path, scope['method'])
                for count, seconds in [(30, 2), (900, 60)]:
                    wait = await self.store.window(f'user:{uid}:all:{seconds}', count, seconds)
                    if wait:
                        return await limited(wait, 'all')
                for count, seconds in rules:
                    wait = await self.store.window(f'user:{uid}:{group}:{seconds}', count, seconds)
                    if wait:
                        return await limited(wait, group)
            else:
                wait = await self.store.window('admin-block:' + ip_key, 1, 900, False)
                if wait:
                    return await limited(wait, 'admin')

            cap = body_limit(path)
            try:
                length = int(headers.get(b'content-length', b'0'))
                if length < 0:
                    raise ValueError()
            except ValueError:
                return await reject(400, 'So‘rov hajmi noto‘g‘ri.')
            if length > cap:
                return await reject(413, 'Yuborilayotgan ma’lumot hajmi juda katta.')
            heavy = api and cap > 64 * 1024 and scope['method'] == 'POST'
            if heavy:
                if self.uploads >= self.config.security_max_uploads:
                    return await reject(503, 'Rasm/video navbati band. Birozdan keyin qayta urinib ko‘ring.', 3)
                self.uploads += 1
                upload_slot = True
                lease = await self.store.acquire(uid)
                if lease is None:
                    return await limited(2, 'upload')

            async def guarded_send(message):
                nonlocal started
                if message['type'] == 'http.response.start':
                    if admin and message['status'] == 401:
                        await self.store.window('admin-fail:' + ip_key, 10, 900)
                        if await self.store.window('admin-fail:' + ip_key, 10, 900, False):
                            await self.store.window('admin-block:' + ip_key, 1, 900)
                    started = True
                    message['headers'] = list(message.get('headers', [])) + [(b'x-content-type-options', b'nosniff')]
                await send(message)

            # Bound chunked bodies too, before multipart parsing or JSON allocation.
            with SpooledTemporaryFile(max_size=MB) as body:
                try:
                    async with asyncio.timeout(60 if heavy else 15):
                        size = 0
                        while True:
                            part = await receive()
                            if part['type'] == 'http.disconnect':
                                return
                            chunk = part.get('body', b'')
                            size += len(chunk)
                            if size > cap:
                                return await reject(413, 'Yuborilayotgan ma’lumot hajmi juda katta.')
                            body.write(chunk)
                            if not part.get('more_body', False):
                                break
                        body.seek(0)
                        delivered = False

                        async def replay():
                            nonlocal delivered
                            if delivered:
                                return await receive()
                            chunk = body.read(65536)
                            more = body.tell() < size
                            delivered = not more
                            return {'type': 'http.request', 'body': chunk, 'more_body': more}

                        await self.app(scope, replay, guarded_send)
                except TimeoutError:
                    if not started:
                        await reject(504, 'So‘rov vaqti tugadi. Holatni tekshirib, qayta urinib ko‘ring.')
        finally:
            self.active -= 1
            if upload_slot:
                self.uploads -= 1
            if lease:
                await self.store.release(lease)
