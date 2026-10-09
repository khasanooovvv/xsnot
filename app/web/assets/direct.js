(() => {
  const layoutFix=document.createElement('style');layoutFix.textContent='#dmListTools{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:2px;padding:3px;border:1px solid var(--border);border-radius:14px;background:var(--surface-2)}#dmListTools button{width:100%;margin:0;padding:9px 4px;border:0;border-radius:10px;background:transparent!important;color:var(--muted)!important;font-size:12px}#dmListTools button.selected{background:var(--surface)!important;color:var(--text)!important}#dmLikesList{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;padding:8px 0}.dm-like-card{min-width:0;overflow:hidden;border:1px solid var(--border);border-radius:16px;background:var(--surface-2);box-shadow:inset 0 1px #ffffff12}.dm-like-photo{display:block;width:100%!important;height:180px!important;min-width:0!important;max-width:none!important;object-fit:cover!important}.dm-like-info{padding:8px 10px 5px}.dm-like-info strong,.dm-like-info small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.dm-like-actions{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:6px}.dm-like-actions button{margin:0!important;padding:9px 4px!important;border-radius:10px!important}.dm-like-nope{background:var(--surface)!important;color:var(--muted)!important}.dm-like-heart{background:#e84d73!important;color:#fff!important}.dm-row .dm-avatar{display:block;width:48px!important;height:48px!important;min-width:48px!important;max-width:48px!important;max-height:48px!important;flex:0 0 48px!important;object-fit:cover!important;border-radius:50%!important}.chat-image{display:block;max-width:100%!important;width:auto!important;height:auto!important;min-width:0!important;max-height:min(320px,70vh)!important;object-fit:contain!important;object-position:center}';document.head.append(layoutFix);const tabStyle=document.createElement('style');tabStyle.textContent='#dmListTools{gap:4px;padding:3px;border-radius:24px;box-shadow:none}#dmListTools button{padding:0 3px;height:26px;border-radius:20px;font-size:11px;font-weight:600;transition:background .18s,color .18s}#dmListTools button.selected{background:#252525!important;color:#69bbee!important;box-shadow:none!important}';document.head.append(tabStyle);const priorityTabStyle=document.createElement('style');priorityTabStyle.textContent='html body #dmListTools{width:min(100%,180px)!important;height:34px!important;margin:0 auto 5px!important;padding:3px!important;border:1px solid #333!important;border-radius:24px!important;background:#050505!important;box-shadow:none!important}html body #dmListTools button{height:26px!important;padding:0 3px!important;border:0!important;border-radius:20px!important;background:transparent!important;color:#999!important;box-shadow:none!important;transform:none!important}html body #dmListTools button.selected{background:#252525!important;color:#69bbee!important}';document.head.append(priorityTabStyle);
  const tabIndicatorStyle=document.createElement('style');tabIndicatorStyle.textContent='html body #dmListTools{display:flex!important;position:relative;isolation:isolate;transform:translateY(-10px)}html body #dmListTools::before{content:"";position:absolute;z-index:-1;top:3px;bottom:3px;left:3px;width:calc((100% - 6px)/2);border-radius:20px;background:#252525;transform:translateX(0);transition:transform .25s ease}html body #dmListTools:has(.dm-likes-toggle.selected)::before{transform:translateX(100%)}html body #dmListTools button{display:flex!important;flex:1 1 0!important;justify-content:center!important;align-items:center!important;width:auto!important;min-width:0!important;text-align:center!important;line-height:16px!important}html body #dmListTools button.selected{background:transparent!important;color:#69bbee!important}';document.head.append(tabIndicatorStyle);
  const el=id=>document.getElementById(id);
  const root=document.createElement('section');root.id='dmWindow';root.hidden=true;
  root.innerHTML=`<div id="dmTop"><button id="dmBack" aria-label="Orqaga">${typeof userBackIconMarkup==='function'?userBackIconMarkup():'←'}</button><div id="dmPartner"></div><button id="dmMenu" aria-label="Chat menyusi">⋮</button></div><div id="dmNotice" role="status" hidden></div><div id="dmMessages" aria-live="polite"></div><div id="dmEditBar" hidden>Tahrirlash <button id="dmCancelEdit" type="button">Bekor qilish</button></div><form id="dmForm"><input id="dmInput" maxlength="2000" placeholder="Xabar yozing…" autocomplete="off" aria-label="Xabar" required><button aria-label="Yuborish"><svg viewBox="0 0 24 24"><path d="M21 3 10.4 13.6M21 3l-6.8 18-3.8 7.4L3 9.8 21 3Z"/></svg></button></form>`;
  document.body.append(root);
  const dialog=document.createElement('dialog');dialog.id='dmActions';document.body.append(dialog);
  const list=document.createElement('div');list.id='dmList';
  const userButton=document.createElement('button');userButton.type='button';userButton.textContent='User';userButton.className='dm-user-toggle selected';
  const likesButton=document.createElement('button');likesButton.type='button';likesButton.textContent='Layklar';likesButton.className='dm-likes-toggle';
  const likesList=document.createElement('div');likesList.id='dmLikesList';likesList.hidden=true;
  const navChat=document.querySelector('[data-page="instagram"]'),navBadge=document.createElement('span');navBadge.className='nav-unread-badge';navBadge.hidden=true;navChat?.append(navBadge);
  const tools=document.createElement('div');tools.id='dmListTools';tools.append(userButton,likesButton);el('instagram').prepend(tools);el('instagram').append(likesList,list);
  let current=null,epoch=0,revision=0,before=null,more=false,editing=null,busy=false,refreshBusy=false,listSignature='';
  const messages=new Map(), people=new Map(), readMarkers=new Map();
  let cachedList=null,cacheOwner=null,listPending=false,avatarSync=0,lastListSync=0;
  function mergePerson(p){const merged={...people.get(p.id),...p};people.set(p.id,merged);return merged}
  async function restoreList(){
    if(!me?.registered||cacheOwner===me.id)return;
    cacheOwner=me.id;const owner=cacheOwner;
    const cached=await avatarCacheStore('get','dm-list:'+owner);
    if(me?.id!==owner||cachedList)return;
    if(cached){cachedList=cached;cached.chats.forEach(c=>mergePerson(c.partner));renderList(cached)}
  }
  const time=v=>v?new Date(v).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}):'';
  const error=e=>{el('dmNotice').textContent=e.message||String(e);el('dmNotice').hidden=false};
  async function loadDatingLikes(){
    const r=await fetch('/api/dating/likes',{cache:'no-store',headers:{'X-Telegram-Init-Data':tg?.initData||''}});
    const data=await r.json();if(!r.ok)throw Error(data.detail||'Layklarni yuklab bo‘lmadi.');
    likesList.replaceChildren();
    if(!data.length){likesList.textContent='Hozircha sizga hech kim like bosmagan.';return 0;}
    for(const p of data){const b=document.createElement('article');b.className='dm-like-card';b.innerHTML='<img class="dm-like-photo" alt="Anketa rasmi" src="'+esc(p.photos?.[0]||'')+'"><div class="dm-like-info"><strong>'+esc(p.name)+badgeMarkup(p)+'</strong><small>'+esc(p.age||'')+' yosh · Sizga like bosdi</small></div><div class="dm-like-actions"><button type="button" class="dm-like-nope" aria-label="O‘tkazib yuborish">×</button><button type="button" class="dm-like-heart" aria-label="Like bilan javob berish">♥</button></div>';const openChat=async()=>{try{const d=await request('/chats/with/'+p.id,'POST');await open(d.chat_id)}catch(e){error(e)}};b.querySelector('.dm-like-heart').onclick=openChat;b.querySelector('.dm-like-nope').onclick=()=>b.remove();likesList.append(b)}
    return data.length;
  }
  async function updateNavBadge(likeCount=0,unreadCount=0){const total=Number(likeCount)+Number(unreadCount);navBadge.textContent=total>99?'99+':String(total);navBadge.hidden=total<1}
  function setDirectTab(tab){const likes=tab==='likes';likesList.hidden=!likes;list.hidden=likes;el('userSearchForm').hidden=likes;el('userSearchResults').hidden=likes;el('instagram').classList.toggle('likes-mode',likes);userButton.classList.toggle('selected',!likes);likesButton.classList.toggle('selected',likes)}
  function tabHaptic(){try{const app=window.Telegram?.WebApp;if(typeof app?.HapticFeedback?.selectionChanged==='function'&&(!app.isVersionAtLeast||app.isVersionAtLeast('6.1')))app.HapticFeedback.selectionChanged();}catch{}}
  userButton.onclick=()=>{tabHaptic();setDirectTab('user')};
  likesButton.onclick=()=>{tabHaptic();setDirectTab('likes');void loadDatingLikes().catch(error)};
  window.openDatingLikes=async()=>{show('instagram');setDirectTab('likes');await loadDatingLikes()};
  async function request(path,method='GET',body){const r=await fetch('/api/direct'+path,{method,cache:'no-store',headers:{'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''},...(body===undefined?{}:{body:JSON.stringify(body)})});const raw=await r.text();let d;try{d=JSON.parse(raw)}catch{throw Error(r.ok?'Serverdan kutilmagan javob olindi.':'Server xatosi ('+r.status+'). Birozdan keyin qayta urinib ko‘ring.')}if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'So‘rov bajarilmadi.');return d}
  function actions(items){dialog.replaceChildren();for(const [label,fn] of [...items,['Bekor qilish',()=>{}]]){const b=document.createElement('button');b.type='button';b.textContent=label;b.onclick=()=>{dialog.close();Promise.resolve().then(fn).catch(error)};dialog.append(b)}dialog.showModal()}
  function hold(node,fn){let timer,start,held=false;node.addEventListener('pointerdown',e=>{held=false;start=[e.clientX,e.clientY];timer=setTimeout(()=>{held=true;fn()},550)});for(const name of ['pointerup','pointercancel','pointerleave'])node.addEventListener(name,()=>clearTimeout(timer));node.addEventListener('pointermove',e=>{if(start&&Math.hypot(e.clientX-start[0],e.clientY-start[1])>10)clearTimeout(timer)});node.addEventListener('contextmenu',e=>{e.preventDefault();clearTimeout(timer);fn()});node.addEventListener('click',e=>{if(held){e.preventDefault();e.stopImmediatePropagation();held=false}},true)}
  function cancelEdit(){editing=null;el('dmEditBar').hidden=true;el('dmInput').value=''}
  function renderMessages(){const box=el('dmMessages'),bottom=box.scrollHeight-box.scrollTop-box.clientHeight<70,oldHeight=box.scrollHeight,oldTop=box.scrollTop;box.replaceChildren();if(more){const b=document.createElement('button');b.textContent='Oldingi xabarlar';b.onclick=()=>older().catch(error);box.append(b)}for(const m of [...messages.values()].sort((a,b)=>a.id-b.id)){if(m.is_deleted)continue;const n=document.createElement('div');n.className='dm-bubble'+(m.mine?' mine':'');n.dataset.id=m.id;n.innerHTML='<div class="dm-text">'+esc(m.text)+'</div><small class="dm-meta">'+(m.is_edited?'tahrirlangan · ':'')+esc(time(m.created_at))+'</small>';if(m.mine){n.tabIndex=0;const menu=()=>messageMenu(m);hold(n,menu);n.onkeydown=e=>{if(e.key==='Enter')menu()}}box.append(n)}box.scrollTop=bottom?box.scrollHeight:oldTop+Math.max(0,box.scrollHeight-oldHeight)}
  function messageMenu(m){const id=current?.id;if(!id)return;const name=current?.partner?.name||'suhbatdosh';actions([['Tahrirlash',()=>{editing=m.id;el('dmInput').value=m.text;el('dmEditBar').hidden=false;el('dmInput').focus()}],['O‘chirish',async()=>{const scope=await confirmChoice('Xabarni o‘chirish',`Mendan va ${name}dan o‘chirish`,`Faqat mendan o‘chirish`);if(!scope)return;const deleted=await request(`/chats/${id}/messages/${m.id}?scope=${scope}`,'DELETE');if(current?.id===id){if(scope==='self')messages.delete(m.id);else messages.set(m.id,deleted);if(editing===m.id)cancelEdit();renderMessages();await poll()}}]])}
  function partner(data){data.partner=mergePerson(data.partner);current.partner=data.partner;current.blocked=data.blocked_by_me;current.canSend=data.can_send;const signature=JSON.stringify(data.partner);if(el('dmPartner').dataset.signature!==signature){el('dmPartner').dataset.signature=signature;el('dmPartner').innerHTML=avatar(data.partner)+'<div class="dm-person"><strong>'+esc(data.partner.name)+badgeMarkup(data.partner)+'</strong><small><i class="'+(data.partner.online?'online':'')+'"></i>'+(data.partner.online?'Online':'Offline')+'</small></div>';}el('dmInput').disabled=!data.can_send;el('dmForm').querySelector('button').disabled=!data.can_send||busy;if(!data.can_send){
 const box=el('dmNotice');box.replaceChildren();box.hidden=false;box.classList.remove('dm-limit-card');
 const reason=data.send_limit?.reason;
 box.textContent=reason==='weekly_dm_limit'?'Har 7 kunda '+(data.send_limit.partner_limit||3)+' ta suhbatdosh limitiga yetdingiz.':reason==='gold_required'?'':'Bloklash sababli xabar yuborish o‘chirilgan.';
 if(reason){
   box.classList.add('dm-limit-card');box.replaceChildren();
   if(reason==='gold_required'){const title=document.createElement('strong');title.className='dm-limit-title';title.textContent='DM';box.append(title)}
   if(reason==='weekly_dm_limit'){
     const title=document.createElement('strong');title.className='dm-limit-title';title.textContent='DM limitingiz tugadi';
     const description=document.createElement('p');description.className='dm-limit-description';description.textContent='Bu hafta '+(data.send_limit.partner_limit||3)+' ta suhbatdosh limiti ishlatildi. Avvalgi suhbatlaringizni davom ettirishingiz mumkin.';
     box.append(title,description);
   }
   const hint=document.createElement('p');hint.className='dm-limit-hint';hint.textContent=reason==='gold_required'?'Limitingizni oshiring yoki verifikatsiyadan o‘ting':'Limitingizni oshiring';box.append(hint);
   if(data.send_limit.resets_at){const reset=document.createElement('div');reset.className='dm-limit-reset';const label=document.createElement('span');label.textContent='Limit yangilanadi';const date=document.createElement('strong');const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Tashkent',day:'numeric',month:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(data.send_limit.resets_at));const part=type=>parts.find(p=>p.type===type)?.value;const months=['yanvar','fevral','mart','aprel','may','iyun','iyul','avgust','sentabr','oktabr','noyabr','dekabr'];date.textContent=part('day')+'-'+months[Number(part('month'))-1]+', '+part('hour')+':'+part('minute');reset.append(label,date);box.append(reset)}
   const upgrade=document.createElement('button');upgrade.type='button';
   upgrade.className='dm-limit-upgrade';upgrade.textContent='Limitni oshirish';
   upgrade.onclick=()=>showPremiumSheet(reason==='weekly_dm_limit'&&(data.send_limit.partner_limit||3)>1?'plus':'gold');
   const buttons=document.createElement('div');buttons.className='dm-limit-actions';buttons.append(upgrade);box.append(buttons);
   if(reason==='gold_required'){const verify=document.createElement('button');verify.type='button';verify.className='dm-limit-verify';verify.textContent='Verifikatsiyadan o‘tish';verify.onclick=()=>document.getElementById('verificationEntry')?.click();buttons.append(verify)}
 }
 }else el('dmNotice').hidden=true}
  async function read(){if(!current||document.hidden)return;const id=current.id,last=Math.max(0,...messages.keys());if(last>(readMarkers.get(id)||0)){await request(`/chats/${id}/read`,'POST',{message_id:last});readMarkers.set(id,last)}}
  async function open(id){const ticket=++epoch;current={id};el('dmPartner').replaceChildren();delete el('dmPartner').dataset.signature;messages.clear();revision=0;before=null;more=false;cancelEdit();root.hidden=false;document.body.classList.add('dm-open');el('dmMessages').replaceChildren();try{const d=await request(`/chats/${id}/messages?include_avatar=${!people.has((cachedList?.chats.find(c=>c.id===id)?.partner.id))}`);if(ticket!==epoch)return;d.messages.forEach(m=>messages.set(m.id,m));revision=d.revision;before=d.before_id;more=d.more;partner(d);renderMessages();el('dmMessages').scrollTop=el('dmMessages').scrollHeight;await read()}catch(e){if(ticket===epoch)error(e)}}
  async function poll(){if(!current?.partner||document.hidden)return;const ticket=epoch,id=current.id;let d;do{d=await request(`/chats/${id}/messages?since_revision=${revision}&include_avatar=false`);if(ticket!==epoch)return;d.messages.forEach(m=>{if(!messages.has(m.id)||messages.get(m.id).revision<=m.revision)messages.set(m.id,m)});revision=Math.max(revision,d.revision);partner(d);if(d.messages.length)renderMessages()}while(d.more);await read()}
  async function older(){const ticket=epoch,id=current.id;const d=await request(`/chats/${id}/messages?before_id=${before}`);if(ticket!==epoch)return;d.messages.forEach(m=>messages.set(m.id,m));before=d.before_id;more=d.more;renderMessages()}
  el('dmBack').onclick=()=>{epoch++;current=null;messages.clear();revision=0;before=null;root.hidden=true;document.body.classList.remove('dm-open');cancelEdit();refreshList().catch(notice)};
  el('dmCancelEdit').onclick=cancelEdit;
  el('dmForm').onsubmit=async e=>{e.preventDefault();if(busy||!current?.canSend)return;const value=el('dmInput').value.trim();if(!value)return;busy=true;const ticket=epoch,id=current.id,editId=editing;try{await request(`/chats/${id}/messages`+(editId?`/${editId}`:''),editId?'PATCH':'POST',{text:value});if(ticket===epoch){cancelEdit();await poll();el('dmMessages').scrollTop=el('dmMessages').scrollHeight}}catch(e){if(ticket===epoch){error(e);await poll()}}finally{busy=false;if(current)el('dmForm').querySelector('button').disabled=!current.canSend}};
  el('dmMenu').onclick=()=>{if(!current?.partner)return;const id=current.id,p=current.partner,blocked=current.blocked;actions([[blocked?'Blokdan chiqarish':'Bloklash',async()=>{if(!confirm(p.name+(blocked?' blokdan chiqarilsinmi?':' bloklansinmi?')))return;await request('/blocks/'+p.id,blocked?'DELETE':'POST');await poll()}],['Chatni ro‘yxatdan o‘chirish',()=>hide(id)]])};
  function confirmChoice(title,both,self){return new Promise(resolve=>{dialog.replaceChildren();dialog.className='dm-confirm';const h=document.createElement('h3');h.textContent=title;const row=document.createElement('div');row.className='dm-confirm-actions';const all=document.createElement('button');all.type='button';all.textContent=both;const own=document.createElement('button');own.type='button';own.textContent=self;const cancel=document.createElement('button');cancel.type='button';cancel.textContent='Bekor qilish';const finish=value=>{dialog.close();dialog.className='';resolve(value)};all.onclick=()=>finish('both');own.onclick=()=>finish('self');cancel.onclick=()=>finish(null);row.append(all,own,cancel);dialog.append(h,row);dialog.showModal()})}
  async function hide(id){const name=current?.partner?.name||people.get(current?.partner?.id)?.name||'suhbatdosh';const scope=await confirmChoice('Chatni o‘chirish',`Mendan va ${name}dan o‘chirish`,'Faqat mendan o‘chirish');if(!scope)return;await request(`/chats/${id}?scope=${scope}`,'DELETE');if(current?.id===id)el('dmBack').click();await refreshList()}
  function renderList(d){
    const signature=JSON.stringify(d);if(signature===listSignature)return;listSignature=signature;
    const existing=new Map([...list.querySelectorAll('.dm-row')].map(n=>[Number(n.dataset.chatId),n]));
    list.querySelector('.dm-more')?.remove();
    for(const c of d.chats){
      let b=existing.get(c.id);existing.delete(c.id);
      if(!b){b=document.createElement('button');b.type='button';b.className='dm-row';b.dataset.chatId=c.id;hold(b,()=>actions([['O‘chirish',()=>hide(c.id)]]));b.onclick=()=>open(c.id)}
      const rowSignature=JSON.stringify({...c,partner:{...c.partner,online:undefined}});
      if(b.dataset.signature!==rowSignature){
        b.dataset.signature=rowSignature;
        b.innerHTML=avatar(c.partner)+'<div class="dm-row-copy"><strong>'+esc(c.partner.name)+badgeMarkup(c.partner)+'</strong><small>'+esc(c.last_message?(c.last_message.is_deleted?'Xabar o‘chirildi':c.last_message.text.slice(0,90)):'Hali xabar yo‘q')+'</small></div><div class="dm-row-meta">'+esc(time(c.last_message_at))+(c.unread?'<span class="dm-unread">'+c.unread+'</span>':'')+'</div>';
      }
      list.append(b);
    }
    existing.forEach(n=>n.remove());
    if(d.more){const b=document.createElement('button');b.className='dm-more';b.textContent='Ko‘proq chatlar';b.onclick=()=>loadMore(d.chats.length,b);list.append(b)}
  }
  async function refreshList(){
    if(document.hidden||el('instagram').hidden||!me?.registered||listPending)return;
    listPending=true;
    try{
      const full=Date.now()-avatarSync>60000;
      const d=await request('/chats?include_avatar='+full);
      d.chats.forEach(c=>{c.partner=mergePerson(c.partner)});
      const unread=d.chats.reduce((sum,c)=>sum+Number(c.unread||0),0);void loadDatingLikes().then(count=>updateNavBadge(count,unread)).catch(()=>updateNavBadge(0,unread));
      if(full)avatarSync=Date.now();
      lastListSync=Date.now();cachedList=d;
      const changed=JSON.stringify(d)!==listSignature;renderList(d);
      if(changed)void avatarCacheStore('put','dm-list:'+me.id,d);
    }finally{listPending=false}
  }
  document.querySelector('[data-page="instagram"]')?.addEventListener('click',()=>{void restoreList();void refreshList().catch(e=>notice(e.message))});
  async function loadMore(offset,b){try{const d=await request('/chats?offset='+offset);for(const c of d.chats){const n=document.createElement('button');n.className='dm-row';n.dataset.chatId=c.id;c.partner=mergePerson(c.partner);n.innerHTML=avatar(c.partner)+'<div class="dm-row-copy"><strong>'+esc(c.partner.name)+badgeMarkup(c.partner)+'</strong><small>'+esc(c.last_message?.text||'')+'</small></div><div class="dm-row-meta">'+esc(time(c.last_message_at))+(c.unread?'<span class="dm-unread">'+c.unread+'</span>':'')+'</div>';hold(n,()=>actions([['O‘chirish',()=>hide(c.id)]]));n.onclick=()=>open(c.id);b.before(n)}if(d.more)b.onclick=()=>loadMore(offset+d.chats.length,b);else b.remove()}catch(e){notice(e.message)}}
  const originalRender=renderUserSearchResults;renderUserSearchResults=rows=>{originalRender(rows);list.hidden=true;el('userSearchResults').hidden=false;el('userSearchResults').querySelectorAll('.direct-result').forEach((n,i)=>{n.classList.add('dm-search-hit');n.tabIndex=0;n.setAttribute('role','button');const action=async()=>{try{const d=await request('/chats/with/'+rows[i].id,'POST');await open(d.chat_id)}catch(e){notice(e.message)}};n.onclick=action;n.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();action()}}})};
  el('userSearchInput').addEventListener('input',()=>{if(!likesList.hidden)return;const searching=el('userSearchInput').value.trim().length>0;list.hidden=searching;if(!searching)el('userSearchResults').hidden=false});
  window.openDatingDirect=async id=>{show('instagram');await open(id);};
  const requestedChat=new URLSearchParams(location.search).get('dm_chat');
  let launchHandled=false;
  async function openRequestedChat(){
    if(launchHandled||!me?.registered)return;
    launchHandled=true;
    if(!requestedChat||!/^\d+$/.test(requestedChat)||!Number.isSafeInteger(Number(requestedChat)))return;
    document.querySelector('[data-page="instagram"]')?.click();
    await open(Number(requestedChat));
  }
  let heartbeat=0;async function tick(){if(!refreshBusy&&me?.registered&&!document.hidden){refreshBusy=true;try{await openRequestedChat();if(Date.now()-heartbeat>10000){heartbeat=Date.now();void request('/presence','POST',{online:true}).catch(()=>{})}void restoreList();if(current)await poll();else if(Date.now()-lastListSync>5000)await refreshList()}catch(e){if(current)error(e);else notice(e.message)}finally{refreshBusy=false}}setTimeout(tick,1000)}tick();
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&me?.registered)request('/presence','POST',{online:false}).catch(()=>{});else heartbeat=0});
  function viewport(){if(window.visualViewport){root.style.height=window.visualViewport.height+'px';root.style.top=window.visualViewport.offsetTop+'px'}}window.visualViewport?.addEventListener('resize',viewport);window.visualViewport?.addEventListener('scroll',viewport);viewport();
})();
