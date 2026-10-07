const assert=require('node:assert/strict'),fs=require('node:fs');
const css=fs.readFileSync('app/web/assets/dating.css','utf8');
const js=fs.readFileSync('app/web/assets/dating.js','utf8');
const html=fs.readFileSync('app/web/index.html','utf8');
assert(html.includes('/assets/dating.css?v=photo-overlay-2'));
assert(html.includes('/assets/dating.js?v=photo-overlay-2'));
const routes=fs.readFileSync('app/dating.py','utf8');
for(const [file,type] of [['dating.js','application/javascript'],['dating.css','text/css']]){
  assert(routes.includes("'web/assets/"+file+"', media_type='"+type+"', headers={'Cache-Control': 'no-cache'}"),'Dating assets must revalidate browser cache');
}
assert(!css.includes('nav#nav'),'Dating styles must not modify bottom navigation');
assert(!css.includes('58dvh')&&!css.includes('100dvh - 320px'),'Old card height overrides must be removed');
assert(css.includes('#dating .dating-copy{position:absolute;bottom:96px'));
assert(css.includes('#dating .dating-actions{position:absolute;bottom:18px'));
assert(js.includes('dating-photo-bars'));
assert(js.includes('class="like" aria-label="Yoqtirish"'));
assert(js.includes("api('dating/vote/'+p.id,{liked:!!i})"),'Voting behavior must remain unchanged');
console.log('PASS: dating-only overlay layout and existing vote behavior');
