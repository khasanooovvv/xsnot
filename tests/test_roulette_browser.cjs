const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');
(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.BROWSER_CHANNEL ? {channel:process.env.BROWSER_CHANNEL} : {})});
  try {
    const page = await browser.newPage({viewport:{width:384,height:650}});
    let state='idle', spins=0, chooses=0, stops=0, empty=false, busy=false;
    const errors=[];
    page.on('pageerror', e=>errors.push(e.message));
    await page.route('**/*', async route => {
      const url=new URL(route.request().url());
      if(url.hostname!=='roulette.test') return route.abort();
      if(url.pathname.startsWith('/api/')) {
        let result={ok:true}, status=200;
        if(url.pathname==='/api/me') result={registered:true,name:'Test',language:'uz',archive_consent:true};
        if(url.pathname==='/api/chat') result=state==='active'?{status:state,match:1,partner:{name:'Aziza',anonymous:false},own_anonymous:false,messages:[]}:{status:state};
        if(url.pathname==='/api/search') {assert.equal(route.request().postDataJSON().roulette,true);state='searching';}
        if(url.pathname==='/api/stop') {state='idle';stops++;}
        if(url.pathname==='/api/roulette/spin') {spins++;result=empty?{items:[],ticket:null,selected:null}:{items:[{name:'Aziza',avatar:null,anonymous:false},{name:'Anonim',avatar:null,anonymous:true},{name:'Javohir',avatar:null,anonymous:false}],selected:0,ticket:'test-ticket'};}
        if(url.pathname==='/api/roulette/choose') {chooses++;assert.equal(route.request().postDataJSON().ticket,'test-ticket');if(busy){status=409;result={detail:'Bu suhbatdosh hozir band. Qayta aylantiring.'}}else state='active';}
        return route.fulfill({status,contentType:'application/json',body:JSON.stringify(result)});
      }
      const file=url.pathname==='/'?'app/web/index.html':path.join('app/web',url.pathname);
      if(fs.existsSync(file))return route.fulfill({path:file});
      return route.abort();
    });
    await page.addInitScript(()=>window.Telegram={WebApp:{initData:'test',ready(){},expand(){}}});
    await page.goto('http://roulette.test/');
    await page.waitForSelector('#home:visible');
    const search=()=>page.locator('#searchForm').evaluate(form=>form.requestSubmit());
    await search();
    await page.waitForSelector('.roulette-card.chosen');
    assert.equal(chooses,0);
    assert.equal(await page.locator('#chatBack').isVisible(),true);
    const position=await page.locator('.roulette-card.chosen').boundingBox();
    assert(Math.abs(position.x+position.width/2-192)<3);
    await page.screenshot({path:path.join(require('node:os').tmpdir(),'roulette-preview.png')});
    await page.locator('.roulette-retry').click();
    await page.waitForSelector('.roulette-card.chosen');
    assert.equal(spins,2);
    busy=true;
    await page.locator('.roulette-card.chosen').click();
    await page.waitForFunction(()=>document.querySelector('.roulette-status').textContent.includes('hozir band'));
    busy=false;
    await page.locator('.roulette-retry').click();
    await page.waitForSelector('.roulette-card.chosen');
    await page.locator('.roulette-card.chosen').click();
    await page.waitForSelector('body.chat-fullscreen');
    assert.equal(await page.locator('#roulette').isVisible(),false);
    assert.equal(await page.locator('#chatBack').isVisible(),false);
    await page.locator('#chatMenuToggle').click();
    await page.locator('#stop').click();
    await page.waitForSelector('#home:visible');
    empty=true;
    await search();
    await page.waitForFunction(()=>document.querySelector('.roulette-status').textContent.includes('Hozircha'));
    await page.locator('#chatBack').click();
    await page.waitForSelector('#home:visible');
    assert.equal(stops,2);
    assert.equal(state,'idle');
    assert.deepEqual(errors,[]);
    console.log('PASS: roulette movement, avatar selection, reroll, busy/empty states and back cancellation');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1});
