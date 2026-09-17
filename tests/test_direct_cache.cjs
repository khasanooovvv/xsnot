const {chromium}=require('playwright'),fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  let release;const gate=new Promise(r=>release=r);let lightweight=false;
  const data={chats:[{id:1,partner:{id:2,name:'Cached friend',online:false,avatar:null},unread:0}],more:false};
  await page.route('http://cache.test/',r=>r.fulfill({contentType:'text/html',body:'<section id="instagram"><div id="userSearchResults"></div></section><button data-page="instagram">Chats</button>'}));
  await page.route('**/api/direct/**',async r=>{
   const u=new URL(r.request().url());
   if(u.pathname.endsWith('/presence')){await gate;return r.fulfill({json:{ok:true}})}
   if(u.pathname.endsWith('/chats')){
    if(u.searchParams.get('include_avatar')==='false')lightweight=true;
    await gate;return r.fulfill({json:data});
   }
   await r.fulfill({json:{ok:true}});
  });
  await page.goto('http://cache.test/');
  await page.evaluate(cached=>{
   window.me={id:1,registered:true};window.tg={initData:'test'};
   window.avatar=()=>'<span class="avatar"></span>';window.badgeMarkup=()=>'';window.esc=x=>String(x??'');window.notice=()=>{};window.renderUserSearchResults=()=>{};
   window.avatarCacheStore=async(action,key,value)=>action==='get'?cached:null;
  },data);
  await page.addScriptTag({content:fs.readFileSync('app/web/assets/direct.js','utf8')});
  await page.locator('.dm-row').waitFor({timeout:2000});
  assert.equal(await page.locator('.dm-row strong').textContent(),'Cached friend');
  await page.evaluate(()=>window.originalRow=document.querySelector('.dm-row'));
  release();
  await page.waitForTimeout(300);
  await page.locator('[data-page="instagram"]').click();
  await page.waitForTimeout(300);
  assert(lightweight);assert(await page.evaluate(()=>originalRow===document.querySelector('.dm-row')));
  assert.deepEqual(errors,[]);
  console.log('PASS: cached list before network, lightweight refresh, unchanged row retained');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
