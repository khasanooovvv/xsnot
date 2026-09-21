(() => {
  const el=id=>document.getElementById(id);
  const root=document.createElement('section');root.id='dmWindow';root.hidden=true;
  root.innerHTML=`<div id="dmTop"><button id="dmBack" aria-label="Orqaga">${typeof userBackIconMarkup==='function'?userBackIconMarkup():'←'}</button><div id="dmPartner"></div><button id="dmMenu" aria-label="Chat menyusi">⋮</button></div><div id="dmNotice" role="status" hidden></div><div id="dmMessages" aria-live="polite"></div><div id="dmEditBar" hidden>Tahrirlash <button id="dmCancelEdit" type="button">Bekor qilish</button></div><form id="dmForm"><input id="dmInput" maxlength="2000" placeholder="Xabar yozing…" autocomplete="off" aria-label="Xabar" required><button aria-label="Yuborish"><svg viewBox="0 0 24 24"><path d="M21 3 10.4 13.6M21 3l-6.8 18-3.8 7.4L3 9.8 21 3Z"/></svg></button></form>`;
  document.body.append(root);
  const dialog=document.createElement('dialog');dialog.id='dmActions';document.body.append(dialog);
  const list=document.createElement('div');list.id='dmList';
  const tools=document.createElement('div');tools.id='dmListTools';tools.innerHTML='<button type="button">Bloklanganlar</button>';
  el('instagram').append(tools,list);
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
  async function request(path,method='GET',body){const r=await fetch('/api/direct'+path,{method,cache:'no-store',headers:{'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''},...(body===undefined?{}:{body:JSON.stringify(body)})});const raw=await r.text();let d;try{d=JSON.parse(raw)}catch{throw Error(r.ok?'Serverdan kutilmagan javob olindi.':'Server xatosi ('+r.status+'). Birozdan keyin qayta urinib ko‘ring.')}if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'So‘rov bajarilmadi.');return d}
  function actions(items){dialog.replaceChildren();for(const [label,fn] of [...items,['Bekor qilish',()=>{}]]){const b=document.createElement('button');b.type='button';b.textContent=label;b.onclick=()=>{dialog.close();Promise.resolve().then(fn).catch(error)};dialog.append(b)}dialog.showModal()}
  function hold(node,fn){let timer,start,held=false;node.addEventListener('pointerdown',e=>{held=false;start=[e.clientX,e.clientY];timer=setTimeout(()=>{held=true;fn()},550)});for(const name of ['pointerup','pointercancel','pointerleave'])node.addEventListener(name,()=>clearTimeout(timer));node.addEventListener('pointermove',e=>{if(start&&Math.hypot(e.clientX-start[0],e.clientY-start[1])>10)clearTimeout(timer)});node.addEventListener('contextmenu',e=>{e.preventDefault();clearTimeout(timer);fn()});node.addEventListener('click',e=>{if(held){e.preventDefault();e.stopImmediatePropagation();held=false}},true)}
  function cancelEdit(){editing=null;el('dmEditBar').hidden=true;el('dmInput').value=''}
  function renderMessages(){const box=el('dmMessages'),bottom=box.scrollHeight-box.scrollTop-box.clientHeight<70,oldHeight=box.scrollHeight,oldTop=box.scrollTop;box.replaceChildren();if(more){const b=document.createElement('button');b.textContent='Oldingi xabarlar';b.onclick=()=>older().catch(error);box.append(b)}for(const m of [...messages.values()].sort((a,b)=>a.id-b.id)){if(m.is_deleted)continue;const n=document.createElement('div');n.className='dm-bubble'+(m.mine?' mine':'');n.dataset.id=m.id;n.innerHTML='<div class="dm-text">'+esc(m.text)+'</div><small class="dm-meta">'+(m.is_edited?'tahrirlangan · ':'')+esc(time(m.created_at))+'</small>';if(m.mine){n.tabIndex=0;const menu=()=>messageMenu(m);hold(n,menu);n.onkeydown=e=>{if(e.key==='Enter')menu()}}box.append(n)}box.scrollTop=bottom?box.scrollHeight:oldTop+Math.max(0,box.scrollHeight-oldHeight)}
  function messageMenu(m){const id=current?.id;if(!id)return;actions([['Tahrirlash',()=>{editing=m.id;el('dmInput').value=m.text;el('dmEditBar').hidden=false;el('dmInput').focus()}],['O‘chirish',async()=>{if(!confirm('Xabar ikkala tomondan o‘chirilsinmi?'))return;await request(`/chats/${id}/messages/${m.id}`,'DELETE');if(current?.id===id){if(editing===m.id)cancelEdit();await poll()}}]])}
  function partner(data){data.partner=mergePerson(data.partner);current.partner=data.partner;current.blocked=data.blocked_by_me;current.canSend=data.can_send;const signature=JSON.stringify(data.partner);if(el('dmPartner').dataset.signature!==signature){el('dmPartner').dataset.signature=signature;el('dmPartner').innerHTML=avatar(data.partner)+'<div class="dm-person"><strong>'+esc(data.partner.name)+badgeMarkup(data.partner)+'</strong><small><i class="'+(data.partner.online?'online':'')+'"></i>'+(data.partner.online?'Online':'Offline')+'</small></div>';}el('dmInput').disabled=!data.can_send;el('dmForm').querySelector('button').disabled=!data.can_send||busy;if(!data.can_send){el('dmNotice').textContent='Bloklash sababli xabar yuborish o‘chirilgan.';el('dmNotice').hidden=false}else el('dmNotice').hidden=true}
  async function read(){if(!current||document.hidden)return;const id=current.id,last=Math.max(0,...messages.keys());if(last>(readMarkers.get(id)||0)){await request(`/chats/${id}/read`,'POST',{message_id:last});readMarkers.set(id,last)}}
  async function open(id){const ticket=++epoch;current={id};el('dmPartner').replaceChildren();delete el('dmPartner').dataset.signature;messages.clear();revision=0;before=null;more=false;cancelEdit();root.hidden=false;document.body.classList.add('dm-open');el('dmMessages').replaceChildren();try{const d=await request(`/chats/${id}/messages?include_avatar=${!people.has((cachedList?.chats.find(c=>c.id===id)?.partner.id))}`);if(ticket!==epoch)return;d.messages.forEach(m=>messages.set(m.id,m));revision=d.revision;before=d.before_id;more=d.more;partner(d);renderMessages();el('dmMessages').scrollTop=el('dmMessages').scrollHeight;await read()}catch(e){if(ticket===epoch)error(e)}}
  async function poll(){if(!current?.partner||document.hidden)return;const ticket=epoch,id=current.id;let d;do{d=await request(`/chats/${id}/messages?since_revision=${revision}&include_avatar=false`);if(ticket!==epoch)return;d.messages.forEach(m=>{if(!messages.has(m.id)||messages.get(m.id).revision<=m.revision)messages.set(m.id,m)});revision=Math.max(revision,d.revision);partner(d);if(d.messages.length)renderMessages()}while(d.more);await read()}
  async function older(){const ticket=epoch,id=current.id;const d=await request(`/chats/${id}/messages?before_id=${before}`);if(ticket!==epoch)return;d.messages.forEach(m=>messages.set(m.id,m));before=d.before_id;more=d.more;renderMessages()}
  el('dmBack').onclick=()=>{epoch++;current=null;messages.clear();revision=0;before=null;root.hidden=true;document.body.classList.remove('dm-open');cancelEdit();refreshList().catch(notice)};
  el('dmCancelEdit').onclick=cancelEdit;
  el('dmForm').onsubmit=async e=>{e.preventDefault();if(busy||!current?.canSend)return;const value=el('dmInput').value.trim();if(!value)return;busy=true;const ticket=epoch,id=current.id,editId=editing;try{await request(`/chats/${id}/messages`+(editId?`/${editId}`:''),editId?'PATCH':'POST',{text:value});if(ticket===epoch){cancelEdit();await poll();el('dmMessages').scrollTop=el('dmMessages').scrollHeight}}catch(e){if(ticket===epoch)error(e)}finally{busy=false;if(current)el('dmForm').querySelector('button').disabled=!current.canSend}};
  el('dmMenu').onclick=()=>{if(!current?.partner)return;const id=current.id,p=current.partner,blocked=current.blocked;actions([[blocked?'Blokdan chiqarish':'Bloklash',async()=>{if(!confirm(p.name+(blocked?' blokdan chiqarilsinmi?':' bloklansinmi?')))return;await request('/blocks/'+p.id,blocked?'DELETE':'POST');await poll()}],['Chatni ro‘yxatdan o‘chirish',()=>hide(id)]])};
  async function hide(id){if(!confirm('Chat sizning ro‘yxatingizdan o‘chirilsinmi?'))return;await request('/chats/'+id,'DELETE');if(current?.id===id)el('dmBack').click();await refreshList()}
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
      if(full)avatarSync=Date.now();
      lastListSync=Date.now();cachedList=d;
      const changed=JSON.stringify(d)!==listSignature;renderList(d);
      if(changed)void avatarCacheStore('put','dm-list:'+me.id,d);
    }finally{listPending=false}
  }
  document.querySelector('[data-page="instagram"]')?.addEventListener('click',()=>{void restoreList();void refreshList().catch(e=>notice(e.message))});
  async function loadMore(offset,b){try{const d=await request('/chats?offset='+offset);for(const c of d.chats){const n=document.createElement('button');n.className='dm-row';n.dataset.chatId=c.id;c.partner=mergePerson(c.partner);n.innerHTML=avatar(c.partner)+'<div class="dm-row-copy"><strong>'+esc(c.partner.name)+badgeMarkup(c.partner)+'</strong><small>'+esc(c.last_message?.text||'')+'</small></div><div class="dm-row-meta">'+esc(time(c.last_message_at))+(c.unread?'<span class="dm-unread">'+c.unread+'</span>':'')+'</div>';hold(n,()=>actions([['O‘chirish',()=>hide(c.id)]]));n.onclick=()=>open(c.id);b.before(n)}if(d.more)b.onclick=()=>loadMore(offset+d.chats.length,b);else b.remove()}catch(e){notice(e.message)}}
  tools.querySelector('button').onclick=async()=>{try{const rows=await request('/blocks');actions(rows.length?rows.map(p=>[p.name+' — blokdan chiqarish',async()=>{await request('/blocks/'+p.id,'DELETE');await refreshList()}]):[['Bloklanganlar yo‘q',()=>{}]])}catch(e){notice(e.message)}};
  const originalRender=renderUserSearchResults;renderUserSearchResults=rows=>{originalRender(rows);el('userSearchResults').querySelectorAll('.direct-result').forEach((n,i)=>{n.classList.add('dm-search-hit');n.tabIndex=0;n.setAttribute('role','button');const action=async()=>{try{const d=await request('/chats/with/'+rows[i].id,'POST');await open(d.chat_id)}catch(e){notice(e.message)}};n.onclick=action;n.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();action()}}})};
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
