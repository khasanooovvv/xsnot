const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
class Element{
 constructor(){this.children=[];this.attrs={};this.style={};this.events={};this.classes=new Set();this.classList={add:(...v)=>v.forEach(x=>this.classes.add(x)),remove:(...v)=>v.forEach(x=>this.classes.delete(x)),contains:x=>this.classes.has(x),toggle:(x,on)=>on?this.classes.add(x):this.classes.delete(x)};}
 set innerHTML(value){this.markup=value;this.children=[];this.svg=new Element();this.firstChild=this.svg;}
 get innerHTML(){return this.markup;}
 append(...children){children.forEach(c=>{c.parentNode=this;this.children.push(c);});}
 prepend(c){this.children.unshift(c);}
 setAttribute(k,v){this.attrs[k]=v;}
 getAttribute(k){return this.attrs[k];}
 removeAttribute(k){delete this.attrs[k];}
 addEventListener(k,v,capture=false){const key=capture?k+'Capture':k;this.events[key]=v;}
 querySelector(q){return q==='svg'?this.svg:null;}
 remove(){this.parentNode.children=this.parentNode.children.filter(x=>x!==this);}
}
const nav=new Element(),pages=['dating','home','instagram','leaders','profile'],buttons=pages.map(()=>new Element());
const handlers=buttons.map((b,i)=>b.onclick=()=>i);buttons[1].classList.add('selected');
nav.querySelector=q=>buttons[pages.findIndex(p=>q.includes('"'+p+'"'))];
const body=new Element();
const context={document:{body,getElementById:()=>nav,createElement:()=>new Element()},me:{avatar:null},MutationObserver:class{observe(){}},renderProfile:()=>42,syncDirectIcon(){},syncRouletteIcon(){},syncLeaderboardIcon(){},syncProfileIcon(){}};
vm.createContext(context);vm.runInContext(fs.readFileSync('app/web/assets/navigation.js','utf8'),context);
buttons.forEach((b,i)=>assert.equal(b.onclick,handlers[i],'Original navigation handler must remain'));
 buttons.forEach(b=>assert(b.classList.contains('major-nav-control'),'Navigation must be isolated from legacy button styles'));
 const theme=fs.readFileSync('app/web/assets/theme.css','utf8');
 assert.match(theme,/html,html \*\{-webkit-tap-highlight-color:transparent\}/,'Touch highlights must be disabled throughout the Mini App, including labels and switches');
 assert(theme.includes('button:not(.major-nav-control){position:relative;overflow:hidden;'), 'Legacy rounded rectangle style must exclude capsule controls');
 assert(!theme.includes('nav#nav button'), 'Old navigation selectors must not target the new capsule');
assert.match(buttons[2].innerHTML,/>Chat</);assert.equal(nav.children[0].children.length,5);
const navigationCss=fs.readFileSync('app/web/assets/navigation.css','utf8');
assert(!navigationCss.includes('dm-flight'),'Obsolete diagonal flight animation must be removed');
assert.equal((navigationCss.match(/\.turn \.dm-plane\{animation:/g)||[]).length,1,'Plane must have a single animation rule');
assert.match(navigationCss,/@keyframes dm-airflow\{0%,100%\{transform:translateX\(0\)\}30%\{transform:translateX\(-3px\)\}70%\{transform:translateX\(3px\)\}\}/,'Plane must move horizontally and return to center');
assert.match(navigationCss,/nav#nav\.major-nav,nav#nav\.major-nav \*\{-webkit-tap-highlight-color:transparent\}/,'Mobile tap overlay must be disabled only within navigation');
assert(navigationCss.includes('button:focus-visible{outline:2px solid #62b9ee'),'Keyboard focus must remain visible');
context.me.avatar='data:image/png;base64,test';context.syncProfileIcon();
const profile=buttons[4],image=profile.children[0];assert.equal(image.src,context.me.avatar);assert.equal(image.hidden,true);
image.onload();assert.equal(image.hidden,false);assert.equal(profile.svg.attrs.hidden,'');
image.onerror();assert.equal(profile.children.length,0);assert.equal(profile.svg.attrs.hidden,undefined);
assert.equal(context.renderProfile(),42);
buttons[2].events.click();assert(buttons[2].classList.contains('turn'));
const selections=[];
context.Telegram={WebApp:{HapticFeedback:{selectionChanged:()=>selections.push('selection')}}};
buttons.forEach(b=>{b.events.clickCapture();b.events.click();});
assert.deepEqual(selections,Array(5).fill('selection'),'All five buttons must trigger one selection haptic');
assert.equal(body.children.length,0,'Temporary diagnostics must be removed');
context.Telegram.WebApp.HapticFeedback.selectionChanged=()=>{throw new Error('Unsupported client');};
assert.doesNotThrow(()=>{buttons[2].events.clickCapture();buttons[2].events.click();});
assert(buttons[2].classList.contains('turn'),'Animation must survive haptic failure');
context.Telegram={WebApp:{isVersionAtLeast:()=>false,HapticFeedback:{selectionChanged:()=>assert.fail('Unsupported API must not be called')}}};
assert.doesNotThrow(()=>buttons[0].events.clickCapture());
delete context.Telegram;
assert.doesNotThrow(()=>profile.events.clickCapture(),'Navigation must work outside Telegram');
console.log('PASS: navigation, avatar fallback, animations and selection haptics without diagnostics');
