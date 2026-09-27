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
    const cardData = {
      UZCARD: {number: '5614 6818 8591 8346', plain: '5614681885918346'},
      HUMO: {number: '9860 3566 4537 9963', plain: '9860356645379963'}
    };
    const dialog = document.createElement('dialog');
    dialog.className = 'card-payment';
    dialog.setAttribute('aria-labelledby', 'cardPaymentTitle');
    dialog.innerHTML = `
      <header class="card-payment-header"><button type="button" class="card-payment-back" aria-label="Orqaga">‹</button><h2 id="cardPaymentTitle">Obuna uchun to‘lov</h2></header>
      <div class="card-payment-body">
        <div class="card-payment-methods" role="radiogroup" aria-label="Karta turi"><button type="button" class="card-network-choice active" data-network="UZCARD"><img src="/assets/uzcard-logo.jpg" alt="UZCARD"><strong>UZCARD</strong></button><button type="button" class="card-network-choice" data-network="HUMO"><img src="/assets/humo-logo.png" alt="HUMO"><strong>HUMO</strong></button></div>
        <fieldset class="card-payment-choices" hidden><legend>To‘lov usuli</legend><label><input type="radio" name="paymentNetwork" value="UZCARD" checked> Uzcard</label><label><input type="radio" name="paymentNetwork" value="HUMO"> Humo</label></fieldset>
        <p class="card-payment-plan"></p><label for="cardPaymentAmount">To‘lov summasi</label><input id="cardPaymentAmount" readonly aria-readonly="true">
        <h3>TO‘LOV BOSQICHLARI</h3><ol><li>Obuna turi, muddati va summani tekshiring</li><li>Uzcard yoki Humo kartasini tanlang</li><li>To‘lov tasdiqlangach obunangiz faollashadi</li></ol>
        <p class="card-payment-note">Davom etib, pul o‘tkazish uchun karta ma’lumotlarini oling.</p>
      </div><footer><button type="button" class="card-payment-primary">Davom etish</button></footer>`;
    dialog.querySelector('.card-payment-plan').textContent = tier.textContent.trim() + ' · ' + plan.querySelector('b').textContent.trim();
    dialog.querySelector('#cardPaymentAmount').value = price;
    const toast = document.createElement('div');
    toast.className = 'card-copy-toast';
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    dialog.prepend(toast);
    let toastTimer;
    const notifyCopy = message => {
      if (!dialog.isConnected) return;
      clearTimeout(toastTimer);
      toast.textContent = message;
      toast.classList.add('visible');
      toastTimer = setTimeout(() => { toast.classList.remove('visible'); toast.textContent = ''; }, 3000);
    };
    let timer;
    let pollTimer;
    const close = () => { clearInterval(timer); clearTimeout(pollTimer); clearTimeout(toastTimer); dialog.close(); dialog.remove(); trigger.focus(); };
    dialog.querySelector('.card-payment-back').onclick = close;
    dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });
    dialog.addEventListener('click', event => { if (event.target === dialog) close(); });
    const choices = dialog.querySelector('.card-payment-choices');
    let selectedNetwork = 'UZCARD';
    const networkButtons = [...dialog.querySelectorAll('.card-network-choice')];
    const selectNetwork = network => {
      selectedNetwork = network;
      networkButtons.forEach(button => {
        button.classList.toggle('active', button.dataset.network === network);
        button.setAttribute('aria-checked', String(button.dataset.network === network));
      });
      const transferCard = dialog.querySelector('.card-transfer');
      if (transferCard) {
        transferCard.querySelector('[data-card-number]').textContent = cardData[network].number;
        transferCard.querySelector('[data-card-owner]').textContent = network + ' · XASANOV SHERZOD';
      }
    };
    networkButtons.forEach(button => { button.onclick = () => selectNetwork(button.dataset.network); });
    choices.onchange = event => {
      selectNetwork(event.target.value);
      choices.hidden = true;
    };
    const initialBody = dialog.querySelector('.card-payment-body');
    const footerButton = dialog.querySelector('footer button');
    const back = dialog.querySelector('.card-payment-back');
    const heading = dialog.querySelector('#cardPaymentTitle');
    const requestOrder = async (id, body) => {
      const response = await fetch('/api/card-orders' + (id ? '/' + id : ''), {
        method: body ? 'POST' : 'GET', cache: 'no-store',
        headers: {'Content-Type': 'application/json', 'X-Telegram-Init-Data': window.Telegram?.WebApp?.initData || ''},
        body: body ? JSON.stringify(body) : undefined
      });
      if (!response.ok) throw new Error('To‘lov holatini tekshirib bo‘lmadi. Qayta urinib ko‘ring.');
      return response.json();
    };
    const showTransfer = async (switchNetwork = false) => {
      footerButton.disabled = true;
      let order;
      try {
        order = await requestOrder(null, {network: selectedNetwork, tier: tier.dataset.tier, days: Number(plan.dataset.days), switch: switchNetwork === true});
      } catch (error) {
        notifyCopy(error.message);
        footerButton.disabled = false;
        footerButton.textContent = 'Davom etish';
        footerButton.onclick = showTransfer;
        return;
      }
      if (!dialog.isConnected) return;
      selectedNetwork = order.network;
      const orderPrice = order.amount.toLocaleString('uz-UZ') + ' so‘m';
      footerButton.disabled = false;
      initialBody.hidden = true;
      heading.textContent = 'To‘lov';
      const transfer = document.createElement('div');
      transfer.className = 'card-payment-body card-transfer';
      transfer.innerHTML = `
        <a class="card-support" href="https://t.me/xssupport" target="_blank" rel="noopener noreferrer"><svg class="card-support-icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 13v-3a8 8 0 0 1 16 0v3M20 17v1a3 3 0 0 1-3 3h-3"/><rect x="2" y="10" width="4" height="8" rx="2"/><rect x="18" y="10" width="4" height="8" rx="2"/><path d="M11 21h3"/></svg><span><strong>Support</strong><small>24/7 yordam</small></span></a>
        <p class="card-transfer-plan"></p>
        <div class="card-transfer-amount"><small>Aynan shu summani o‘tkazing</small><strong></strong><button type="button" data-copy="amount">Summani nusxalash</button></div>
        <div class="card-transfer-time"><span>To‘lov uchun vaqt</span><b>5:00</b><progress max="300" value="300" aria-label="Qolgan vaqt"></progress></div>
        <div class="card-transfer-bank"><small>Qabul qiluvchi karta raqami</small><strong data-card-number>5614 6818 8591 8346</strong><span data-card-owner>UZCARD · XASANOV SHERZOD</span><button type="button" data-copy="card">Karta raqamini nusxalash</button></div>
        <h3>TO‘LOV QOIDALARI</h3><ol><li>Ko‘rsatilgan summani aniq o‘tkazing</li><li>5 daqiqa ichida to‘lang</li><li>To‘lov chekini saqlang</li></ol>
        <p class="card-transfer-status" role="status">To‘lov kutilmoqda</p><p class="card-copy-status" role="status"></p>`;
      transfer.querySelector('.card-transfer-plan').textContent = (order.tier === 'plus' ? 'Gold Plus' : 'Gold') + ' · ' + order.days + ' kun';
      transfer.querySelector('.card-transfer-amount strong').textContent = orderPrice;
      initialBody.after(transfer);
      dialog.scrollTop = 0;
      const status = transfer.querySelector('.card-transfer-status');
      let deadline = Date.now() + order.remaining * 1000;
      const tick = () => {
        const seconds = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
        transfer.querySelector('.card-transfer-time b').textContent = Math.floor(seconds / 60) + ':' + String(seconds % 60).padStart(2, '0');
        transfer.querySelector('progress').value = seconds;
        if (!seconds) {
          if (order.status === 'active') {
            status.textContent = 'To‘lov vaqti tugadi. Agar to‘lov qilgan bo‘lsangiz, supportga murojaat qiling.';
          }
        }
      };
      tick();
      timer = setInterval(tick, 1000);
      transfer.addEventListener('click', async event => {
        const copy = event.target.closest('[data-copy]');
        if (!copy) return;
        const value = copy.dataset.copy === 'card' ? cardData[selectedNetwork].plain : String(order.amount);
        try {
          await navigator.clipboard.writeText(value);
          notifyCopy(copy.dataset.copy === 'card' ? 'Karta raqami nusxalandi' : 'Summa nusxalandi');
        } catch {
          notifyCopy('Nusxalab bo‘lmadi. Qayta urinib ko‘ring.');
        }
      });
      const support = transfer.querySelector('.card-support').cloneNode(true);
      support.hidden = true;
      status.after(support);
      const renderOrder = () => {
        const active = order.status === 'active';
        transfer.querySelectorAll('.card-transfer-amount,.card-transfer-bank,.card-transfer-time,h3,ol').forEach(el => { el.hidden = !active; });
        support.hidden = !['expired', 'cancelled'].includes(order.status);
        footerButton.disabled = false;
        if (order.status === 'queued') {
          status.textContent = 'Kutish rejimi. Navbat: ' + order.position + '. Hozircha pul yubormang.' + (order.alternative ? ' ' + order.alternative + ' bo‘sh — foydalanishingiz mumkin.' : '');
          footerButton.textContent = order.alternative ? order.alternative + ' orqali to‘lash' : 'Navbat kutilmoqda';
          footerButton.disabled = !order.alternative;
          footerButton.onclick = async () => {
            selectedNetwork = order.alternative;
            clearInterval(timer); clearTimeout(pollTimer);
            transfer.remove(); initialBody.hidden = false;
            await showTransfer(true);
          };
        } else if (active) {
          status.textContent = 'To‘lov kutilmoqda. Avtomatik tekshirilmoqda.';
          footerButton.textContent = 'To‘lovni tekshirish';
          footerButton.onclick = () => pollOrder();
        } else if (order.status === 'paid') {
          status.textContent = 'To‘lov tasdiqlandi! Obunangiz faollashtirildi.';
          footerButton.textContent = 'Yopish'; footerButton.onclick = close;
        } else {
          status.textContent = order.status === 'expired' ? 'To‘lov vaqti tugadi. Agar to‘lov qilgan bo‘lsangiz, supportga murojaat qiling.' : 'Navbat bekor qilindi. Qayta buyurtma ochishingiz mumkin.';
          footerButton.textContent = 'Support’ga yozish';
          footerButton.onclick = () => support.click();
        }
        if (!['active', 'queued'].includes(order.status)) { clearInterval(timer); clearTimeout(pollTimer); }
      };
      let checking = false;
      const pollOrder = async () => {
        if (checking || !transfer.isConnected) return;
        checking = true; clearTimeout(pollTimer);
        try {
          const latest = await requestOrder(order.id);
          if (!transfer.isConnected) return;
          order = latest;
          deadline = Date.now() + order.remaining * 1000;
          renderOrder(); tick();
        } catch (error) { if (transfer.isConnected) status.textContent = error.message; }
        finally {
          checking = false;
          if (transfer.isConnected && ['active', 'queued'].includes(order.status)) pollTimer = setTimeout(pollOrder, 3000);
        }
      };
      renderOrder();
      if (['active', 'queued'].includes(order.status)) pollTimer = setTimeout(pollOrder, 3000);
      const updateTransferCard = network => {
        const card = cardData[network];
        transfer.querySelector('[data-card-number]').textContent = card.number;
        transfer.querySelector('[data-card-owner]').textContent = network + ' · XASANOV SHERZOD';
      };
      updateTransferCard(selectedNetwork);
      back.onclick = () => {
        clearInterval(timer);
        clearTimeout(pollTimer);
        transfer.remove();
        initialBody.hidden = false;
        heading.textContent = 'Obuna uchun to‘lov';
        footerButton.textContent = 'Davom etish';
        footerButton.disabled = false;
        footerButton.onclick = showTransfer;
        back.onclick = close;
        dialog.scrollTop = 0;
      };
    };
    footerButton.onclick = showTransfer;
    document.body.append(dialog);
    dialog.showModal();
  });
})();
