/* Exact expiry from the server, independent of the phone's clock. */
function goldRemaining(until, now) {
  const seconds = Math.max(0, Math.ceil((until - now) / 1000));
  return {seconds, days: Math.floor(seconds / 86400), hours: Math.floor(seconds % 86400 / 3600), minutes: Math.floor(seconds % 3600 / 60)};
}
function goldExpiryLabel(until) {
  const parts = new Intl.DateTimeFormat('en', {timeZone:'Asia/Tashkent', day:'numeric', month:'numeric', hour:'2-digit', minute:'2-digit', hourCycle:'h23'}).formatToParts(new Date(until));
  const get = type => parts.find(p => p.type === type).value;
  const months = ['yanvar','fevral','mart','aprel','may','iyun','iyul','avgust','sentyabr','oktyabr','noyabr','dekabr'];
  return `Gold ${get('day')}-${months[Number(get('month'))-1]}gacha faol`;
}
if (typeof module !== 'undefined') module.exports = {goldRemaining, goldExpiryLabel};
if (typeof document !== 'undefined') (() => {
  const entry = document.getElementById('verificationEntry');
  if (!entry) return;
  const card = document.createElement('div');
  card.id='goldStatus';card.className='card';card.hidden=true;
  card.innerHTML='<strong id="goldExpiry"></strong><p id="goldCountdown"></p>';
  entry.after(card);
  const style=document.createElement('style');
  style.textContent='#goldStatus{background:#151b2b;border:1px solid #5b1f2a;text-align:center;padding:20px}#goldStatus strong{display:block;font-size:18px;color:#f3f5ff}#goldStatus p{font-size:13px;color:#a4adc5;margin:7px 0 0}';
  document.head.append(style);
  let owner=null, deadline=null, serverTime=0, sampledAt=0, lastSync=-Infinity, pending=false;
  const visible=()=>!document.hidden&&!document.getElementById('profile').hidden&&me?.registered;
  function paint(){
    if(owner!==me?.id){card.hidden=true;return}
    if(!deadline){card.hidden=true;return}
    const now=serverTime+(performance.now()-sampledAt);
    const left=goldRemaining(deadline,now);
    card.hidden=false;
    document.getElementById('goldExpiry').textContent=left.seconds?goldExpiryLabel(deadline):'Gold muddati tugadi';
    document.getElementById('goldCountdown').textContent=left.seconds?(left.seconds<60?`${left.seconds} soniya qoldi`:`${left.days} kun ${left.hours} soat ${left.minutes} daqiqa qoldi`):'Gold hozir faol emas';
    card.title='Tugash vaqti: '+new Intl.DateTimeFormat('uz-UZ',{timeZone:'Asia/Tashkent',dateStyle:'long',timeStyle:'short'}).format(new Date(deadline))+' (Toshkent)';
    if(!left.seconds&&me.gold){me.gold=0;renderProfile()}
  }
  async function sync(){
    if(!visible()||pending)return;
    if(owner!==me.id){owner=me.id;deadline=null;lastSync=-Infinity;card.hidden=true}
    if(performance.now()-lastSync<15000)return;
    const id=me.id, started=performance.now();pending=true;lastSync=started;
    try{
      const data=await api('me/gold');
      if(me?.id!==id)return;
      sampledAt=performance.now();serverTime=Date.parse(data.server_now)+(sampledAt-started)/2;
      deadline=data.gold_until?Date.parse(data.gold_until):null;
      const days=deadline?Math.ceil(Math.max(0,deadline-serverTime)/86400000):0;
      if(me.gold!==days){me.gold=days;if(visible())renderProfile()}
      paint();
    }catch{/* Retain the last known countdown; retry on the next refresh. */}
    finally{pending=false}
  }
  const baseRender=renderProfile;
  renderProfile=function(){baseRender();paint();queueMicrotask(sync)};
  setInterval(()=>{if(visible()){paint();sync()}},1000);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden){lastSync=-Infinity;sync()}});
})();
