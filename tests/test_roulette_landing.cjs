const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
let now=1;
const timers=[];
const track={children:[],style:{},append(node){this.children.push(node)},replaceChildren(){this.children=[]},animate(){return {cancel(){}}}};
const status={textContent:''},viewport={clientWidth:384};
const panel={hidden:true,querySelector(selector){return selector==='.roulette-track'?track:selector==='.roulette-window'?viewport:status}};
let divs=0;
const scope=vm.createContext({window:{roulettePeople:[{name:'Preview'}]},document:{head:{append(){}},body:{classList:{add(){}}},createElement(tag){return tag==='div'&&divs++===0?panel:{}}},
  $:()=>({before(){}}),avatar:p=>p.anonymous?'MASK':'AVATAR',esc:x=>x,badgeMarkup:()=>'',performance:{now:()=>now},matchMedia:()=>({matches:false}),
  setTimeout(fn,delay){timers.push({fn,delay});return timers.length},clearTimeout(){}});
vm.runInContext(fs.readFileSync('app/web/assets/roulette.js','utf8'),scope);
(async()=>{
  const roulette=scope.window.chatRoulette;
  roulette.start();
  assert(track.children[24].innerHTML.includes('Qidirilmoqda'));
  roulette.setPeople([{name:'Offline preview'}]);
  assert(!track.children[24].innerHTML.includes('Offline preview'));
  now=5000;
  let opened=false;
  const ready=roulette.ready({name:'Actual partner'}).then(()=>opened=true);
  assert(track.children[24].innerHTML.includes('Actual partner'));
  assert.equal(opened,false);
  assert.equal(timers.at(-1).delay,600);
  now+=600;timers.at(-1).fn();await ready;
  assert.equal(opened,true);
  assert.equal(roulette.hold({name:'Actual partner'}),false);
  roulette.reset();assert.equal(panel.hidden,true);
  console.log('PASS: no preview landing, confirmed late match, reset');
})().catch(error=>{console.error(error);process.exitCode=1});
