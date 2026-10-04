const {chromium}=require('playwright'),fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{const browser=await chromium.launch({headless:true,channel:'msedge'});try{
const page=await browser.newPage();await page.setContent('<div id="messages"></div>');
await page.addScriptTag({content:`const $=id=>document.getElementById(id);const avatar=()=>'<div class="avatar">?</div>';const esc=x=>x;`});
await page.addScriptTag({content:fs.readFileSync('app/web/assets/roulette.js','utf8')});
await page.evaluate(()=>chatRoulette.start());
assert(await page.evaluate(()=>chatRoulette.hold({name:'Vali'})));
const animation=await page.evaluate(()=>{const a=document.querySelector('.roulette-track').getAnimations()[0];return {duration:a.effect.getTiming().duration,iterations:a.effect.getTiming().iterations,frames:a.effect.getKeyframes()}});
// hold() has already supplied the real partner, so the loop becomes a landing.
assert.equal(animation.duration,600);assert.equal(animation.iterations,1);
assert.equal(await page.locator('#roulette button').count(),0);
await page.evaluate(()=>{window.opened=false;chatRoulette.ready({name:'Vali'}).then(()=>window.opened=true)});
assert.equal(await page.evaluate(()=>window.opened),false);
await page.waitForFunction(()=>window.opened);
assert.equal(await page.evaluate(()=>chatRoulette.hold({name:'Vali'})),false);
await page.evaluate(()=>chatRoulette.reset());assert.equal(await page.locator('#roulette').isVisible(),false);
assert.equal(await page.evaluate(()=>chatRoulette.hold({name:'Vali'})),false);
await page.evaluate(async()=>{chatRoulette.start();const wait=chatRoulette.ready({name:'Vali'});chatRoulette.reset();await wait});
console.log('PASS: confirmed partner landing and cancellation');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
