const {chromium}=require('playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  await page.setContent('<meta name="viewport" content="width=device-width, initial-scale=1"><section id="instagram"><form class="direct-box"><div class="direct-search-field"><span>⌕</span><input id="userSearchInput" placeholder="Username qidiring"></div></form></section>');
  await page.addStyleTag({content:fs.readFileSync('app/web/assets/theme.css','utf8')});
  await page.addStyleTag({content:fs.readFileSync('app/web/assets/direct.css','utf8')});
  await page.locator('#userSearchInput').tap();
  assert.equal(await page.locator('#userSearchInput').evaluate(n=>getComputedStyle(n).fontSize),'16px');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  console.log('PASS: mobile search font 16px; no horizontal overflow');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
