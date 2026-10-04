const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
class Element{
 constructor(){this.children=[];this.attrs={};this.style={};this.events={};this.classes=new Set();this.classList={add:(...v)=>v.forEach(x=>this.classes.add(x)),remove:(...v)=>v.forEach(x=>this.classes.delete(x)),contains:x=>this.classes.has(x),toggle:(x,on)=>on?this.classes.add(x):this.classes.delete(x)};}
 set innerHTML(value){this.markup=value;this.children=[];this.svg=new Element();this.firstChild=this.svg;}
 get innerHTML(){return this.markup;}
 append(...children){children.forEach(c=>{c.parentNode=this;this.children.push(c);});}
 prepend(c){this.children.unshift(c);}
 setAttribute(k,v){this.attrs[k]=v;}
 removeAttribute(k){delete this.attrs[k];}
 addEventListener(k,v){this.events[k]=v;}
 querySelector(q){return q==='svg'?this.svg:null;}
 remove(){this.parentNode.children=this.parentNode.children.filter(x=>x!==this);}
}
const nav=new Element(),pages=['dating','home','instagram','leaders','profile'],buttons=pages.map(()=>new Element());
const handlers=buttons.map((b,i)=>b.onclick=()=>i);buttons[1].classList.add('selected');
nav.querySelector=q=>buttons[pages.findIndex(p=>q.includes('"'+p+'"'))];
const context={document:{getElementById:()=>nav,createElement:()=>new Element()},me:{avatar:null},MutationObserver:class{observe(){}},renderProfile:()=>42,syncDirectIcon(){},syncRouletteIcon(){},syncLeaderboardIcon(){},syncProfileIcon(){}};
vm.createContext(context);vm.runInContext(fs.readFileSync('app/web/assets/navigation.js','utf8'),context);
buttons.forEach((b,i)=>assert.equal(b.onclick,handlers[i],'Original navigation handler must remain'));
assert.match(buttons[2].innerHTML,/>Chat</);assert.equal(nav.children[0].children.length,5);
context.me.avatar='data:image/png;base64,test';context.syncProfileIcon();
const profile=buttons[4],image=profile.children[0];assert.equal(image.src,context.me.avatar);assert.equal(image.hidden,true);
image.onload();assert.equal(image.hidden,false);assert.equal(profile.svg.attrs.hidden,'');
image.onerror();assert.equal(profile.children.length,0);assert.equal(profile.svg.attrs.hidden,undefined);
assert.equal(context.renderProfile(),42);
buttons[2].events.click();assert(buttons[2].classList.contains('turn'));
console.log('PASS: navigation handlers, labels, avatar loading/fallback and click animation');
