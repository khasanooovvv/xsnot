(() => {
  const panel=document.createElement('div');
  panel.id='roulette';panel.hidden=true;
  panel.innerHTML='<div class="roulette-window"><div class="roulette-track"></div><div class="roulette-marker"></div></div><p class="roulette-status" role="status"></p>';
  $('messages').before(panel);
  const track=panel.querySelector('.roulette-track'),viewport=panel.querySelector('.roulette-window'),status=panel.querySelector('.roulette-status');
  const style=document.createElement('style');
  style.textContent='#roulette{padding:24px 0;text-align:center}body.chat-searching #messages{display:none}.roulette-window{position:relative;overflow:hidden;height:202px;border:1px solid #ffffff30;border-radius:24px;background:rgba(42,56,70,.20);box-shadow:inset 0 1px #ffffff38,0 10px 26px #0005;backdrop-filter:blur(14px) saturate(135%);-webkit-backdrop-filter:blur(14px) saturate(135%)}.roulette-marker{position:absolute;left:50%;top:14px;bottom:14px;width:124px;transform:translateX(-50%);border:2px solid #8ea3b5;border-radius:20px;box-shadow:0 0 24px #71889755;pointer-events:none}.roulette-track{display:flex;align-items:center;height:100%;width:max-content;will-change:transform}.roulette-card{flex:0 0 132px;width:132px;padding:16px 8px;box-sizing:border-box;color:#c5d0d9}.roulette-card .avatar{width:88px;height:88px;border-radius:50%;margin:auto}.roulette-card strong{display:block;margin:12px auto 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:14px}.roulette-status{color:#aebbc5}body.chat-fullscreen #roulette{display:none}';
  document.head.append(style);
  let started=0,animation=null,timer=null,landing=null,signature='',wake=null;
  function reset(){
    wake?.();wake=null;
    started=0;clearTimeout(timer);animation?.cancel();animation=null;
    panel.hidden=true;track.replaceChildren();landing=null;signature='';
  }
  function start(){
    if(started)return;
    document.body.classList.add('chat-searching');
    started=performance.now()||1;panel.hidden=false;
    status.textContent='Ruletka aylanmoqda…';
    for(let i=0;i<28;i++){
      const node=document.createElement('div');node.className='roulette-card';
      node.innerHTML=avatar({name:'?',anonymous:true})+'<strong>Suhbatdosh</strong>';
      track.append(node);if(i===24)landing=node;
    }
    const from=viewport.clientWidth/2-66,to=from-24*132;
    track.style.transform='translateX('+to+'px)';
    animation=track.animate([
      {transform:'translateX('+from+'px)',offset:0,easing:'linear'},
      {transform:'translateX('+(from-20*132)+'px)',offset:2/3,easing:'cubic-bezier(.16,1,.3,1)'},
      {transform:'translateX('+to+'px)',offset:1}
    ],{duration:matchMedia('(prefers-reduced-motion: reduce)').matches?0:3000,fill:'forwards'});
    timer=setTimeout(()=>{status.textContent='Suhbatdosh kutilmoqda…'},3000);
  }
  window.chatRoulette={reset,start,hold(person){
    if(!started)return false;
    const next=JSON.stringify(person);
    if(signature!==next&&landing){signature=next;landing.innerHTML=avatar(person)+'<strong>'+esc(person.anonymous?'Anonim':person.name)+'</strong>'}
    return performance.now()-started<3000;
  },async ready(person){
    if(!this.hold(person))return;
    const remaining=Math.max(0,3000-(performance.now()-started));
    await new Promise(resolve=>{
      const timeout=setTimeout(()=>{wake=null;resolve()},remaining);
      wake=()=>{clearTimeout(timeout);resolve()};
    });
  }};
})();
