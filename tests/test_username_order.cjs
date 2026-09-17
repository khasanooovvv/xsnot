const {chromium}=require('playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try {
  const page=await browser.newPage();
  await page.setContent('<section id="profile"><div id="profileInfo"></div></section>');
  await page.evaluate(()=>{
   window.$=id=>document.getElementById(id);
   window.me={id:1,name:'Tester',verified:true,usernames:['telegram','ceo','iphone'],app_username:'telegram',avatar:'cached-photo'};
   window.saved=[];window.profileRefresh=null;window.avatarCacheEpoch=0;
   window.avatar=()=>'';window.notice=()=>{};
   window.renderProfile=()=>{$('profileInfo').textContent=me.usernames.join(',')};
   window.api=async(path,data)=>{if(path!=='profile')throw Error('Unexpected request');saved.push(data);return {name:data.name,usernames:data.usernames,app_username:data.app_username}};
  });
  await page.addScriptTag({content:fs.readFileSync('app/web/assets/profile-editor.js','utf8')});
  await page.click('#editProfile');
  await page.click('.username-list-row');
  await page.locator('.order-down').first().click();
  await page.click('.order-save');
  assert.equal(await page.inputValue('#editUsername'),'@ceo\n@telegram\n@iphone');
  await page.click('#saveProfileEdit');
  assert.deepEqual(await page.evaluate(()=>saved.map(x=>x.usernames)),[['ceo','telegram','iphone'],['ceo','telegram','iphone']]);
  assert.equal(await page.evaluate(()=>me.avatar),'cached-photo');
  await page.click('#editProfile');await page.click('.username-list-row');
  assert.equal(await page.locator('.tg-row').first().getAttribute('data-username'),'ceo');
  await page.locator('.order-down').first().click();
  await page.click('.blank-window-close');
  await page.click('.username-list-row');
  assert.equal(await page.locator('.tg-row').first().getAttribute('data-username'),'ceo');
  console.log('PASS: reorder, parent save, reopen, cancel, avatar preserved');
 } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
