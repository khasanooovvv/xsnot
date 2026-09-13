const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('app/web/index.html', 'utf8');
const script = html.split('<script>').pop().split('</script>')[0];
new vm.Script(script);
const apiSource = script.slice(script.indexOf('async function api('), script.indexOf('\nfunction show('));
async function test(status, raw, expected) {
  const context = vm.createContext({tg:{initData:'test'}, fetch:async()=>({status,ok:status===200,text:async()=>raw})});
  vm.runInContext(apiSource, context);
  if (expected) await assert.rejects(context.api('me'), e => e.message.includes(expected));
  else assert.equal((await context.api('me')).registered, true);
}
(async()=>{
  await test(500, 'Internal Server Error', 'Serverda xato');
  await test(502, '<html>Bad Gateway</html>', '502');
  await test(401, '{"detail":"Session expired"}', 'Session expired');
  await test(200, '{"registered":true}');
  assert.ok(html.includes("show('errorState')"));
  console.log('PASS: API errors, valid JSON, script syntax, and dedicated error screen');
})().catch(e=>{console.error(e);process.exitCode=1});
