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
        <div class="card-payment-method"><span class="card-payment-logo">UZCARD</span><div><strong class="card-payment-network">UZCARD</strong><small>Karta orqali to‘lov</small></div></div>
        <fieldset class="card-payment-choices" hidden><legend>To‘lov usuli</legend><label><input type="radio" name="paymentNetwork" value="UZCARD" checked> Uzcard</label><label><input type="radio" name="paymentNetwork" value="HUMO"> Humo</label></fieldset>
        <p class="card-payment-plan"></p><label for="cardPaymentAmount">To‘lov summasi</label><input id="cardPaymentAmount" readonly aria-readonly="true">
        <h3>TO‘LOV BOSQICHLARI</h3><ol><li>Obuna turi, muddati va summani tekshiring</li><li>Uzcard yoki Humo kartasini tanlang</li><li>To‘lov tasdiqlangach obunangiz faollashadi</li></ol>
        <p class="card-payment-note">Davom etib, pul o‘tkazish uchun karta ma’lumotlarini oling.</p>
      </div><footer><button type="button" class="card-payment-primary">Davom etish</button></footer>`;
    dialog.querySelector('.card-payment-plan').textContent = tier.textContent.trim() + ' · ' + plan.querySelector('b').textContent.trim();
    dialog.querySelector('#cardPaymentAmount').value = price;
    let timer;
    const close = () => { clearInterval(timer); dialog.close(); dialog.remove(); trigger.focus(); };
    dialog.querySelector('.card-payment-back').onclick = close;
    dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });
    dialog.addEventListener('click', event => { if (event.target === dialog) close(); });
    const choices = dialog.querySelector('.card-payment-choices');
    const change = dialog.querySelector('.card-payment-change');
    const networkButtons = [...dialog.querySelectorAll('.card-network-choice')];
    const selectNetwork = network => {
      networkButtons.forEach(button => {
        button.classList.toggle('active', button.dataset.network === network);
        button.setAttribute('aria-checked', String(button.dataset.network === network));
      });
      dialog.querySelector('.card-payment-logo').textContent = network;
      dialog.querySelector('.card-payment-network').textContent = network;
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
    const showTransfer = () => {
      initialBody.hidden = true;
      heading.textContent = 'To‘lov';
      const transfer = document.createElement('div');
      transfer.className = 'card-payment-body card-transfer';
      transfer.innerHTML = `
        <a class="card-support" href="https://t.me/xssupport" target="_blank" rel="noopener noreferrer">Support · @xssupport ↗</a>
        <p class="card-transfer-plan"></p>
        <div class="card-transfer-amount"><small>Aynan shu summani o‘tkazing</small><strong></strong><button type="button" data-copy="amount">Summani nusxalash</button></div>
        <div class="card-transfer-time"><span>To‘lov uchun vaqt</span><b>5:00</b><progress max="300" value="300" aria-label="Qolgan vaqt"></progress></div>
        <div class="card-transfer-bank"><small>Qabul qiluvchi karta raqami</small><strong data-card-number>5614 6818 8591 8346</strong><span data-card-owner>UZCARD · XASANOV SHERZOD</span><button type="button" data-copy="card">Karta raqamini nusxalash</button></div>
        <h3>TO‘LOV QOIDALARI</h3><ol><li>Ko‘rsatilgan summani aniq o‘tkazing</li><li>5 daqiqa ichida to‘lang</li><li>To‘lov chekini saqlang</li></ol>
        <p class="card-transfer-status" role="status">To‘lov kutilmoqda</p><p class="card-copy-status" role="status"></p>`;
      transfer.querySelector('.card-transfer-plan').textContent = initialBody.querySelector('.card-payment-plan').textContent;
      transfer.querySelector('.card-transfer-amount strong').textContent = price;
      initialBody.after(transfer);
      dialog.scrollTop = 0;
      const status = transfer.querySelector('.card-transfer-status');
      const deadline = Date.now() + 300000;
      const tick = () => {
        const seconds = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
        transfer.querySelector('.card-transfer-time b').textContent = Math.floor(seconds / 60) + ':' + String(seconds % 60).padStart(2, '0');
        transfer.querySelector('progress').value = seconds;
        if (!seconds) {
          clearInterval(timer);
          status.textContent = 'Vaqt tugadi. To‘lagan bo‘lsangiz, chek bilan @xssupport ga murojaat qiling.';
        }
      };
      tick();
      timer = setInterval(tick, 1000);
      transfer.addEventListener('click', async event => {
        const copy = event.target.closest('[data-copy]');
        if (!copy) return;
        const value = copy.dataset.copy === 'card' ? cardData[dialog.querySelector('.card-payment-network').textContent].plain : price.replace(/\D/g, '');
        const feedback = transfer.querySelector('.card-copy-status');
        try {
          await navigator.clipboard.writeText(value);
          feedback.textContent = 'Nusxa olindi';
        } catch {
          feedback.textContent = 'Nusxalab bo‘lmadi. Matnni belgilab nusxa oling: ' + value;
        }
      });
      footerButton.textContent = 'To‘lovni amalga oshirdim';
      footerButton.onclick = () => {
        clearInterval(timer);
        status.textContent = 'To‘lov chekini @xssupport ga yuboring. Obuna to‘lov tasdiqlangach faollashadi.';
        status.scrollIntoView({block:'center'});
        footerButton.textContent = 'Support’ga yozish';
        footerButton.onclick = () => {
          if (window.Telegram?.WebApp?.openTelegramLink) window.Telegram.WebApp.openTelegramLink('https://t.me/xssupport');
          else window.open('https://t.me/xssupport', '_blank', 'noopener,noreferrer');
        };
      };
      const updateTransferCard = network => {
        const card = cardData[network];
        transfer.querySelector('[data-card-number]').textContent = card.number;
        transfer.querySelector('[data-card-owner]').textContent = network + ' · XASANOV SHERZOD';
      };
      updateTransferCard(dialog.querySelector('.card-payment-network').textContent);
      back.onclick = () => {
        clearInterval(timer);
        transfer.remove();
        initialBody.hidden = false;
        heading.textContent = 'Obuna uchun to‘lov';
        footerButton.textContent = 'Davom etish';
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
