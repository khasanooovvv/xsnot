(() => {
  const root=document.createElement('section');root.id='dating';root.hidden=true;
  root.innerHTML='<div class="dating-tabs"><button data-tab="cards" class="selected">Anketam</button><button data-tab="matches">Matchlar</button><button data-tab="edit">Tahrirlash</button></div><p class="dating-note" id="datingStatus" role="status"></p><div id="datingContent"></div>';
  document.querySelector('main').append(root);
  const nav=document.querySelector('nav#nav'),button=document.createElement('button');button.dataset.page='dating';button.title='Tanishuv';button.setAttribute('aria-label','Tanishuv');button.textContent='♡';
  nav.prepend(button);nav.append(nav.querySelector('[data-page="home"]'),nav.querySelector('[data-page="instagram"]'),nav.querySelector('[data-page="leaders"]'),nav.querySelector('[data-page="profile"]'));
  let tab='cards',own={photos:[],bio:''},rows=[],position=0,photo=0,busy=false,loaded=false;
  const content=root.querySelector('#datingContent'),status=root.querySelector('#datingStatus');
  function message(text){status.textContent=text;}
  const undoButton=document.createElement('button');undoButton.className='dating-undo';undoButton.textContent='↶ Anketani qaytarish';root.append(undoButton);
  undoButton.onclick=()=>work(async()=>{
    const likes=await api('dating/history');
    const dialog=document.createElement('dialog');dialog.className='dating-undo-dialog';
    const heading=document.createElement('h3');heading.textContent='Qaysi anketa qaytarilsin?';dialog.append(heading);
    if(!likes.length){const p=document.createElement('p');p.textContent='Qaytarish uchun anketa yo‘q.';dialog.append(p);}
    for(const p of likes){const b=document.createElement('button');b.textContent=p.name+(p.liked?' · ♥ Like':' · × O‘tkazilgan')+' — qaytarish';b.onclick=()=>work(async()=>{await api('dating/undo/'+p.id,{});dialog.close();dialog.remove();message('Amal bekor qilindi.');if(tab==='cards'||tab==='matches')await display();});dialog.append(b);}
    const close=document.createElement('button');close.textContent='Yopish';close.onclick=()=>dialog.close();dialog.append(close);dialog.addEventListener('close',()=>dialog.remove(),{once:true});document.body.append(dialog);dialog.showModal();
  });
  root.querySelector('.dating-tabs').addEventListener('click',e=>{
    const target=e.target.closest('button[data-tab]');
    if(!target||target.disabled||busy)return;
    try{
      const app=window.Telegram?.WebApp;
      if(typeof app?.HapticFeedback?.selectionChanged==='function'&&(!app.isVersionAtLeast||app.isVersionAtLeast('6.1')))app.HapticFeedback.selectionChanged();
    }catch{}
  },true);
  async function work(fn){if(busy)return;busy=true;root.querySelectorAll('button,input,textarea').forEach(b=>b.disabled=true);root.setAttribute('aria-busy','true');try{await fn();}catch(e){message(e.message);}finally{busy=false;root.removeAttribute('aria-busy');root.querySelectorAll('button,input,textarea').forEach(b=>b.disabled=false);}}
  async function load(){own=await api('dating/me');loaded=true;await display();}
  button.onclick=()=>{show('dating');work(load);};
  root.querySelectorAll('[data-tab]').forEach((b,index)=>b.onclick=()=>{if(busy)return;tab=b.dataset.tab;root.querySelector('.dating-tabs').style.setProperty('--tab-index',index);root.querySelectorAll('[data-tab]').forEach(x=>{x.classList.toggle('selected',x===b);x.setAttribute('aria-pressed',String(x===b));});message('');work(async()=>{if(!loaded)own=await api('dating/me');await display();});});
  async function display(){
    if(tab==='edit'){editor();return;}
    if(tab==='matches'){
      const matches=await api('dating/matches');content.replaceChildren();
      if(!matches.length){content.textContent='Hozircha o‘zaro like yo‘q.';return;}
      for(const p of matches){const b=document.createElement('button');b.className='dating-match';b.innerHTML='<img alt="Anketa rasmi" src="'+esc(p.photos[0])+'"><span>'+esc(p.name)+'<small> · O‘zaro like</small></span>';b.onclick=()=>work(async()=>{const d=await api('direct/chats/with/'+p.id,{});if(window.openDatingDirect)await window.openDatingDirect(d.chat_id);else message('DM oynasini qayta oching.');});content.append(b);}return;
    }
    own=await api('dating/me');
    if(!own.photos.length){content.innerHTML='<h3>Rasmingizdan boshlaymiz</h3><p class="dating-note">Anketa uchun rasm yuklang.</p><button class="dating-upload">Rasm yuklash</button>';content.querySelector('button').onclick=()=>{tab='edit';root.querySelector('[data-tab="edit"]').click();};return;}
    rows=await api('dating/cards');position=0;photo=0;renderCard();
    message('');
  }
  function renderCard(){
    const p=rows[position];if(!p){content.innerHTML='<p>Hozircha yangi anketalar yo‘q.</p><button class="dating-save">Yangilash</button>';content.querySelector('button').onclick=()=>work(display);return;}
    const bars=p.photos.map((_,i)=>'<i class="'+(i===photo?'current':'')+'"></i>').join('');
    content.innerHTML='<article class="dating-card"><img alt="Anketa rasmi" src="'+esc(p.photos[photo])+'"><div class="dating-photo-nav"><div class="dating-photo-bars" role="img" aria-label="'+(photo+1)+' / '+p.photos.length+' rasm">'+bars+'</div></div><div class="dating-copy"><div class="dating-identity"><h3>'+esc(p.name)+(p.age?'<span class="dating-age">, '+esc(p.age)+'</span>':'')+'</h3><small class="dating-city">'+esc(p.city)+'</small></div><p>'+esc(p.bio)+'</p></div><div class="dating-actions"><button class="skip" aria-label="O‘tkazish">×</button><button class="like" aria-label="Yoqtirish">♥</button></div></article>';
    content.querySelectorAll('.dating-actions button').forEach((b,i)=>b.onclick=()=>work(async()=>{content.querySelectorAll('button').forEach(x=>x.disabled=true);const r=await api('dating/vote/'+p.id,{liked:!!i});message(r.matched?'O‘zaro like! Matchlar bo‘limida ko‘rishingiz mumkin.':'');position++;photo=0;renderCard();}));
    const card=content.querySelector('article');let start=null;
    card.onpointerdown=e=>{if(e.isPrimary!==false&&!e.target.closest('button,.dating-copy'))start={x:e.clientX,y:e.clientY};};
    card.onpointerup=e=>{
      if(!start||busy)return;
      const dx=e.clientX-start.x,dy=e.clientY-start.y;start=null;
      if(Math.abs(dx)>90&&Math.abs(dx)>Math.abs(dy)){content.querySelectorAll('.dating-actions button')[dx>0?1:0].click();return;}
      if(Math.abs(dx)>10||Math.abs(dy)>10||e.target.closest('button,.dating-copy'))return;
      const bounds=card.getBoundingClientRect();
      photo=Math.max(0,Math.min(p.photos.length-1,photo+(e.clientX-bounds.left>=bounds.width/2?1:-1)));
      renderCard();
    };
    card.onpointercancel=()=>start=null;
  }
  function editor(){
    content.innerHTML='<strong>Anketa rasmlari · '+own.photos.length+'/6</strong><div class="dating-grid"></div><input type="file" accept="image/*" multiple hidden><label for="datingBio">Anketa uchun bio</label><textarea id="datingBio" maxlength="300" placeholder="O‘zingiz haqingizda qisqacha…"></textarea><p class="dating-note">6 tagacha rasm · Har biri 10 MB gacha</p><button class="dating-save">Saqlash</button>';
    const bio=content.querySelector('textarea');bio.value=own.bio;bio.oninput=()=>own.bio=bio.value;
    const input=content.querySelector('input'),grid=content.querySelector('.dating-grid');
    for(let i=0;i<6;i++){const tile=document.createElement('div');tile.className='dating-slot';if(own.photos[i]){tile.innerHTML='<img alt="Anketa rasmi '+(i+1)+'" src="'+esc(own.photos[i])+'"><button class="remove" aria-label="Rasmni o‘chirish">×</button><button class="cover">'+(i===0?'Asosiy rasm':'Asosiy qilish')+'</button>';tile.querySelector('.remove').onclick=()=>{if(busy)return;own.photos.splice(i,1);editor();};tile.querySelector('.cover').onclick=()=>{if(busy)return;own.photos.unshift(own.photos.splice(i,1)[0]);editor();};}else{tile.innerHTML='<button class="add" aria-label="Rasm qo‘shish">+</button>';tile.querySelector('button').onclick=()=>input.click();}grid.append(tile);}
    input.onchange=()=>work(async()=>{message('Rasmlar tayyorlanmoqda…');const files=Array.from(input.files);input.value='';for(const file of files){if(own.photos.length===6){message('Ko‘pi bilan 6 ta rasm.');break;}if(!file.type.startsWith('image/')||file.size>10*1024*1024){message('10 MB gacha rasm tanlang.');continue;}const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error('Rasm o‘qilmadi.'));reader.readAsDataURL(file);});const img=new Image();img.src=data;await img.decode();if(img.naturalWidth*img.naturalHeight>40000000)throw Error('Rasm o‘lchami juda katta.');const canvas=document.createElement('canvas'),scale=Math.min(1,1200/img.naturalWidth,1600/img.naturalHeight);canvas.width=Math.round(img.naturalWidth*scale);canvas.height=Math.round(img.naturalHeight*scale);const ctx=canvas.getContext('2d');ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0,canvas.width,canvas.height);own.photos.push(canvas.toDataURL('image/jpeg',.85));}editor();message('Rasmlar tayyor. Anketani chiqarish uchun Saqlashni bosing.');});
    content.querySelector('.dating-save').onclick=()=>work(async()=>{own=await api('dating/me',own);message('Anketa saqlandi.');editor();});
  }
})();
