// Respect server cooldowns without resending a message or an upload automatically.
(() => {
  const original = window.fetch.bind(window), deadlines = new Map();
  function group(path, method) {
    if (method === 'GET') return path === '/api/users/search' ? 'user-search' : 'read:' + path.replace(/\/\d+(?=\/|$)/g, '/:id');
    if (path === '/api/message' || /^\/api\/direct\/chats\/\d+\/messages$/.test(path)) return 'message';
    if (path === '/api/message/image') return 'image';
    if (path === '/api/photo/prepare') return 'photo';
    if (['/api/search', '/api/roulette/spin'].includes(path)) return 'match-search';
    if (path.startsWith('/api/direct/chats/with/')) return 'open-chat';
    if (['/api/profile', '/api/profile/name', '/api/register'].includes(path)) return 'profile';
    if (path === '/api/verification/submit') return 'video';
    if (path === '/api/direct/presence' || path.endsWith('/read')) return 'presence-read';
    return 'other-write';
  }
  window.fetch = async function(input, options) {
    const url = new URL(input instanceof Request ? input.url : input, location.href);
    if (url.origin !== location.origin || !url.pathname.startsWith('/api/')) return original(input, options);
    const path = url.pathname.replace(/\/$/, ''), method = (options?.method || (input instanceof Request ? input.method : 'GET')).toUpperCase();
    const key = group(path, method), now = Date.now();
    for (const [name, until] of deadlines) if (until <= now) deadlines.delete(name);
    const uploadUntil = ['image', 'photo', 'profile', 'video'].includes(key) ? deadlines.get('upload') || 0 : 0;
    const wait = Math.ceil((Math.max(deadlines.get('all') || 0, deadlines.get(key) || 0, deadlines.get('auth') || 0, uploadUntil) - now) / 1000);
    if (wait > 0) return new Response(JSON.stringify({detail: `${wait} soniyadan keyin qayta urinib ko‘ring.`}), {status: 429, headers: {'Content-Type': 'application/json', 'Retry-After': String(wait)}});
    const response = await original(input, options);
    if (response.status === 429 || response.status === 503) {
      const seconds = Math.max(1, Math.min(900, Number(response.headers.get('Retry-After')) || 3));
      const scope = response.status === 503 ? 'all' : response.headers.get('X-RateLimit-Scope') || key;
      deadlines.set(scope, Date.now() + seconds * 1000);
    }
    return response;
  };
})();
