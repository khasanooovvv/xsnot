(() => {
  function mount(){
    const info=document.getElementById('profileInfo');
    if(!info||document.getElementById('profileShop'))return;
    const shop=document.createElement('div');shop.id='profileShop';shop.className='profile-shop';
    shop.innerHTML='<button type="button" data-buy-gold><span class="profile-shop-label"><span class="profile-shop-shimmer">Gold / Gold Plus</span><svg class="profile-shop-gold" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 1.5 15 3l3.3.3 1.4 3 2.3 2.4-.6 3.3.6 3.3-2.3 2.4-1.4 3-3.3.3-3 1.5-3-1.5-3.3-.3-1.4-3L2 15.3l.6-3.3L2 8.7l2.3-2.4 1.4-3L9 3Z"/><path d="m7.4 12.1 3 3 6.2-6.2" fill="none" stroke="#332400" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/></svg></span></button><button type="button" data-buy-username><span class="profile-shop-username">@ Username sotib olish</span><span>›</span></button>';
    info.after(shop);
    shop.querySelector('[data-buy-gold]').onclick=()=>showPremiumSheet('gold');
    shop.querySelector('[data-buy-username]').onclick=()=>{
      const dialog=document.createElement('dialog');dialog.className='username-shop';
      dialog.innerHTML='<button type="button" class="username-shop-close" aria-label="Yopish">×</button><h2>@ Username</h2><p>1–4 belgili unikal username’larni sotib olish</p><a href="https://t.me/the_pasibo" target="_blank" rel="noopener">Admin bilan bog‘lanish ↗</a>';
      document.body.append(dialog);dialog.showModal();
      dialog.querySelector('button').onclick=()=>{dialog.close();dialog.remove()};
      dialog.addEventListener('close',()=>dialog.remove(),{once:true});
    };
  }
  mount();
})();
