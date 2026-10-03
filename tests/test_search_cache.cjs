const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const html=fs.readFileSync('app/web/index.html','utf8');
const source=html.slice(html.indexOf('let userSearchTimer='),html.indexOf("$('userSearchForm').onsubmit"));
const input={value:'Test'},box={innerHTML:''};
let calls=0,rendered;
const context=vm.createContext({Map,Date,AbortController,clearTimeout,encodeURIComponent,
  $:id=>id==='userSearchInput'?input:box,tg:{initData:'test'},
  renderUserSearchResults:rows=>{rendered=rows},notice:message=>{throw Error(message)},
  fetch:async(url,options)=>{calls++;assert.equal(options.headers['X-Telegram-Init-Data'],'test');return {ok:true,json:async()=>[{name:'Test'}]}}
});
vm.runInContext(source,context);
(async()=>{
  await vm.runInContext('searchUsers()',context);
  assert.equal(rendered[0].name,'Test');
  input.value='@TEST';
  await vm.runInContext('searchUsers()',context);
  assert.equal(calls,1,'normalized repeat query should use cache');
  input.value='';await vm.runInContext('searchUsers()',context);
  assert.equal(box.innerHTML,'');
  console.log('Search cache, normalization and empty input passed');
})().catch(error=>{console.error(error);process.exitCode=1});
