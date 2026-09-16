const assert=require('node:assert/strict'),fs=require('node:fs');
const {chromium}=require('playwright');
(async()=>{const browser=await chromium.launch({headless:true,channel:'msedge'});try{
const page=await browser.newPage({viewport:{width:384,height:650}}),errors=[];
page.on('pageerror',e=>errors.push(e.message));
let revision=0,rows=[],blocked=false;
const partner={id:2,name:'Partner',online:true};
await page.route('**/api/direct/**',async r=>{const p=new URL(r.request().url()).pathname,m=r.request().method();let d={ok:true};
if(p.endsWith('/presence'))d={ok:true};
else if(p.includes('/blocks/'))blocked=m==='POST';
else if(p.endsWith('/with/2'))d={chat_id:1};
else if(p.endsWith('/chats'))d={chats:[{id:1,partner,last_message:rows.at(-1),unread:1}],more:false};
else if(m==='POST'&&p.endsWith('/messages')){const body=r.request().postDataJSON();rows.push({id:rows.length+1,text:body.text,mine:true,created_at:new Date().toISOString(),revision:++revision});d=rows.at(-1)}
else if(m==='PATCH'){rows[0].text=r.request().postDataJSON().text;rows[0].is_edited=true;rows[0].revision=++revision}
else if(m==='DELETE'&&p.includes('/messages/')){rows[0].is_deleted=true;rows[0].revision=++revision}
else if(p.endsWith('/messages'))d={messages:rows,revision,more:false,partner,can_send:!blocked,blocked_by_me:blocked};
await r.fulfill({json:d})});
await page.route('http://example.test/',r=>r.fulfill({contentType:'text/html',body:'<html><body></body></html>'}));
await page.goto('http://example.test');
await page.setContent('<section id="instagram"><div id="userSearchResults"></div></section>');
await page.addScriptTag({content:`const me={registered:true},tg={initData:'test'};const esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;');const avatar=p=>'<div class="avatar">P</div>';const badgeMarkup=()=>'';const notice=()=>{};let renderUserSearchResults=rows=>{document.getElementById('userSearchResults').innerHTML=rows.map(p=>'<div class="direct-result">'+p.name+'</div>').join('')};`});
await page.addStyleTag({content:fs.readFileSync('app/web/assets/direct.css','utf8')});
await page.addScriptTag({content:fs.readFileSync('app/web/assets/direct.js','utf8')});
await page.evaluate(()=>renderUserSearchResults([{id:2,name:'Partner'}]));
await page.locator('.direct-result').click();await page.locator('#dmPartner strong').waitFor();
await page.locator('#dmInput').fill('hello');await page.locator('#dmForm button').click();
await page.locator('.dm-bubble').waitFor();assert.equal(await page.locator('.dm-text').textContent(),'hello');
await page.locator('.dm-bubble').click({button:'right'});await page.getByRole('button',{name:'Tahrirlash',exact:true}).click();
await page.locator('#dmInput').fill('changed');await page.locator('#dmForm button').click();
await page.waitForFunction(()=>document.querySelector('.dm-meta')?.textContent.includes('tahrirlangan'));
page.on('dialog',d=>d.accept());await page.locator('#dmMenu').click();await page.getByRole('button',{name:'Bloklash',exact:true}).click();
await page.waitForFunction(()=>document.getElementById('dmInput').disabled);
await page.locator('#dmMenu').click();await page.getByRole('button',{name:'Blokdan chiqarish',exact:true}).click();
await page.waitForFunction(()=>!document.getElementById('dmInput').disabled);
await page.locator('.dm-bubble').click({button:'right'});await page.getByRole('button',{name:'O‘chirish',exact:true}).click();
await page.waitForFunction(()=>!document.querySelector('.dm-bubble'));
await page.locator('#dmBack').click();assert.equal(await page.locator('#dmWindow').isVisible(),false);
assert.deepEqual(errors,[]);console.log('PASS: private chat open/send/edit/delete/block/unblock/back');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
