(() => {
  'use strict';
  document.addEventListener('click', event => {
    const trigger = event.target.closest('#premiumSheet .premium-payments button:first-child');
    if (!trigger) return;
    const sheet = trigger.closest('#premiumSheet');
    const plan = sheet.querySelector('.premium-plan.active');
    const tier = sheet.querySelector('.premium-tier.active');
    if (!plan || !tier) return;
    const price = plan.querySelector('.gold-price').textContent.trim().replace(/(\d)\s+(?=\d)/g, '$1.');
    const dialog = document.createElement('dialog');
    dialog.className = 'card-payment';
    dialog.setAttribute('aria-labelledby', 'cardPaymentTitle');
    dialog.innerHTML = `
      <header class="card-payment-header"><button type="button" class="card-payment-back" aria-label="Orqaga">‹</button><h2 id="cardPaymentTitle">Obuna uchun to‘lov</h2></header>
      <div class="card-payment-body">
        <div class="card-payment-method"><span class="card-payment-logo">UZCARD</span><div><strong class="card-payment-network">UZCARD</strong><small>Karta orqali to‘lov</small></div><button type="button" class="card-payment-change">O‘zgartirish</button></div>
        <fieldset class="card-payment-choices" hidden><legend>To‘lov usuli</legend><label><input type="radio" name="paymentNetwork" value="UZCARD" checked> Uzcard</label><label><input type="radio" name="paymentNetwork" value="HUMO"> Humo</label></fieldset>
        <p class="card-payment-plan"></p><label for="cardPaymentAmount">To‘lov summasi</label><input id="cardPaymentAmount" readonly aria-readonly="true">
        <h3>TO‘LOV BOSQICHLARI</h3><ol><li>Obuna turi, muddati va summani tekshiring</li><li>Uzcard yoki Humo kartasini tanlang</li><li>To‘lov tasdiqlangach obunangiz faollashadi</li></ol>
        <p class="card-payment-note" role="status">Uzcard / Humo orqali to‘lov tez orada ishga tushadi.</p>
      </div><footer><button type="button" disabled>Davom etish</button></footer>`;
    dialog.querySelector('.card-payment-plan').textContent = tier.textContent.trim() + ' · ' + plan.querySelector('b').textContent.trim();
    dialog.querySelector('#cardPaymentAmount').value = price;
    const close = () => { dialog.close(); dialog.remove(); trigger.focus(); };
    dialog.querySelector('.card-payment-back').onclick = close;
    dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });
    dialog.addEventListener('click', event => { if (event.target === dialog) close(); });
    const choices = dialog.querySelector('.card-payment-choices');
    const change = dialog.querySelector('.card-payment-change');
    change.setAttribute('aria-expanded', 'false');
    change.onclick = () => { choices.hidden = !choices.hidden; change.setAttribute('aria-expanded', String(!choices.hidden)); };
    choices.onchange = event => {
      dialog.querySelector('.card-payment-logo').textContent = event.target.value;
      dialog.querySelector('.card-payment-network').textContent = event.target.value;
      choices.hidden = true;
      change.setAttribute('aria-expanded', 'false');
      change.focus();
    };
    document.body.append(dialog);
    dialog.showModal();
  });
})();
