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
  let closeActive = null;
  pick.onclick = async () => {
    closeActive?.();
    const overlay = document.createElement('div');
    overlay.id='photoPicker';
    overlay.innerHTML=`<section class="sheet" role="dialog" aria-modal="true" aria-labelledby="photoPickerTitle"><div class="handle"></div><div class="sheet-head"><h2 id="photoPickerTitle">Rasm tanlash</h2><button type="button" class="close" aria-label="Yopish">×</button></div><video autoplay muted playsinline aria-label="Old kamera"></video><p role="status">Kamera ochilmoqda…</p><button type="button" class="capture" disabled>Suratga olish</button><button type="button" class="gallery">Galereyadan tanlash</button></section>`;
    document.body.append(overlay);
    const video=overlay.querySelector('video'), status=overlay.querySelector('[role=status]'), capture=overlay.querySelector('.capture');
    const previousOverflow=document.body.style.overflow;
    document.body.style.overflow='hidden';
    let stream=null, closed=false;
    function close(){
      if(closed)return;
      closed=true; stream?.getTracks().forEach(track=>track.stop()); video.srcObject=null;
      overlay.remove();document.body.style.overflow=previousOverflow;
      document.removeEventListener('keydown',keys);closeActive=null;pick.focus();
    }
    function keys(event){
      if(event.key==='Escape')close();
      if(event.key==='Tab'){
        const items=[...overlay.querySelectorAll('button:not(:disabled)')];
        if(event.shiftKey&&document.activeElement===items[0]){event.preventDefault();items.at(-1).focus()}
        else if(!event.shiftKey&&document.activeElement===items.at(-1)){event.preventDefault();items[0].focus()}
      }
    }
    closeActive=close;
    document.addEventListener('keydown',keys);
    overlay.querySelector('.close').onclick=close;
    overlay.onclick=event=>{if(event.target===overlay)close()};
    overlay.querySelector('.gallery').onclick=()=>{close();input.click()};
    overlay.querySelector('.close').focus();
    capture.onclick=()=>{
      if(!video.videoWidth||!video.videoHeight)return;
      capture.disabled=true;
      const canvas=document.createElement('canvas');
      const scale=Math.min(1,2048/Math.max(video.videoWidth,video.videoHeight));
      canvas.width=Math.round(video.videoWidth*scale);canvas.height=Math.round(video.videoHeight*scale);
      const context=canvas.getContext('2d');
      context.translate(canvas.width,0);context.scale(-1,1);context.drawImage(video,0,0,canvas.width,canvas.height);
      canvas.toBlob(blob=>{
        if(closed)return;
        if(!blob){status.textContent='Surat olinmadi. Qayta urinib ko‘ring.';capture.disabled=false;return}
        try{
          const transfer=new DataTransfer();transfer.items.add(new File([blob],'camera.jpg',{type:'image/jpeg'}));input.files=transfer.files;
          close();input.dispatchEvent(new Event('change',{bubbles:true}));
        }catch{status.textContent='Suratni uzatib bo‘lmadi. Galereyadan tanlang.';capture.disabled=false}
      },'image/jpeg',.92);
    };
    try{
      if(!navigator.mediaDevices?.getUserMedia)throw Error('unsupported');
      stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user',width:{ideal:1280},height:{ideal:1280}},audio:false});
      if(closed){stream.getTracks().forEach(track=>track.stop());return}
      video.srcObject=stream;await video.play();
      if(closed)return;
      capture.disabled=false;status.textContent='Suratga oling yoki galereyadan rasm tanlang.';
    }catch(error){
      stream?.getTracks().forEach(track=>track.stop());
      if(!closed){video.hidden=true;status.textContent=error.name==='NotAllowedError'?'Kameraga ruxsat berilmadi. Galereyadan rasm tanlashingiz mumkin.':'Kamera ochilmadi. Galereyadan rasm tanlang.'}
    }
  };
  window.addEventListener('pagehide',()=>closeActive?.());
  document.addEventListener('visibilitychange',()=>{if(document.hidden)closeActive?.()});
})();
