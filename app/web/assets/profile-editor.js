(() => {
  const entry = document.createElement('button');
  entry.id = 'editProfile';
  entry.type = 'button';
  entry.textContent = 'Profilni tahrirlash';
  $('profileInfo').after(entry);
  const dialog = document.createElement('dialog');
  dialog.id = 'profileEditor';
  dialog.setAttribute('aria-labelledby', 'profileEditorTitle');
  dialog.innerHTML = `<form id="profileEditForm">
    <h2 id="profileEditorTitle">Profilni tahrirlash</h2>
    <div id="editAvatarPreview" class="center"></div>
    <button id="pickEditAvatar" class="secondary" type="button">Profil rasmini almashtirish</button>
    <input id="editAvatar" type="file" accept="image/jpeg,image/png,image/webp" hidden>
    <small>Rasmning markaziy qismi olinadi. 10 MB gacha.</small>
    <label for="editName">Ismingiz / nik</label><input id="editName" required minlength="2" maxlength="64" autocomplete="nickname">
    <label for="editUsername">Ichki username</label><input id="editUsername" maxlength="25" placeholder="@username" autocomplete="off" autocapitalize="none" spellcheck="false" aria-describedby="usernameHint">
    <small id="usernameHint">Ilova ichidagi username. Oddiy profil: kamida 6, Gold/verifikatsiya: kamida 5 belgi.</small>
    <label for="editBio">Bio</label><textarea id="editBio" maxlength="300" rows="4" placeholder="O‘zingiz haqingizda qisqacha…" aria-describedby="bioCount"></textarea><small id="bioCount">0 / 300</small>
    <p id="profileEditError" role="alert" hidden></p>
    <div class="row"><button type="button" id="cancelProfileEdit" class="secondary">Bekor qilish</button><button id="saveProfileEdit" type="submit">Saqlash</button></div>
  </form>`;
  document.body.append(dialog);
  const style = document.createElement('style');
  style.textContent = '#profile #editProfile{display:block;max-width:300px;margin:16px auto 24px;border:1px solid #72589b;background:linear-gradient(145deg,#35294c,#201b30);color:#e7d8ff}#profileEditor{width:min(94vw,440px);max-height:88dvh;overflow:auto;padding:24px;border:1px solid #544066;border-radius:24px;background:#121421;color:#f3f5ff;box-shadow:0 24px 70px #0009}#profileEditor::backdrop{background:#050711bb;backdrop-filter:blur(5px)}#profileEditor h2{margin:0 0 20px;font-size:22px;text-align:center}#editAvatarPreview .avatar{width:88px;height:88px;border-radius:50%;margin:0 auto 16px}#profileEditor input,#profileEditor select{width:100%;min-width:0}#profileEditor input:focus-visible,#profileEditor select:focus-visible,#profileEditor button:focus-visible{outline:2px solid #bda0ff;outline-offset:2px}#profileEditError{color:#ffacbb;font-size:14px}#profileEditor .row{margin-top:18px}';
  document.head.append(style);
  const bioStyle = document.createElement('style');
  bioStyle.textContent = '#profileEditor textarea{display:block;width:100%;font:inherit;color:inherit;background:#101626;border:1px solid #35405c;border-radius:14px;padding:14px;margin:6px 0;resize:vertical;min-height:100px}#profileEditor textarea:focus-visible{outline:2px solid #bda0ff;outline-offset:2px}#profileInfo .profile-username{color:#c6acff;margin:8px 0;font-size:15px;overflow-wrap:anywhere}#profileInfo .profile-bio{white-space:pre-wrap;overflow-wrap:anywhere;color:#c9cfe0;font-size:14px;line-height:1.6;margin:12px auto;max-width:360px}';
  document.head.append(bioStyle);
  const updateBioCount = () => { $('bioCount').textContent = `${$('editBio').value.length} / 300`; };
  $('editBio').addEventListener('input', updateBioCount);
  let draftAvatar = null, preparing = false, saving = false, revision = 0;
  const error = message => { $('profileEditError').textContent = message; $('profileEditError').hidden = !message; };
  entry.onclick = async () => {
    if (profileRefresh) { try { await profileRefresh; } catch {} }
    if (!me || $('profile').hidden) return;
    revision++;
    draftAvatar = null;
    preparing = false;
    $('editName').value = me.name || '';
    $('editUsername').value = me.app_username || '';
    $('editBio').value = me.bio || '';
    updateBioCount();
    $('editAvatar').value = '';
    $('editAvatarPreview').innerHTML = avatar(me);
    $('saveProfileEdit').disabled = false;
    error('');
    dialog.showModal();
  };
  $('cancelProfileEdit').onclick = () => { if (!saving) dialog.close(); };
  $('pickEditAvatar').onclick = () => $('editAvatar').click();
  $('profileEditForm').addEventListener('input', () => error(''));
  dialog.addEventListener('cancel', event => { if (saving) event.preventDefault(); });
  dialog.addEventListener('close', () => { revision++; draftAvatar = null; });
  $('editAvatar').onchange = async () => {
    const current = ++revision, file = $('editAvatar').files[0];
    draftAvatar = null;
    preparing = false;
    $('saveProfileEdit').disabled = false;
    error('');
    $('editAvatarPreview').innerHTML = avatar(me);
    if (!file) return;
    preparing = true;
    $('saveProfileEdit').disabled = true;
    try {
      if (file.size > 10000000) throw Error('10 MB dan kichik rasm tanlang.');
      const bitmap = await createImageBitmap(file);
      try {
        const side = Math.min(bitmap.width, bitmap.height);
        const canvas = document.createElement('canvas');
        canvas.width = canvas.height = 512;
        canvas.getContext('2d').drawImage(bitmap, (bitmap.width-side)/2, (bitmap.height-side)/2, side, side, 0, 0, 512, 512);
        if (current !== revision) return;
        draftAvatar = canvas.toDataURL('image/jpeg', .9);
        $('editAvatarPreview').innerHTML = avatar({name:me.name, avatar:draftAvatar});
      } finally { bitmap.close(); }
    } catch (e) {
      if (current === revision) { error(e.message || 'Rasm ochilmadi.'); $('editAvatar').value = ''; }
    } finally {
      if (current === revision) { preparing = false; $('saveProfileEdit').disabled = false; }
    }
  };
  $('profileEditForm').onsubmit = async event => {
    event.preventDefault();
    if (saving || preparing) return;
    const data = {name:$('editName').value.trim(), app_username:$('editUsername').value.trim().replace(/^@/, '').toLowerCase(), bio:$('editBio').value.trim()};
    if (draftAvatar) data.avatar = draftAvatar;
    if (data.name.length < 2) return error('Ism kamida 2 ta belgidan iborat bo‘lsin.');
    const minimumUsernameLength = me?.short_username_access ? 1 : ((Number(me?.gold) > 0 || me?.silver || me?.verified) ? 5 : 6);
    if (data.app_username && (data.app_username.length < minimumUsernameLength || !/^[a-z][a-z0-9_]{0,23}$/.test(data.app_username))) return error('Username '+minimumUsernameLength+'–24 ta lotin harfi, raqam yoki _ dan iborat bo‘lsin va harf bilan boshlansin.');
    saving = true;
    error('');
    const controls = [...$('profileEditForm').elements];
    controls.forEach(control => control.disabled = true);
    $('saveProfileEdit').textContent = 'Saqlanmoqda…';
    try {
      const fresh = await api('profile', data);
      ++avatarCacheEpoch;
      me = {...me, ...fresh};
      await avatarCacheStore('delete', me.id);
      renderProfile();
      dialog.close();
      notice('Profil yangilandi.');
    } catch (e) { error(e.message); }
    finally {
      saving = false;
      controls.forEach(control => control.disabled = false);
      $('saveProfileEdit').textContent = 'Saqlash';
    }
  };
})();
