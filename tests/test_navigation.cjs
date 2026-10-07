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
const impacts=[];
const nativeEvents=[];
context.TelegramWebviewProxy={postEvent:(name,payload)=>nativeEvents.push([name,JSON.parse(payload)])};
buttons.forEach(b=>b.events.clickCapture());
assert.equal(nativeEvents.length,5,'Android native bridge must receive one event per button');
nativeEvents.forEach(([name,payload])=>{assert.equal(name,'web_app_trigger_haptic_feedback');assert.deepEqual(payload,{type:'impact',impact_style:'light'});});
delete context.TelegramWebviewProxy;
context.Telegram={WebApp:{HapticFeedback:{impactOccurred:style=>impacts.push(style)}}};
buttons.forEach(b=>{b.events.clickCapture();b.events.click();});
assert.deepEqual(impacts,['light','light','light','light','light'],'Each of the five buttons must trigger exactly one light impact');
const vibrations=[];context.navigator={vibrate:duration=>vibrations.push(duration)};
context.Telegram.WebApp.HapticFeedback.impactOccurred=()=>{throw new Error('Unsupported client');};
assert.doesNotThrow(()=>{buttons[2].events.clickCapture();buttons[2].events.click();},'Haptic failure must not interrupt navigation');
assert.deepEqual(vibrations,[15],'Failed Telegram haptics must use the vibration fallback');
assert(buttons[2].classList.contains('turn'),'Animation must still run after haptic failure');
delete context.Telegram;
assert.doesNotThrow(()=>{profile.events.clickCapture();profile.events.click();},'Navigation must work outside Telegram');
assert.deepEqual(vibrations,[15,15]);
context.Telegram={WebApp:{isVersionAtLeast:()=>false,HapticFeedback:{impactOccurred:()=>assert.fail('Unsupported API must not be called')}}};
buttons[0].events.clickCapture();assert.deepEqual(vibrations,[15,15,15]);
delete context.navigator;delete context.Telegram;
assert.doesNotThrow(()=>buttons[0].events.clickCapture(),'Clients without either vibration API must remain usable');
console.log('PASS: navigation handlers, labels, avatar loading/fallback and click animation');
const diagnostic=body.children[0],diagnosticText=diagnostic.children[0];
assert.match(diagnosticText.textContent,/HAPTIC DIAG v1/);
assert.match(diagnosticText.textContent,/vibrate API yoq/);
buttons[2].events.clickCapture({currentTarget:buttons[2]});
assert.match(diagnosticText.textContent,/\/ Chat/,'Diagnostics must identify the tapped button');
diagnostic.children[1].events.click();assert.equal(body.children.length,0,'Diagnostic panel must be dismissible');
