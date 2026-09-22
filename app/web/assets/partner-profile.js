(() => {
  const header = $('reveal');
  header.setAttribute('role', 'button');
  header.setAttribute('tabindex', '0');
  header.setAttribute('aria-label', 'Suhbatdosh profilini ko‘rish');
  header.setAttribute('aria-haspopup', 'dialog');
  header.title = 'Profilni ko‘rish';
  const dialog = document.createElement('dialog');
  dialog.id = 'partnerProfileDialog';
  dialog.setAttribute('aria-labelledby', 'partnerProfileTitle');
  dialog.innerHTML = '<button id="closePartnerProfile" type="button" aria-label="Yopish">×</button><h2 id="partnerProfileTitle">Suhbatdosh profili</h2><div id="partnerProfileContent" aria-live="polite"></div>';
  document.body.append(dialog);
  const style = document.createElement('style');
  style.textContent = '#reveal[role="button"]{cursor:pointer}#reveal[role="button"]:focus-visible{outline:2px solid #c7a7ff;outline-offset:2px}#partnerProfileDialog{width:min(92vw,410px);max-height:85dvh;overflow:auto;padding:24px;border:1px solid #584776;border-radius:26px;background:radial-gradient(ellipse at top,#302342,#111725 70%);color:#f3f5ff;text-align:center;box-shadow:0 24px 80px #0009}#partnerProfileDialog::backdrop{background:#040710bd;backdrop-filter:blur(6px)}#closePartnerProfile{width:38px;height:38px;display:block;margin:0 0 0 auto;padding:0;background:#ffffff0c;color:#cbbfdd;font-size:26px;border-radius:50%}#partnerProfileTitle{font-size:15px;font-weight:500;color:#b8accb;margin:0 0 22px}#partnerProfileContent .avatar{width:112px;height:112px;border-radius:50%;font-size:38px;margin:0 auto 18px;border:2px solid #9b78c4;box-shadow:0 8px 28px #0005}#partnerProfileContent h3{font-size:24px;margin:0 0 8px;overflow-wrap:anywhere}#partnerProfileContent .partner-handle{color:#c7a7ff;font-size:15px;overflow-wrap:anywhere}#partnerProfileContent .partner-bio{white-space:pre-wrap;overflow-wrap:anywhere;font-size:15px;line-height:1.6;padding:18px 0;margin:16px 0 0;border-top:1px solid #ffffff14}#partnerProfileContent .partner-meta{color:#a9b2c7;font-size:14px;margin-top:12px}#partnerProfileContent .partner-error{color:#ffb4c1}#partnerProfileContent .gold-lock{color:#d8c6ff;line-height:1.6;margin:18px 0}#partnerProfileContent #buyGold{width:100%;margin:0;padding:13px;border:0;border-radius:14px;background:linear-gradient(135deg,#9b6cff,#6840d5);color:#fff;font-weight:700}';
  document.head.append(style);
  let generation = 0, shownMatch = null, shownAnonymous = null, latestAnonymous = null;
  function close() {
    generation++;
    shownMatch = null;
    shownAnonymous = null;
    $('partnerProfileContent').replaceChildren();
    if (dialog.open) dialog.close();
  }
  dialog.addEventListener('close', close);
  $('closePartnerProfile').onclick = close;
  dialog.addEventListener('click', event => {
    const rect = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) close();
  });
  async function open() {
    if (!match || dialog.open) return;
    const current = ++generation, id = match;
    shownMatch = id;
    shownAnonymous = latestAnonymous;
    $('partnerProfileContent').textContent = 'Profil yuklanmoqda…';
    document.activeElement?.blur();
    dialog.showModal();
    if (Number(me?.gold) <= 0) {
      $('partnerProfileContent').innerHTML = '<div class="gold-lock">🔒 Bu funksiya faqat Gold obunachilar uchun mavjud.<br>Gold’ga o‘ting va suhbatdoshingiz profilini ko‘ring.</div><button id="buyGold" type="button">🥇 Gold sotib olish</button>';
      $('buyGold').onclick = () => notice('Gold to‘lov tizimi tez orada qo‘shiladi.');
      return;
    }
    try {
      const result = await api('chat/partner?match_id=' + encodeURIComponent(id));
      if (current !== generation || match !== id || !dialog.open || result.match !== id) return;
      const person = result.partner;
      shownAnonymous = person.anonymous;
      let markup = avatar(person) + '<h3>' + esc(person.name) + (person.anonymous ? '' : badgeMarkup(person)) + '</h3>';
      if (person.anonymous) {
        markup += '<p class="muted">Suhbatdosh anonim rejimda. Profil ma’lumotlari yashirilgan.</p>';
      } else {
        if (person.app_username) markup += '<div class="partner-handle">@' + esc(person.app_username) + '</div>';
        const meta = [person.city, person.age ? person.age + ' yosh' : ''].filter(Boolean);
        if (meta.length) markup += '<div class="partner-meta">' + esc(meta.join(' • ')) + '</div>';
        markup += '<p class="partner-bio">' + esc(person.bio || 'Bio hali yozilmagan.') + '</p>';
      }
      $('partnerProfileContent').innerHTML = markup;
    } catch (error) {
      if (current !== generation || !dialog.open) return;
      const message = document.createElement('p');
      message.className = 'partner-error';
      message.textContent = error.message;
      $('partnerProfileContent').replaceChildren(message);
    }
  }
  header.addEventListener('click', open);
  header.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); open(); }
  });
  window.partnerProfile = { close, sync(id, anonymous) {
    latestAnonymous = anonymous;
    if (dialog.open && (shownMatch !== id || (shownAnonymous !== null && shownAnonymous !== anonymous))) close();
  } };
})();
