/* Camera/gallery bottom sheet. Both sources feed the existing crop input. */
(() => {
  const css = document.createElement('style');
  css.textContent = `
  #photoPicker{position:fixed;inset:0;z-index:90;background:#0009;display:flex;align-items:flex-end;justify-content:center}
  #photoPicker .sheet{width:min(100%,520px);max-height:90dvh;overflow:auto;background:#141418;border:1px solid #5b1f2a;border-radius:26px 26px 0 0;padding:12px 20px calc(20px + env(safe-area-inset-bottom));animation:photoSlide .22s ease-out}
  #photoPicker .handle{width:40px;height:4px;border-radius:4px;background:#626269;margin:0 auto 16px}
  #photoPicker .sheet-head{display:flex;align-items:center;justify-content:space-between;gap:12px}
  #photoPicker h2{font-size:20px;margin:0}#photoPicker .close{width:44px;background:transparent;font-size:24px}
  #photoPicker video{display:block;width:100%;height:220px;object-fit:cover;border-radius:18px;background:#08080a;transform:scaleX(-1)}
  #photoPicker p{font-size:14px;color:#bcbcc6}#photoPicker button{background:#242428;border:1px solid #69313f}
  #photoPicker .capture{background:#248ddd;border-color:#248ddd}#photoPicker button:focus-visible{outline:2px solid #fff;outline-offset:2px}
  @keyframes photoSlide{from{transform:translateY(100%)}to{transform:translateY(0)}}
  @media(prefers-reduced-motion:reduce){#photoPicker .sheet{animation:none}}`;
  document.head.append(css);
  const pick = document.getElementById('pickPhoto'), input = document.getElementById('photo');
  if (!pick || !input) return;
  const camera = document.createElement('input');
  camera.type='file';camera.accept='image/*';camera.setAttribute('capture','user');camera.hidden=true;
  document.body.append(camera);
  camera.onchange=()=>{
    if(!camera.files.length)return;
    input.files=camera.files;
    input.dispatchEvent(new Event('change',{bubbles:true}));
    camera.value='';
  };
  let closeActive=null;
  pick.onclick=()=>{
    closeActive?.();
    const overlay=document.createElement('div');overlay.id='photoPicker';
    overlay.innerHTML='<section class="sheet" role="dialog" aria-modal="true" aria-label="Rasm tanlash"><div class="handle"></div><button type="button" class="capture">📷 Suratga olish</button><button type="button" class="gallery">🖼 Galereyadan tanlash</button></section>';
    document.body.append(overlay);
    const previous=document.body.style.overflow;document.body.style.overflow='hidden';
    const close=()=>{overlay.remove();document.body.style.overflow=previous;document.removeEventListener('keydown',keys);closeActive=null;pick.focus()};
    const buttons=[...overlay.querySelectorAll('button')];
    function keys(e){
      if(e.key==='Escape')close();
      if(e.key==='Tab'){e.preventDefault();buttons[document.activeElement===buttons[0]?1:0].focus()}
    }
    closeActive=close;document.addEventListener('keydown',keys);
    overlay.onclick=e=>{if(e.target===overlay)close()};
    buttons[0].onclick=()=>{close();camera.click()};
    buttons[1].onclick=()=>{close();input.click()};
    buttons[0].focus();
  };
  window.addEventListener('pagehide',()=>closeActive?.());
})();
