(() => {
  const root=document.createElement('section');root.id='dating';root.hidden=true;
  root.innerHTML='<h2>Tanishuv</h2><div class="dating-tabs"><button data-tab="cards" class="selected">Anketam</button><button data-tab="matches">Matchlar</button><button data-tab="edit">Tahrirlash</button></div><p class="dating-note" id="datingStatus" role="status"></p><div id="datingContent"></div>';
  document.querySelector('main').append(root);
  const nav=document.querySelector('nav#nav'),button=document.createElement('button');button.dataset.page='dating';button.title='Tanishuv';button.setAttribute('aria-label','Tanishuv');button.textContent='♡';
  nav.prepend(button);nav.append(nav.querySelector('[data-page="home"]'),nav.querySelector('[data-page="instagram"]'),nav.querySelector('[data-page="leaders"]'),nav.querySelector('[data-page="profile"]'));
  let tab='cards',own={photos:[],bio:''},rows=[],position=0,photo=0,busy=false,loaded=false;
  const content=root.querySelector('#datingContent'),status=root.querySelector('#datingStatus');
  function message(text){status.textContent=text;}
  async function work(fn){if(busy)return;busy=true;try{await fn();}catch(e){message(e.message);}finally{busy=false;root.querySelectorAll('button').forEach(b=>b.disabled=false);}}
  async function load(){own=await api('dating/me');loaded=true;await display();}
  button.onclick=()=>{show('dating');work(load);};
  root.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{if(busy)return;tab=b.dataset.tab;root.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('selected',x===b));message('');work(async()=>{if(!loaded)own=await api('dating/me');await display();});});
  async function display(){
    if(tab==='edit'){editor();return;}
    if(tab==='matches'){
      const matches=await api('dating/matches');content.replaceChildren();
      if(!matches.length){content.textContent='Hozircha o‘zaro like yo‘q.';return;}
      for(const p of matches){const b=document.createElement('button');b.className='dating-match';b.innerHTML='<img alt="Anketa rasmi" src="'+esc(p.photos[0])+'"><span>'+esc(p.name)+'<small> · O‘zaro like</small></span>';b.onclick=()=>work(async()=>{const d=await api('direct/chats/with/'+p.id,{});if(window.openDatingDirect)await window.openDatingDirect(d.chat_id);else message('DM oynasini qayta oching.');});content.append(b);}return;
    }
    if(!own.photos.length){content.innerHTML='<h3>Rasmingizdan boshlaymiz</h3><p class="dating-note">Ism, yosh va shahar profilingizdan olinadi. Anketa uchun rasm yuklang.</p><button class="dating-upload">Rasm yuklash</button>';content.querySelector('button').onclick=()=>{tab='edit';root.querySelector('[data-tab="edit"]').click();};return;}
    rows=await api('dating/cards');position=0;photo=0;renderCard();
  }
  function renderCard(){
    const p=rows[position];if(!p){content.innerHTML='<p>Hozircha yangi anketalar yo‘q.</p><button class="dating-save">Yangilash</button>';content.querySelector('button').onclick=()=>work(display);return;}
    content.innerHTML='<article class="dating-card"><img alt="Anketa rasmi" src="'+esc(p.photos[photo])+'"><div class="dating-photo-nav"><button aria-label="Oldingi rasm">‹</button><small>'+(photo+1)+'/'+p.photos.length+'</small><button aria-label="Keyingi rasm">›</button></div><div class="dating-copy"><h3>'+esc(p.name)+(p.age?', '+p.age:'')+'</h3><small>'+esc(p.city)+'</small><p>'+esc(p.bio)+'</p></div></article><div class="dating-actions"><button aria-label="O‘tkazish">×</button><button aria-label="Yoqtirish">♡</button></div>';
    content.querySelectorAll('.dating-photo-nav button').forEach((b,i)=>b.onclick=()=>{photo=(photo+(i?1:-1)+p.photos.length)%p.photos.length;renderCard();});
    content.querySelectorAll('.dating-actions button').forEach((b,i)=>b.onclick=()=>work(async()=>{content.querySelectorAll('button').forEach(x=>x.disabled=true);const r=await api('dating/vote/'+p.id,{liked:!!i});message(r.matched?'O‘zaro like! Matchlar bo‘limida ko‘rishingiz mumkin.':'');position++;photo=0;renderCard();}));
    const card=content.querySelector('article');let start=null;card.onpointerdown=e=>{if(!e.target.closest('button'))start=e.clientX;};card.onpointerup=e=>{if(start===null)return;const dx=e.clientX-start;start=null;if(Math.abs(dx)>90)content.querySelectorAll('.dating-actions button')[dx>0?1:0].click();};card.onpointercancel=()=>start=null;
  }
  function editor(){
    content.innerHTML='<strong>Anketa rasmlari · '+own.photos.length+'/6</strong><div class="dating-grid"></div><input type="file" accept="image/*" multiple hidden><label for="datingBio">Anketa uchun bio</label><textarea id="datingBio" maxlength="300" placeholder="O‘zingiz haqingizda qisqacha…"></textarea><p class="dating-note">6 tagacha rasm · Har biri 10 MB gacha · Bio 300 belgigacha. O‘zgarishlar Saqlash bosilganda bazaga yoziladi.</p><button class="dating-save">Saqlash</button>';
    const bio=content.querySelector('textarea');bio.value=own.bio;bio.oninput=()=>own.bio=bio.value;
    const input=content.querySelector('input'),grid=content.querySelector('.dating-grid');
    for(let i=0;i<6;i++){const tile=document.createElement('div');tile.className='dating-slot';if(own.photos[i]){tile.innerHTML='<img alt="Anketa rasmi '+(i+1)+'" src="'+esc(own.photos[i])+'"><button class="remove" aria-label="Rasmni o‘chirish">×</button><button class="cover">'+(i===0?'Asosiy rasm':'Asosiy qilish')+'</button>';tile.querySelector('.remove').onclick=()=>{if(busy)return;own.photos.splice(i,1);editor();};tile.querySelector('.cover').onclick=()=>{if(busy)return;own.photos.unshift(own.photos.splice(i,1)[0]);editor();};}else{tile.innerHTML='<button class="add" aria-label="Rasm qo‘shish">+</button>';tile.querySelector('button').onclick=()=>input.click();}grid.append(tile);}
    input.onchange=()=>work(async()=>{const files=Array.from(input.files);input.value='';for(const file of files){if(own.photos.length===6){message('Ko‘pi bilan 6 ta rasm.');break;}if(!file.type.startsWith('image/')||file.size>10*1024*1024){message('10 MB gacha rasm tanlang.');continue;}const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error('Rasm o‘qilmadi.'));reader.readAsDataURL(file);});const img=new Image();img.src=data;await img.decode();if(img.naturalWidth*img.naturalHeight>40000000)throw Error('Rasm o‘lchami juda katta.');const canvas=document.createElement('canvas'),scale=Math.min(1,1200/img.naturalWidth,1600/img.naturalHeight);canvas.width=Math.round(img.naturalWidth*scale);canvas.height=Math.round(img.naturalHeight*scale);const ctx=canvas.getContext('2d');ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0,canvas.width,canvas.height);own.photos.push(canvas.toDataURL('image/jpeg',.85));}editor();});
    content.querySelector('.dating-save').onclick=()=>work(async()=>{own=await api('dating/me',own);message('Anketa saqlandi.');editor();});
  }
})();
