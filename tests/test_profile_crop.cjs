const {chromium}=require('playwright'),fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{const browser=await chromium.launch({headless:true,channel:'msedge'});try{
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setContent('<section id="profile"><div id="profileInfo"></div></section><input id="photo" type="file"><button id="pickPhoto"></button><p id="photoRequiredMessage"></p>');
 await page.evaluate(()=>{
  window.$=id=>document.getElementById(id);window.me={id:1,name:'Tester',usernames:[],avatar:'old'};window.profileRefresh=null;window.avatarCacheEpoch=0;
  window.avatar=()=>'';window.notice=()=>{};window.renderProfile=()=>{};window.avatarCacheStore=async()=>{};window.photo=async()=>{};
  window.api=async(path,data)=>{if(path==='photo/prepare'){const canvas=document.createElement('canvas');canvas.width=800;canvas.height=400;canvas.getContext('2d').fillRect(0,0,400,400);return {image:canvas.toDataURL()}}window.saved=data;return {name:data.name}};
 });
 const html=fs.readFileSync('app/web/index.html','utf8');
 const start=html.indexOf('const style = document.createElement',html.indexOf('/* Manual avatar crop'));
 const end=html.indexOf('\n})();',start);
 await page.addScriptTag({content:'(()=>{'+html.slice(start,end)+'})();'});
 await page.addScriptTag({content:fs.readFileSync('app/web/assets/profile-editor.js','utf8')});
 await page.click('#editProfile');
 const file={name:'test.png',mimeType:'image/png',buffer:Buffer.from('test')};
 await page.setInputFiles('#editAvatar',file);
 await page.locator('#cropConfirm:enabled').waitFor();
 assert(await page.locator('#cropModal').isVisible());
 await page.click('#cropCancel');assert(await page.locator('#profileEditor').isVisible());
 await page.setInputFiles('#editAvatar',file);await page.locator('#cropConfirm:enabled').waitFor();
 await page.click('#cropConfirm');await page.click('#saveProfileEdit');
 await page.waitForFunction(()=>!!window.saved);
 assert((await page.evaluate(()=>saved.avatar)).startsWith('data:image/jpeg;base64,'));
 assert.equal(await page.evaluate(()=>me.avatar),await page.evaluate(()=>saved.avatar));
 await page.setInputFiles('#photo',file);await page.locator('#cropConfirm:enabled').waitFor();await page.click('#cropConfirm');
 assert((await page.evaluate(()=>photo())).startsWith('data:image/png;base64,'));
 assert.deepEqual(errors,[]);console.log('PASS: profile crop confirm/cancel/save; registration crop preserved');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
