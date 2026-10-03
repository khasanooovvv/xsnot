const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const html=fs.readFileSync('app/web/index.html','utf8');
const source=html.slice(html.indexOf('let verificationOpenVersion=0;'),html.indexOf('function closeVerification()'));
async function test(status,fail=false){
  const nodes={videoForm:{hidden:true},verificationStatus:{textContent:'',append(node){this.retry=node}}};
  const dialog={open:false,showModal(){this.open=true}};
  const entry={};let cameras=0,loads=0;
  const context={verificationEntry:entry,verificationDialog:dialog,
    verificationCamera:{cancel(){},open(){cameras++}},$:id=>nodes[id],notice(){},
    document:{createElement:()=>({remove(){}})},
    async loadVerification(){loads++;if(fail)throw Error('Network error');nodes.videoForm.hidden=['pending','approved'].includes(status);nodes.verificationStatus.textContent=status}
  };
  vm.runInNewContext(source,context);
  await entry.onclick();
  assert.equal(dialog.open,true);
  assert.equal(loads,1);
  assert.equal(cameras,0,'Opening the dialog must not request camera permission');
  if(fail){assert.match(nodes.verificationStatus.textContent,/yuklab bo‘lmadi/);assert.equal(nodes.verificationStatus.retry.textContent,'Qayta urinish')}
  else assert.equal(nodes.videoForm.hidden,['pending','approved'].includes(status));
}
(async()=>{for(const status of ['none','rejected','pending','approved'])await test(status);await test('none',true);console.log('PASS: DM verification loads status, shows eligible form and handles errors without requesting camera')})().catch(error=>{console.error(error);process.exitCode=1});
