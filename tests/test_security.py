"""Exercise early protection without a database or a live Redis dependency."""
import asyncio
import hashlib
import hmac
import json
import time
from types import SimpleNamespace
from urllib.parse import urlencode
from unittest.mock import patch

import httpx
import pytest
from starlette.responses import JSONResponse

from app.security import LimitStore, SecurityMiddleware, body_limit, policy, verified_uid
from app.security import client_ip


@pytest.mark.parametrize('value', [b'garbage', b'1.2.3.4,5.6.7.8', b'1.2.3.4:80', b'fe80::1%eth0', b'\xff'])
def test_invalid_real_ip_rejected_in_edge_mode(value):
    scope = {'client': ('100.64.0.1', 1234), 'headers': [(b'x-real-ip', value)]}
    with pytest.raises(ValueError):
        client_ip(scope, True)


def test_real_ip_trust_and_normalization():
    scope = {'client': ('100.64.0.1', 1234), 'headers': [(b'x-real-ip', b'::ffff:203.0.113.7')]}
    assert client_ip(scope, True) == '203.0.113.7'
    assert client_ip(scope, False) == '100.64.0.1'
    scope['headers'].append((b'x-real-ip', b'203.0.113.8'))
    with pytest.raises(ValueError):
        client_ip(scope, True)
    scope['headers'] = [(b'x-forwarded-for', b'203.0.113.7')]
    with pytest.raises(ValueError):
        client_ip(scope, True)


@pytest.mark.asyncio
async def test_rotating_trusted_proxies_share_client_budget_without_blocking_other_clients():
    async def forbidden(*args):
        pytest.fail('Unsigned request reached app')
    config = SimpleNamespace(redis_url='', bot_token='test-token', security_max_concurrent=100,
                             security_max_uploads=4, railway_environment_id='production',
                             railway_public_domain='test.up.railway.app')
    app = SecurityMiddleware(forbidden, config, store())
    for i in range(45):
        peer = f'100.64.{i // 20}.{i % 20 + 1}'
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=(peer, 1234)), base_url='http://test') as client:
            r = await client.get('/api/me', headers={'X-Real-IP': '203.0.113.7'})
            assert r.status_code == (401 if i < 30 else 429)
    assert r.headers['Retry-After'] == '300'
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=('100.64.0.1', 1234)), base_url='http://test') as client:
        assert (await client.get('/api/me', headers={'X-Real-IP': '203.0.113.8'})).status_code == 401


@pytest.mark.asyncio
async def test_untrusted_client_cannot_rotate_real_ip_to_bypass_limit():
    app = middleware(echo)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=('203.0.113.9', 1234)), base_url='http://test') as client:
        for i in range(31):
            r = await client.get('/api/me', headers={'X-Real-IP': f'198.51.100.{i}', 'X-Railway-Edge': 'fake', 'X-Forwarded-For': '100.64.0.1'})
            assert r.status_code == (401 if i < 30 else 429)


def test_proxy_trust_disabled_outside_railway():
    app = middleware(echo)
    assert app.railway_edge is False


def test_tcp_bypass_refuses_edge_trust_and_operator_can_disable():
    config = SimpleNamespace(redis_url='', railway_environment_id='prod',
                             railway_public_domain='test.up.railway.app',
                             railway_tcp_proxy_domain='bypass.proxy.rlwy.net')
    with pytest.raises(ValueError, match='no TCP proxy'):
        SecurityMiddleware(echo, config, store())
    config.security_trust_railway_edge = False
    assert SecurityMiddleware(echo, config, store()).railway_edge is False


@pytest.mark.asyncio
async def test_missing_edge_header_rejected_before_app_and_counters():
    app = middleware(echo)
    app.railway_edge = True
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        assert (await client.get('/api/me')).status_code == 400
        assert (await client.get('/api/me', headers=[('X-Real-IP', '203.0.113.1'), ('X-Real-IP', '203.0.113.2')])).status_code == 400
    assert not app.store.local
    assert app.active == 0


def signed(uid=1):
    data = {'auth_date': str(int(time.time())), 'user': json.dumps({'id': uid})}
    secret = hmac.new(b'WebAppData', b'test-token', hashlib.sha256).digest()
    data['hash'] = hmac.new(secret, '\n'.join(f'{k}={v}' for k, v in sorted(data.items())).encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


def store():
    result = LimitStore('redis://localhost:6379/15')
    result.offline_until = float('inf')
    return result


def middleware(app, limits=None):
    return SecurityMiddleware(app, SimpleNamespace(redis_url='', bot_token='test-token', security_max_concurrent=100, security_max_uploads=4), limits or store())


async def echo(scope, receive, send):
    size = 0
    while True:
        message = await receive()
        size += len(message.get('body', b''))
        if not message.get('more_body'):
            break
    await JSONResponse({'size': size})(scope, receive, send)


@pytest.mark.asyncio
async def test_shared_message_budget_and_user_isolation():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=middleware(echo)), base_url='http://test') as client:
        for i in range(10):
            path = '/api/message' if i % 2 else '/api/direct/chats/123/messages'
            assert (await client.post(path, headers={'X-Telegram-Init-Data': signed()})).status_code == 200
        r = await client.post('/api/message', headers={'X-Telegram-Init-Data': signed()})
        assert r.status_code == 429
        assert 1 <= int(r.headers['Retry-After']) <= 5
        assert r.headers['X-RateLimit-Scope'] == 'message'
        assert (await client.get('/api/chat', headers={'X-Telegram-Init-Data': signed()})).status_code == 200
        assert (await client.post('/api/message', headers={'X-Telegram-Init-Data': signed(2)})).status_code == 200


@pytest.mark.asyncio
async def test_invalid_auth_before_body_or_application_and_forwarded_ip_spoof():
    async def forbidden(*args):
        pytest.fail('Unauthenticated request reached the app')
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=middleware(forbidden)), base_url='http://test') as client:
        for i in range(30):
            r = await client.post('/api/photo/prepare', headers={'X-Forwarded-For': f'1.2.3.{i}'})
            assert r.status_code == 401
        r = await client.post('/api/photo/prepare')
        assert r.status_code == 429
        assert r.headers['Retry-After'] == '300'


@pytest.mark.asyncio
async def test_body_limits_include_chunked_requests_and_profile_exception():
    async def chunks():
        yield b'x' * 40000
        yield b'x' * 40000
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=middleware(echo)), base_url='http://test', headers={'X-Telegram-Init-Data': signed()}) as client:
        assert (await client.post('/api/message', content=b'x' * 65537)).status_code == 413
        assert (await client.post('/api/message', content=chunks())).status_code == 413
        r = await client.post('/api/profile', content=b'x' * 100000)
        assert r.status_code == 200 and r.json()['size'] == 100000


@pytest.mark.asyncio
async def test_upload_concurrency_released_after_completion():
    limits = store()
    a, b = await limits.acquire(1), await limits.acquire(1)
    assert a and b and await limits.acquire(1) is None
    await limits.release(a)
    c = await limits.acquire(1)
    assert c
    await limits.release(b)
    await limits.release(c)
    assert limits.leases == {}


@pytest.mark.asyncio
async def test_window_expiry_and_bounded_fallback():
    limits = store()
    with patch('app.security.time.monotonic', return_value=100):
        assert await limits.window('key', 1, 5) == 0
        assert await limits.window('key', 1, 5) == 5
    with patch('app.security.time.monotonic', return_value=106):
        assert await limits.window('key', 1, 5) == 0
    for i in range(10010):
        await limits.window(f'key{i}', 1, 5)
    assert len(limits.local) == 10000


@pytest.mark.asyncio
async def test_admin_failed_login_block():
    async def unauthorized(scope, receive, send):
        await JSONResponse({}, status_code=401)(scope, receive, send)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=middleware(unauthorized)), base_url='http://test') as client:
        for _ in range(10):
            assert (await client.get('/admin')).status_code == 401
        r = await client.get('/users/123')
        assert r.status_code == 429 and int(r.headers['Retry-After']) >= 899


@pytest.mark.asyncio
async def test_server_concurrency_and_exception_cleanup():
    started, finish = asyncio.Event(), asyncio.Event()
    async def slow(scope, receive, send):
        started.set()
        await finish.wait()
        await echo(scope, receive, send)
    app = middleware(slow)
    app.config.security_max_concurrent = 1
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test', headers={'X-Telegram-Init-Data': signed()}) as client:
        pending = asyncio.create_task(client.get('/api/chat'))
        await started.wait()
        assert (await client.get('/api/chat')).status_code == 503
        finish.set()
        assert (await pending).status_code == 200
        assert app.active == 0


def test_authentication_and_policy():
    value = signed()
    assert verified_uid(value, 'test-token') == 1
    assert verified_uid(value, 'wrong-token') is None
    assert verified_uid(value + '&auth_date=1', 'test-token') is None
    assert verified_uid('x' * 20000, 'test-token') is None
    assert policy('/api/direct/chats/1/messages', 'GET') == policy('/api/direct/chats/2/messages', 'GET')
    assert body_limit('/api/verification/submit') > 15 * 1024 * 1024


@pytest.mark.asyncio
async def test_redis_atomic_windows_and_cross_worker_upload_leases():
    import fakeredis.aioredis
    import fakeredis
    server = fakeredis.FakeServer()
    a, b = store(), store()
    for limits in (a, b):
        limits.redis = fakeredis.aioredis.FakeRedis(server=server)
        limits.offline_until = 0
    results = await asyncio.gather(*( (a if i % 2 else b).window('shared', 10, 60) for i in range(25)))
    assert results.count(0) == 10
    assert all(1 <= r <= 60 for r in results if r)
    one, two = await a.acquire(123), await b.acquire(123)
    assert one and two and await a.acquire(123) is None
    await b.release(one)
    three = await a.acquire(123)
    assert three
    await a.release(two)
    await a.release(three)
    await a.redis.aclose()
    await b.redis.aclose()


@pytest.mark.asyncio
async def test_real_fastapi_multipart_photo_flow():
    import base64
    import io
    import os
    os.environ.setdefault('BOT_TOKEN', '123:test')
    from fastapi import FastAPI
    from PIL import Image
    from app import miniapp
    app = FastAPI()
    app.include_router(miniapp.router)
    app.dependency_overrides[miniapp.identity] = lambda: 1
    image = io.BytesIO()
    Image.new('RGB', (3000, 100), 'red').save(image, format='PNG')
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=middleware(app)), base_url='http://test', headers={'X-Telegram-Init-Data': signed()}) as client:
        for _ in range(6):
            r = await client.post('/api/photo/prepare', files={'image': ('photo.png', image.getvalue(), 'image/png')})
            assert r.status_code == 200, r.text
        prepared = Image.open(io.BytesIO(base64.b64decode(r.json()['image'].split(',')[1])))
        assert prepared.width == 2048
        assert (await client.post('/api/photo/prepare', files={'image': ('photo.png', image.getvalue(), 'image/png')})).status_code == 429


@pytest.mark.asyncio
async def test_redis_outage_keeps_local_limits_and_backs_off():
    from unittest.mock import AsyncMock
    from redis.exceptions import ConnectionError
    limits = store()
    limits.offline_until = 0
    limits.redis.eval = AsyncMock(side_effect=ConnectionError('offline'))
    assert await limits.window('outage', 1, 60) == 0
    assert await limits.window('outage', 1, 60) > 0
    assert limits.redis.eval.await_count == 1


@pytest.mark.asyncio
async def test_timeout_releases_upload_and_server_slots():
    original_timeout = asyncio.timeout
    async def slow(scope, receive, send):
        await asyncio.sleep(1)
    app = middleware(slow)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test', headers={'X-Telegram-Init-Data': signed()}) as client:
        with patch('app.security.asyncio.timeout', side_effect=lambda seconds: original_timeout(0.01)):
            r = await client.post('/api/photo/prepare', content=b'photo')
        assert r.status_code == 504
        assert app.active == app.uploads == 0
        assert app.store.leases == {}
