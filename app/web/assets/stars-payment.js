(() => {
  const prices={gold:{7:50,30:150,90:350},plus:{7:75,30:250,90:600}};
  function update(sheet){
    const payments=sheet.querySelector('.premium-payments');
    if(!payments)return;
    let button=payments.querySelector('[data-stars-pay]');
    if(!button){button=document.createElement('button');button.type='button';button.dataset.starsPay='1';payments.append(button)}
    const tier=sheet.querySelector('.premium-tier.active')?.dataset.tier||'gold';
    const days=Number(sheet.querySelector('.premium-plan.active')?.dataset.days);
    const text='⭐ Stars bilan to‘lash · '+prices[tier]?.[days]+' ⭐';
    if(button.textContent!==text)button.textContent=text;
  }
  new MutationObserver(()=>{const sheet=document.querySelector('#premiumSheet');if(sheet)update(sheet)}).observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});
  document.addEventListener('click',async event=>{
    const button=event.target.closest('[data-stars-pay]');if(!button)return;
    const sheet=button.closest('#premiumSheet'),webapp=window.Telegram?.WebApp;
    if(!webapp?.openInvoice){notice('To‘lov uchun Telegram Mini App’ni oching.');return}
    button.disabled=true;
    try{
      const tier=sheet.querySelector('.premium-tier.active').dataset.tier;
      const days=Number(sheet.querySelector('.premium-plan.active').dataset.days);
      const invoice=await api('stars/invoice',{tier,days});
      webapp.openInvoice(invoice.url,status=>{
        button.disabled=false;
        if(status==='paid'){sheet.remove();notice('To‘lov bajarildi. Obuna server tasdig‘idan keyin faollashadi.');}
        else if(status==='failed')notice('To‘lov bajarilmadi. Qayta urinib ko‘ring.');
      });
    }catch(error){notice(error.message);button.disabled=false}
  });
})();
