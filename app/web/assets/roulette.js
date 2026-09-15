(() => {
  const panel = document.createElement('div');
  panel.id = 'roulette';
  panel.hidden = true;
  panel.innerHTML = '<div class="roulette-window"><div class="roulette-marker" aria-hidden="true"></div><div class="roulette-track"></div></div><p class="roulette-status" role="status"></p><button class="roulette-retry secondary" type="button" aria-label="Qayta aylantirish"><span aria-hidden="true">⟳</span> Qayta aylantirish</button>';
  $('messages').before(panel);
  const track = panel.querySelector('.roulette-track');
  const status = panel.querySelector('.roulette-status');
  const retry = panel.querySelector('.roulette-retry');
  const viewport = panel.querySelector('.roulette-window');
  const invitationBox = document.createElement('div');
  invitationBox.className = 'roulette-invitation';
  invitationBox.hidden = true;
  invitationBox.innerHTML = '<div class="invitation-person"></div><div class="row"><button type="button" class="invitation-accept">Qabul qilish</button><button type="button" class="invitation-reject secondary">Rad etish</button><button type="button" class="invitation-cancel secondary">Taklifni bekor qilish</button></div>';
  viewport.after(invitationBox);
  const accept = invitationBox.querySelector('.invitation-accept');
  const reject = invitationBox.querySelector('.invitation-reject');
  const cancel = invitationBox.querySelector('.invitation-cancel');
  const style = document.createElement('style');
  style.textContent = '#roulette{padding:24px 0;text-align:center}body.chat-searching #messages{display:none}.roulette-window{position:relative;overflow:hidden;height:202px;border:1px solid #384365;border-radius:24px;background:radial-gradient(ellipse at center,#302347,#0c1220 75%)}.roulette-window:after{content:"";position:absolute;inset:0;pointer-events:none;background:linear-gradient(90deg,#0c1220,transparent 22%,transparent 78%,#0c1220)}.roulette-marker{position:absolute;left:50%;top:14px;bottom:14px;width:124px;transform:translateX(-50%);border:2px solid #bc96ff;border-radius:20px;box-shadow:0 0 24px #9461e644;pointer-events:none;z-index:2}.roulette-track{display:flex;align-items:center;height:100%;width:max-content;will-change:transform}.roulette-card{flex:0 0 132px;width:132px;margin:0;padding:16px 8px;background:transparent;border-radius:18px;color:#c5bed6;opacity:1!important;cursor:default!important}.roulette-card .avatar{width:88px;height:88px;border-radius:50%;border:2px solid #5d4c78;box-shadow:0 5px 20px #0005}.roulette-card strong{display:block;width:112px;margin:12px auto 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:14px}.roulette-card.chosen{color:#fff;cursor:pointer!important}.roulette-card.chosen .avatar{border-color:#dfbeff;box-shadow:0 0 25px #ab72ff88}.roulette-card:focus-visible{outline:2px solid #e5ceff;outline-offset:-5px}.roulette-status{color:#c6b6df;min-height:44px;font-size:14px;padding:0 12px}.roulette-retry{max-width:250px;border:1px solid #5d4c78!important;background:#231e35!important}.roulette-retry span{font-size:24px;vertical-align:middle;margin-right:8px}body.chat-fullscreen #roulette{display:none}';
  document.head.append(style);
  const invitationStyle = document.createElement('style');
  invitationStyle.textContent = '.roulette-invitation{padding:24px 18px;border:1px solid #705292;border-radius:24px;background:radial-gradient(ellipse at top,#342444,#121827)}.invitation-person .avatar{width:96px;height:96px;border-radius:50%;margin-bottom:14px;border:2px solid #b28ee0}.invitation-person strong{display:block;overflow-wrap:anywhere;margin-bottom:18px;font-size:20px}.invitation-reject{background:#493044!important}.invitation-accept{background:#7552c9!important}';
  document.head.append(invitationStyle);
  let generation = 0, running = false, ticket = null, timer = null, animation = null, currentInvitation = null;
  function reset() {
    generation++;
    running = false;
    ticket = null;
    clearTimeout(timer);
    animation?.cancel();
    animation = null;
    panel.hidden = true;
    currentInvitation = null;
    invitationBox.hidden = true;
    viewport.hidden = false;
    retry.hidden = false;
    track.replaceChildren();
  }
  function showInvitation(invitation) {
    if (currentInvitation?.id !== invitation.id) {
      reset();
      invitationBox.querySelectorAll('button').forEach(button => button.disabled = false);
    }
    currentInvitation = invitation;
    panel.hidden = false;
    invitationBox.hidden = false;
    viewport.hidden = true;
    retry.hidden = true;
    const person = invitation.person;
    const markup = avatar(person) + '<strong>' + esc(person.anonymous ? 'Anonim' : person.name) + '</strong>';
    const personBox = invitationBox.querySelector('.invitation-person');
    if (personBox.innerHTML !== markup) personBox.innerHTML = markup;
    const incoming = invitation.direction === 'incoming';
    accept.hidden = reject.hidden = !incoming;
    cancel.hidden = incoming;
    const message = (incoming ? 'Sizga suhbat taklifi keldi. Qabul qilasizmi?' : 'Taklif yuborildi. Suhbatdoshning roziligi kutilmoqda…') + ' (' + invitation.remaining + ' soniya)';
    if (status.textContent !== message) status.textContent = message;
  }
  function finishInvitation(message) {
    reset();
    panel.hidden = false;
    viewport.hidden = true;
    retry.disabled = false;
    status.textContent = message;
  }
  function respond(action) {
    return chatAction(async () => {
      if (!currentInvitation) return;
      const id = currentInvitation.id;
      invitationBox.querySelectorAll('button').forEach(button => button.disabled = true);
      try {
        await api('roulette/respond', {invitation_id:id, action});
        if (action === 'accept') {
          status.textContent = 'Suhbat ochilmoqda…';
        } else {
          finishInvitation(action === 'reject' ? 'Taklif rad etildi. Qayta aylantirishingiz mumkin.' : 'Taklif bekor qilindi. Qayta aylantirishingiz mumkin.');
        }
      } catch (error) {
        status.textContent = error.message;
        invitationBox.querySelectorAll('button').forEach(button => button.disabled = false);
      }
    });
  }
  accept.onclick = () => respond('accept');
  reject.onclick = () => respond('reject');
  cancel.onclick = () => respond('cancel');
  function card(person) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'roulette-card';
    button.disabled = true;
    button.innerHTML = avatar(person);
    const name = document.createElement('strong');
    name.textContent = person.anonymous ? 'Anonim' : person.name;
    button.append(name);
    return button;
  }
  async function spin() {
    if (running || currentInvitation || !document.body.classList.contains('chat-searching')) return;
    clearTimeout(timer);
    const current = ++generation;
    running = true;
    ticket = null;
    retry.disabled = true;
    panel.hidden = false;
    viewport.hidden = false;
    track.replaceChildren();
    status.textContent = 'Suhbatdoshlar qidirilmoqda…';
    try {
      const data = await api('roulette/spin', {});
      if (current !== generation) return;
      if (!data.items.length) {
        status.textContent = 'Hozircha boshqa suhbatdosh yo‘q. Kimdir kirishi bilan ruletka aylanadi.';
        timer = setTimeout(spin, 5000);
        return;
      }
      const count = data.items.length;
      const landing = Math.max(18, count * 3);
      let chosen;
      for (let i = 0; i < landing + 4; i++) {
        const person = data.items[((i - landing + data.selected) % count + count) % count];
        const button = card(person);
        track.append(button);
        if (i === landing) chosen = button;
      }
      status.textContent = 'Ruletka aylanmoqda…';
      const start = viewport.clientWidth / 2 - 66;
      const end = start - landing * 132;
      track.style.transform = `translateX(${end}px)`;
      animation = track.animate([{ transform: `translateX(${start}px)` }, { transform: `translateX(${end}px)` }], {
        duration: matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 3300,
        easing: 'cubic-bezier(.12,.72,.14,1)',
      });
      await animation.finished;
      if (current !== generation) return;
      ticket = data.ticket;
      chosen.disabled = false;
      chosen.classList.add('chosen');
      chosen.setAttribute('aria-label', `${chosen.textContent}: suhbat taklifini yuborish`);
      chosen.onclick = () => chatAction(async () => {
        if (!ticket || running) return;
        chosen.disabled = true;
        retry.disabled = true;
        try {
          const result = await api('roulette/choose', { ticket });
          showInvitation(result.invitation);
        } catch (error) {
          ticket = null;
          status.textContent = error.message;
          retry.disabled = false;
        }
      });
      status.textContent = 'Suhbat taklifini yuborish uchun tanlangan avatarni bosing.';
    } catch (error) {
      if (current === generation) status.textContent = error.message;
    } finally {
      if (current === generation) { running = false; retry.disabled = false; }
    }
  }
  retry.onclick = spin;
  window.chatRoulette = { reset, start(invitation) {
    if (invitation) return showInvitation(invitation);
    if (currentInvitation) return finishInvitation('Taklif rad etildi, bekor qilindi yoki muddati tugadi. Qayta aylantiring.');
    if (panel.hidden) spin();
  } };
})();
