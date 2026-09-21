const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
let now = 100000, calls = 0, status = 429, scope = 'message';
const context = {
  URL, Request, Response, Map,
  location: {href: 'https://app.test/', origin: 'https://app.test'},
  Date: {now: () => now},
  window: {fetch: async () => {
    calls++;
    return new Response('{}', {status, headers: {'Retry-After': '5', 'X-RateLimit-Scope': scope}});
  }},
};
vm.runInNewContext(fs.readFileSync('app/web/assets/security-client.js', 'utf8'), context);
(async () => {
  const fetch = context.window.fetch;
  assert.equal((await fetch('/api/message', {method: 'POST'})).status, 429);
  status = 200;
  assert.equal((await fetch('/api/direct/chats/123/messages', {method: 'POST'})).status, 429);
  assert.equal(calls, 1, 'No writes retried during cooldown');
  assert.equal((await fetch('/api/chat')).status, 200, 'Read requests remain available');
  now += 5001;
  assert.equal((await fetch('/api/message', {method: 'POST'})).status, 200);
  status = 429; scope = 'upload';
  await fetch('/api/photo/prepare', {method: 'POST'});
  status = 200;
  assert.equal((await fetch('/api/chat')).status, 200, 'Upload cooldown does not stop reads');
  const before = calls;
  assert.equal((await fetch('/api/message/image', {method: 'POST'})).status, 429);
  assert.equal(calls, before);
  console.log('security-client cooldown checks passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
