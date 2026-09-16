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
    <section class="username-settings" aria-labelledby="usernameSettingsTitle"><h3 id="usernameSettingsTitle">Username</h3><div class="username-entry"><span>t.me/</span><textarea id="editUsername" rows="3" placeholder="username&#10;qo‘shimcha_username" autocomplete="off" autocapitalize="none" spellcheck="false" aria-describedby="usernameHint"></textarea></div><small class="username-help">Username orqali odamlar sizni topishi va bog‘lanishi mumkin.</small><div id="usernameList" class="username-list"></div><button id="addUsername" type="button" class="secondary">+ Username qo‘shish</button><small id="usernameHint">Oddiy profil: 1 ta, Silver: 2 ta, Gold: 3 ta username.</small></section>
    <label for="editBio">Bio</label><textarea id="editBio" maxlength="300" rows="4" placeholder="O‘zingiz haqingizda qisqacha…" aria-describedby="bioCount"></textarea><small id="bioCount">0 / 300</small>
    <p id="profileEditError" role="alert" hidden></p>
    <div class="row"><button type="button" id="cancelProfileEdit" class="secondary">Bekor qilish</button><button id="saveProfileEdit" type="submit">Saqlash</button></div>
  </form>`;
  document.body.append(dialog);
  const usernameDialog=document.createElement('dialog');usernameDialog.id='usernameDetail';usernameDialog.innerHTML='<form method="dialog" id="usernameDetailForm"><button type="button" id="usernameBack" class="username-back">‹</button><h2>Username</h2><div class="username-detail-card"><b>Username qo‘yish</b><div class="username-detail-input"><span>t.me/</span><input id="usernameDetailInput" autocomplete="off" autocapitalize="none" spellcheck="false"></div></div><p class="username-detail-help">Bu username orqali odamlar sizni topishi va siz bilan bog‘lanishi mumkin.</p><div class="row"><button type="button" id="usernameCancel" class="secondary">Bekor qilish</button><button type="button" id="usernameApply">Tayyor</button></div></form>';
  document.body.append(usernameDialog);
  const style = document.createElement('style');
  style.textContent = '#profile{position:relative}#profile #editProfile{display:grid;place-items:center;position:absolute;top:0;right:3px;width:40px;height:40px;margin:0;padding:0;border:1px solid #718897;border-radius:50%;background:#3a4b57;color:#fff;font-size:0;line-height:1;box-shadow:0 3px 10px #0004}#profile #editProfile::after{content:"⋮";font-family:Arial,sans-serif;font-size:25px;line-height:1;transform:translateY(-1px)}#profileEditor{width:min(94vw,440px);max-height:88dvh;overflow:auto;padding:24px;border:1px solid var(--border);border-radius:24px;background:var(--surface);color:var(--text);box-shadow:0 24px 70px #0004}#profileEditor::backdrop{background:#0008;backdrop-filter:blur(5px)}#profileEditor h2{margin:0 0 20px;font-size:22px;text-align:center}#editAvatarPreview .avatar{width:88px;height:88px;border-radius:50%;margin:0 auto 16px}#profileEditor input,#profileEditor select{width:100%;min-width:0;background:var(--surface-2);color:var(--text);border-color:var(--border)}#profileEditor input:focus-visible,#profileEditor select:focus-visible,#profileEditor button:focus-visible{outline:2px solid #718897;outline-offset:2px}#profileEditError{color:#b34255;font-size:14px}#profileEditor .row{margin-top:18px}';
  document.head.append(style);
  const bioStyle = document.createElement('style');
  bioStyle.textContent = '#profileEditor textarea{display:block;width:100%;font:inherit;color:var(--text);background:var(--surface-2);border:1px solid var(--border);border-radius:14px;padding:14px;margin:6px 0;resize:vertical;min-height:100px}#profileEditor textarea:focus-visible{outline:2px solid #718897;outline-offset:2px}.username-settings{margin:14px 0;padding:16px;border:1px solid var(--border);border-radius:18px;background:var(--surface-2)}.username-settings h3,.username-settings h4{margin:0 0 10px;color:var(--accent);font-size:16px}.username-settings h4{margin-top:16px;font-size:14px}.username-entry{display:flex;align-items:flex-start;gap:4px;padding:10px 12px;border-radius:14px;background:var(--surface);border:1px solid var(--border);color:var(--muted);font-size:16px}.username-entry textarea{flex:1;border:0;background:transparent;padding:0;margin:0;min-height:72px;resize:none}.username-help,.username-settings #usernameHint{display:block;margin-top:8px;color:var(--muted);font-size:12px;line-height:1.4}.username-list{display:grid;gap:6px}.username-list-row{display:flex;align-items:center;gap:10px;padding:9px;border-top:1px solid var(--border);color:var(--text)}.username-link-icon{display:grid;place-items:center;width:30px;height:30px;border-radius:50%;background:var(--accent);color:#fff}.username-list-row span:nth-child(2){min-width:0;flex:1}.username-list-row small{display:block;color:var(--muted);margin-top:2px}.username-drag{color:var(--muted);font-size:20px}#profileInfo .profile-username{color:#2a8ab8;margin:8px 0;font-size:15px;overflow-wrap:anywhere}#profileInfo .profile-bio{white-space:pre-wrap;overflow-wrap:anywhere;color:var(--muted);font-size:14px;line-height:1.6;margin:12px auto;max-width:360px}';
  document.head.append(bioStyle);
  const usernameStyle=document.createElement('style');usernameStyle.textContent='.username-entry{display:none!important}.username-settings #addUsername{display:none!important}.username-link-icon{font-family:Arial,sans-serif;font-size:16px!important;font-weight:700;line-height:1}.username-list-row{display:flex;align-items:center;gap:10px;width:100%;padding:10px 16px;text-align:left;border:1px solid #aab9c4;border-radius:999px;color:var(--text)!important;background:linear-gradient(145deg,#ffffff,#dfe7ec)!important;box-shadow:inset 0 2px 1px #fff,0 6px 14px #71808b66,0 2px 3px #71808b44;transition:transform .15s,box-shadow .15s}.username-list-row span:nth-child(2){min-width:0;flex:1}.username-list-row:hover{background:linear-gradient(145deg,#fff,#d6e0e7)!important;transform:translateY(-1px);box-shadow:inset 0 2px 1px #fff,0 8px 16px #71808b77}.username-list-row:active{transform:translateY(1px);box-shadow:inset 0 2px 4px #71808b55,0 2px 5px #71808b44}#usernameDetail{width:min(94vw,440px);padding:20px;border:1px solid var(--border);border-radius:24px;background:var(--surface);color:var(--text)}#usernameDetail::backdrop{background:#0008}.username-back{width:42px!important;padding:5px!important;background:transparent!important;color:var(--text)!important;font-size:28px!important}.username-detail-card{margin-top:12px;padding:16px;border-radius:18px;background:var(--surface-2)}.username-detail-card>b{display:block;color:var(--accent);margin-bottom:12px}.username-detail-input{display:flex;align-items:center;gap:4px;padding:12px;border-radius:14px;background:var(--surface);border:1px solid var(--border);color:var(--muted)}.username-detail-input input{margin:0!important;padding:0!important;border:0!important;background:transparent!important;color:var(--text)!important}.username-detail-help{color:var(--muted);line-height:1.5}body.theme-dark .username-list-row{border-color:#536678;background:linear-gradient(145deg,#3f5361,#293943)!important;box-shadow:inset 0 2px 1px #ffffff22,0 6px 14px #0008,0 2px 3px #0006}.username-list-row:hover{filter:brightness(1.08)}';document.head.append(usernameStyle);
  const updateBioCount = () => { $('bioCount').textContent = `${$('editBio').value.length} / 300`; };
  const updateUsernameList = () => { const list=$('usernameList'); if(!list)return; const items=$('editUsername').value.split(/\s+/).map(x=>x.replace(/^@/,'')).filter(Boolean); const x=items[0]; list.innerHTML=x?`<button type="button" class="username-list-row" data-username="${x}"><span class="username-link-icon">@</span><span><b>@${x}</b></span><span class="username-drag">☷</span></button>`:''; };
  $('editBio').addEventListener('input', updateBioCount);
  $('editUsername').addEventListener('input', updateUsernameList);
  // Username controls are launchers, rather than inline editors. Open a
  // completely empty, separate window and make a best effort to maximize it.
  const openBlankUsernameWindow = () => {
    const win=window.open('about:blank','_blank','popup=yes,fullscreen=yes');
    if(!win){
      let blank=document.getElementById('blankUsernameWindow');
      if(!blank){
        blank=document.createElement('dialog'); blank.id='blankUsernameWindow';
        blank.innerHTML='<button type="button" class="blank-window-close" aria-label="Yopish">×</button>';
        document.body.append(blank);
        blank.firstElementChild.onclick=()=>blank.close();
        const s=document.createElement('style');
        s.textContent='#blankUsernameWindow{width:100vw;height:100vh;max-width:none;max-height:none;border:0;padding:0;background:#fff}#blankUsernameWindow::backdrop{background:#fff}#blankUsernameWindow .blank-window-close{position:fixed;top:14px;left:14px;width:42px;height:42px;padding:0;border:1px solid #9aa8b5;border-radius:12px;background:linear-gradient(145deg,#ffffff,#d7e0e7);color:#344454;font:700 25px/1 Arial;box-shadow:inset 0 2px 1px #fff,0 5px 0 #9aa8b5,0 8px 14px #65758566;cursor:pointer}#blankUsernameWindow .blank-window-close:hover{filter:brightness(1.04);transform:translateY(-1px)}#blankUsernameWindow .blank-window-close:active{transform:translateY(3px);box-shadow:inset 0 2px 3px #b5c0c8,0 2px 0 #9aa8b5,0 4px 8px #65758555}';
        document.head.append(s);
      }
      blank.showModal();
      return;
    }
    try{
      win.document.title='';
      win.document.body.replaceChildren();
      win.document.documentElement.style.cssText='width:100%;height:100%;margin:0;background:#fff;';
      win.document.body.style.cssText='width:100%;height:100%;margin:0;background:#fff;';
      win.focus();
      const request=win.document.documentElement.requestFullscreen;
      if(request)Promise.resolve(request.call(win.document.documentElement)).catch(()=>{});
    }catch{}
  };
  $('usernameList').addEventListener('click',e=>{
    if(e.target.closest('.username-list-row'))openBlankUsernameWindow();
  });
  // Other profile views render the handle directly instead of using the
  // editor's username row. Give those handles the same behavior.
  document.addEventListener('click',e=>{
    if(e.target.closest('.username-list-row'))return;
    if(e.target.closest('.partner-handle,.profile-primary-username,.profile-extra-usernames span:not(.profile-usernames-label)'))openBlankUsernameWindow();
  });
  const closeUsername=()=>usernameDialog.close();$('usernameBack').onclick=closeUsername;$('usernameCancel').onclick=closeUsername;$('usernameApply').onclick=()=>{const value=$('usernameDetailInput').value.trim().replace(/^@/,'');if(!value)return;const rows=$('editUsername').value.split(/\s+/).filter(Boolean);const index=rows.findIndex(x=>x.replace(/^@/,'')===$('usernameDetailInput').dataset.original);if(index>=0)rows[index]='@'+value;else rows.push('@'+value);$('editUsername').value=rows.join('\n');updateUsernameList();closeUsername()};
  let draftAvatar = null, preparing = false, saving = false, revision = 0;
  const error = message => { $('profileEditError').textContent = message; $('profileEditError').hidden = !message; };
  entry.onclick = async () => {
    if (profileRefresh) { try { await profileRefresh; } catch {} }
    if (!me || $('profile').hidden) return;
    revision++;
    draftAvatar = null;
    preparing = false;
    $('editName').value = me.name || '';
    $('editUsername').value = (me.usernames || (me.app_username ? [me.app_username] : [])).map(x => '@'+x).join('\n');
    updateUsernameList();
    $('editBio').value = me.bio || '';
    updateBioCount();
    $('editAvatar').value = '';
    $('editAvatarPreview').innerHTML = avatar(me);
    $('saveProfileEdit').disabled = false;
    error('');
    dialog.showModal();
  };
  $('cancelProfileEdit').onclick = () => { if (!saving) dialog.close(); };
  $('addUsername').onclick = () => { const field=$('editUsername'); const limit=me?.verified?999:Number(me?.gold)>0?3:me?.silver?2:1; const count=field.value.split(/\s+/).filter(Boolean).length; if(count>=limit){error('Siz ko‘pi bilan '+limit+' ta username qo‘ya olasiz.');return} field.value=field.value.trim()+(field.value.trim()?'\n':'')+'@'; field.focus(); };
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
    const usernames = $('editUsername').value.split(/\s+/).map(x=>x.trim().replace(/^@/,'').toLowerCase()).filter(Boolean);
    const data = {name:$('editName').value.trim(), app_username:usernames[0]||'', usernames, bio:$('editBio').value.trim()};
    if (draftAvatar) data.avatar = draftAvatar;
    if (data.name.length < 2) return error('Ism kamida 2 ta belgidan iborat bo‘lsin.');
    const minimumUsernameLength = me?.verified ? 1 : Number(me?.short_username_min_length) || (Number(me?.gold) > 0 ? 3 : me?.silver ? 2 : 1);
    const usernameLimit = me?.verified ? 999 : Number(me?.gold) > 0 ? 3 : me?.silver ? 2 : 1;
    if (usernames.length > usernameLimit) return error('Siz ko‘pi bilan '+usernameLimit+' ta username qo‘ya olasiz.');
    if (usernames.some(x=>x.length < minimumUsernameLength || !/^[a-z][a-z0-9_]{0,23}$/.test(x))) return error('Username '+minimumUsernameLength+'–24 ta lotin harfi, raqam yoki _ dan iborat bo‘lsin.');
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
