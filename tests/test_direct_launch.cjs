const {chromium}=require('playwright'),fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('http://launch.test/**',async r=>{
   const url=new URL(r.request().url());
   if(url.pathname==='/')return r.fulfill({contentType:'text/html',body:'<section id="instagram"><div id="userSearchResults"></div></section>'});
   let data={ok:true};
   if(url.pathname==='/api/direct/chats/99/messages')data={partner:{id:2,name:'Sherzod'},messages:[],revision:0,more:false,can_send:true};
   if(url.pathname==='/api/direct/chats')data={chats:[],more:false};
   return r.fulfill({json:data});
  });
  await page.goto('http://launch.test/?v=1&dm_chat=99');
  await page.addScriptTag({content:`const me={id:1,registered:true},tg={initData:'test'};const esc=s=>String(s??'');const avatar=()=>'';const badgeMarkup=()=>'';const notice=()=>{};let renderUserSearchResults=()=>{};async function avatarCacheStore(){return null}`});
  await page.addScriptTag({content:fs.readFileSync('app/web/assets/direct.js','utf8')});
  await page.locator('#dmPartner strong').waitFor();
  assert.equal(await page.locator('#dmPartner strong').textContent(),'Sherzod');
  assert.equal(await page.locator('#dmWindow').isVisible(),true);
  assert.deepEqual(errors,[]);console.log('PASS: notification link opens requested chat');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
