const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const html=fs.readFileSync('app/web/index.html','utf8');
const code=html.slice(html.indexOf('let chatEpoch='),html.indexOf("$('invite').onclick="));
const nodes={};
function $(id){return nodes[id]??=( {hidden:false,value:'',checked:false,innerHTML:'',children:[],replaceChildren(){this.children=[];this.innerHTML=''},append(el){this.children.push(el)}} )}
let response, pending=null;
const calls=[];
const ctx=vm.createContext({$,document:{hidden:false,createElement:()=>({})},me:{registered:true,name:'Me'},match:null,after:0,polling:false,searchOptions:{accepted:true,mode:'anonymous'},
  api:async(path,body)=>{calls.push([path,body]);if(path.startsWith('chat?'))return pending?pending:response;return {ok:true}},
  run:async fn=>fn(),notice:()=>{},show:()=>{},t:x=>x,esc:x=>x,badgeMarkup:()=>'',avatar:p=>p.anonymous?'MASK':p.name,prompt:()=>''});
vm.runInContext(code,ctx);
const active=(anon=false)=>({status:'active',match:5,own_anonymous:false,partner:{name:'Partner',anonymous:anon},messages:[{id:1,text:'old message',mine:false}]});
(async()=>{
  response=active(true);await ctx.poll();assert.equal($('messages').children.length,1);assert($('reveal').innerHTML.includes('MASK'));
  response=active(false);await ctx.poll();assert(!$('reveal').innerHTML.includes('MASK'));assert.equal($('messages').children.length,1);
  response={status:'idle'};await ctx.poll();assert.equal($('messages').children.length,0);assert.equal(ctx.after,0);assert.equal($('reveal').innerHTML,'');
  response=active(false);await ctx.poll();let resolve;
  pending=new Promise(r=>resolve=r);const oldPoll=ctx.poll();
  response={status:'searching'};await $('next').onclick();assert.equal($('messages').children.length,0);
  resolve(active(true));await oldPoll;pending=null;
  assert.equal($('messages').children.length,0);assert.equal(ctx.match,null);
  await ctx.poll();assert.equal($('messages').children.length,0);
  $('anonymousMode').checked=false;await $('anonymousMode').onchange();
  await new Promise(r=>setImmediate(r));assert(calls.some(([path,body])=>path==='chat/privacy'&&body.anonymous===false));
  assert.equal(ctx.searchOptions.mode,'open');
  console.log('PASS: privacy refresh, duplicate prevention, ended chat cleanup and late response protection');
})().catch(e=>{console.error(e);process.exitCode=1});
