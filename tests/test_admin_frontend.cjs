const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('app/web/admin.html','utf8');
const script=html.split('<script>')[1].split('</script>')[0];new vm.Script(script);
const source=script.slice(script.indexOf('async function api('),script.indexOf('\nasync function run('));
(async()=>{
 let request;
 const context=vm.createContext({fetch:async(path,options)=>{request={path,options};return {ok:true,status:200,text:async()=>'{"ok":true}'}}});
 vm.runInContext(source,context);
 await context.api('/users/6322372175/verify',{verified:false});
 assert.equal(request.options.method,'POST');assert.equal(request.options.credentials,'same-origin');assert.deepEqual(JSON.parse(request.options.body),{verified:false});
 context.fetch=async()=>({ok:false,status:500,text:async()=>'Internal Server Error'});
 await assert.rejects(context.api('/reports'),e=>e.message.includes('500'));
 const escaped=script.slice(script.indexOf('const esc='),script.indexOf('\nfunction notify'));
 vm.runInContext(escaped+'\nglobalThis.result=esc("<img src=x onerror=alert(1)>");',context);
 assert.ok(!context.result.includes('<img'));
 console.log('PASS: admin script, mutation payload, auth credentials, server errors, HTML escaping');
})().catch(e=>{console.error(e);process.exitCode=1});
