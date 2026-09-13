const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const page=fs.readFileSync('app/web/index.html','utf8');
const handler=page.slice(page.indexOf("$('copyInvite').onclick="),page.indexOf("\ndocument.querySelectorAll('nav button')"));
let copied,notice;
const nodes={copyInvite:{},inviteLink:{href:'https://t.me/testbot?start=ref_99'}};
const context=vm.createContext({$:id=>nodes[id],navigator:{clipboard:{writeText:async text=>{copied=text}}},notice:text=>notice=text,t:text=>text});
vm.runInContext(handler,context);
(async()=>{await nodes.copyInvite.onclick();assert.equal(copied,nodes.inviteLink.href);assert.equal(notice,'Havola nusxalandi.');context.navigator.clipboard.writeText=async()=>{throw Error('denied')};await nodes.copyInvite.onclick();assert.ok(notice.includes('Nusxalash ishlamadi'));console.log('PASS: clipboard success and permission failure');})().catch(e=>{console.error(e);process.exitCode=1});
