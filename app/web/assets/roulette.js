(() => {
  window.showRouletteLimit=function(limit){
    document.getElementById('rouletteLimitDialog')?.remove();
    const dialog=document.createElement('dialog');dialog.id='rouletteLimitDialog';
    dialog.setAttribute('aria-labelledby','rouletteLimitTitle');
    dialog.innerHTML='<button class="limit-close" type="button" aria-label="Yopish">×</button><h2 id="rouletteLimitTitle">Ruletka limitingiz tugadi</h2><p>Bugungi '+Number(limit)+' ta aylantirish imkoniyati ishlatildi.</p><p>'+(limit===10?'Limitingizni oshiring yoki verifikatsiyadan o‘ting.':limit>=100?'Limit yangilangach yana suhbatlashishingiz mumkin.':'Ko‘proq suhbat uchun limitingizni oshiring.')+'</p><div class="limit-reset"><span>Limit yangilanadi</span><strong>Ertaga, 00:00</strong></div><div class="limit-actions"></div>';
    const actions=dialog.querySelector('.limit-actions');
    function action(label,callback){const button=document.createElement('button');button.type='button';button.textContent=label;button.onclick=()=>{dialog.close();callback()};actions.append(button)}
    if(limit<100)action('Limitni oshirish',()=>showPremiumSheet(limit>=20?'plus':'gold'));
    if(limit===10)action('Verifikatsiyadan o‘tish',()=>document.getElementById('verificationEntry')?.click());
    dialog.querySelector('.limit-close').onclick=()=>dialog.close();
    dialog.addEventListener('close',()=>dialog.remove());document.body.append(dialog);dialog.showModal();
  };
  const limitStyle=document.createElement('style');
  limitStyle.textContent=`#rouletteLimitDialog{box-sizing:border-box;width:calc(100% - 28px);max-width:480px;max-height:90dvh;overflow:auto;padding:22px;border:1px solid #393939;border-radius:22px;background:#1a1a1a;color:#f4f4f4;background-image:none;box-shadow:0 16px 48px #0005;animation:rouletteLimitIn .18s ease-out}#rouletteLimitDialog::backdrop{background:rgba(0,0,0,.72);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px)}#rouletteLimitDialog h2{font-size:20px;margin:12px 0 14px}#rouletteLimitDialog p{font-size:14px;line-height:1.6;color:#bdbdbd}#rouletteLimitDialog .limit-reset{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;padding:16px 0;margin:18px 0;border-top:1px solid #393939;border-bottom:1px solid #393939;font-size:13px;color:#999}#rouletteLimitDialog .limit-reset strong{color:#eee}#rouletteLimitDialog .limit-actions{display:flex;gap:10px}#rouletteLimitDialog button{min-width:0;min-height:46px;background:#3b3b3b!important;color:#fff;border:1px solid #494949;border-radius:14px;background-image:none!important;box-shadow:none!important;filter:none!important;transform:none!important;transition:background-color .18s ease,transform .12s ease}#rouletteLimitDialog .limit-actions button{flex:1;white-space:normal}#rouletteLimitDialog button::before,#rouletteLimitDialog button::after{display:none!important}#rouletteLimitDialog button:hover{background:#484848!important}#rouletteLimitDialog button:active{background:#303030!important;transform:scale(.98)!important}#rouletteLimitDialog button:focus-visible{outline:2px solid #aaa;outline-offset:3px}#rouletteLimitDialog .limit-close{display:block;margin-left:auto;width:32px;min-height:32px;padding:0;background:#262626!important;border:0;font-size:24px}@keyframes rouletteLimitIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}@media(max-width:360px){#rouletteLimitDialog{padding:16px}#rouletteLimitDialog .limit-actions{flex-direction:column}}@media(prefers-reduced-motion:reduce){#rouletteLimitDialog{animation:none}#rouletteLimitDialog button{transition:none}}`;
  document.head.append(limitStyle);
  const panel=document.createElement('div');
  panel.id='roulette';panel.hidden=true;
  panel.innerHTML='<div class="roulette-window"><div class="roulette-track"></div><div class="roulette-marker"></div></div><p class="roulette-status" role="status"></p>';
  $('messages').before(panel);
  const track=panel.querySelector('.roulette-track'),viewport=panel.querySelector('.roulette-window'),status=panel.querySelector('.roulette-status');
  const style=document.createElement('style');
  style.textContent='#roulette{padding:24px 0;text-align:center}body.chat-searching #messages{display:none}.roulette-window{position:relative;overflow:hidden;height:202px;border:1px solid #ffffff30;border-radius:24px;background:rgba(42,56,70,.20);box-shadow:inset 0 1px #ffffff38,0 10px 26px #0005;backdrop-filter:blur(14px) saturate(135%);-webkit-backdrop-filter:blur(14px) saturate(135%)}.roulette-marker{position:absolute;left:50%;top:14px;bottom:14px;width:124px;transform:translateX(-50%);border:2px solid #8ea3b5;border-radius:20px;box-shadow:0 0 24px #71889755;pointer-events:none}.roulette-track{display:flex;align-items:center;height:100%;width:max-content;will-change:transform}.roulette-card{flex:0 0 132px;width:132px;padding:16px 8px;box-sizing:border-box;color:#c5d0d9}.roulette-card .avatar{width:88px;height:88px;border-radius:50%;margin:auto}.roulette-card strong{display:block;margin:12px auto 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:14px}.roulette-status{color:#aebbc5}body.chat-fullscreen #roulette{display:none}';
  document.head.append(style);
  let started=0,animation=null,timer=null,landing=null,signature='',wake=null,readyUntil=0;
  function reset(){
    wake?.();wake=null;
    started=0;clearTimeout(timer);animation?.cancel();animation=null;
    panel.hidden=true;track.replaceChildren();landing=null;signature='';readyUntil=0;
  }
  function setPeople(people){
    if(!started||!Array.isArray(people)||!people.length)return;
    [...track.children].forEach((node,i)=>{
      if(node===landing)return; // Only the confirmed match may occupy the final card.
      const person=people[i%people.length];
      node.innerHTML=avatar(person)+'<strong>'+esc(person.name||'Suhbatdosh')+badgeMarkup(person)+'</strong>';
    });
  }
  function start(){
    if(started)return;
    document.body.classList.add('chat-searching');
    started=performance.now()||1;panel.hidden=false;
    status.textContent='Ruletka aylanmoqda…';
    const people=Array.isArray(window.roulettePeople)?window.roulettePeople:[];
    for(let i=0;i<28;i++){
      const node=document.createElement('div');node.className='roulette-card';
      const person=i===24?{name:'Qidirilmoqda…',anonymous:true}:
        people.length?people[i%people.length]:{name:'?',anonymous:true};
      node.innerHTML=avatar(person)+'<strong>'+esc(person.name||'Suhbatdosh')+badgeMarkup(person)+'</strong>';
      track.append(node);if(i===24)landing=node;
    }
    const from=viewport.clientWidth/2-66,to=from-24*132;
    track.style.transform='translateX('+to+'px)';
    animation=track.animate([
      {transform:'translateX('+from+'px)',offset:0,easing:'linear'},
      {transform:'translateX('+(from-20*132)+'px)',offset:2/3,easing:'cubic-bezier(.16,1,.3,1)'},
      {transform:'translateX('+to+'px)',offset:1}
    ],{duration:matchMedia('(prefers-reduced-motion: reduce)').matches?0:3000,fill:'forwards'});
    timer=setTimeout(()=>{status.textContent=signature?'Suhbatdosh topildi':'Suhbatdosh kutilmoqda…'},3000);
  }
  window.chatRoulette={reset,start,setPeople,hold(person){
    if(!started)return false;
    const next=JSON.stringify(person);
    if(signature!==next&&landing){
      signature=next;landing.innerHTML=avatar(person)+'<strong>'+esc(person.anonymous?'Anonim':person.name)+badgeMarkup(person)+'</strong>';
      // A late match still gets a visible landing, never a random preview user.
      readyUntil=Math.max(started+3000,performance.now()+600);
      status.textContent='Suhbatdosh topildi';
    }
    return performance.now()<readyUntil;
  },async ready(person){
    if(!this.hold(person))return;
    const remaining=Math.max(0,readyUntil-performance.now());
    await new Promise(resolve=>{
      const timeout=setTimeout(()=>{wake=null;resolve()},remaining);
      wake=()=>{clearTimeout(timeout);resolve()};
    });
  }};
})();
