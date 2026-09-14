/* Manual avatar crop: the canvas and exported image use the same coordinates. */
(() => {
const style = document.createElement('style');
style.textContent = '#cropModal{position:fixed;inset:0;z-index:100;background:#08080b;display:flex;flex-direction:column;justify-content:center;padding:20px;gap:20px;overflow:auto}#cropStage{position:relative;width:min(100%,380px);aspect-ratio:1;margin:auto;touch-action:none;overflow:hidden}#cropCanvas{width:100%;height:100%;display:block}#cropMask{position:absolute;inset:0;border-radius:50%;box-shadow:0 0 0 200px #0009;pointer-events:none}#cropModal .crop-controls{width:min(100%,380px);margin:0 auto}#cropModal button{background:#248ddd}#cropModal .secondary{background:#22232b}#cropModal p{text-align:center;color:#ccc}';
document.head.append(style);
let confirmed = null, selected = null, generation = 0;
const input = $('photo');
input.accept = 'image/*,.heic,.heif,.avif,.bmp,.tif,.tiff';
photo = async () => {
  if (!confirmed || selected !== input.files[0]) throw Error('Rasmni crop oynasida tasdiqlang.');
  return confirmed;
};
input.addEventListener('change', async () => {
  const token = ++generation, file = input.files[0];
  confirmed = null; selected = null;
  document.querySelector('#cropModal')?.remove();
  if (!file) return;
  const modal = document.createElement('div');
  modal.id = 'cropModal'; modal.setAttribute('role','dialog'); modal.setAttribute('aria-modal','true');
  modal.innerHTML = '<p id="cropHelp">Rasm yuklanmoqda…</p><div id="cropStage"><canvas id="cropCanvas" width="512" height="512"></canvas><div id="cropMask"></div></div><div class="crop-controls"><button id="cropConfirm" type="button" disabled>Tasdiqlash ✓</button><button id="cropCancel" type="button" class="secondary">Bekor qilish</button></div>';
  document.body.append(modal);
  const canvas = modal.querySelector('canvas'), ctx = canvas.getContext('2d'), stage = modal.querySelector('#cropStage'), confirm = modal.querySelector('#cropConfirm');
  const cancel = () => { ++generation; input.value=''; confirmed=null; selected=null; $('pickPhoto').textContent='Rasm tanlash'; modal.remove(); };
  modal.querySelector('#cropCancel').onclick=cancel;
  let bitmap;
  try {
    if(file.size>20*1024*1024) throw Error('20 MB dan kichik rasm tanlang.');
    const body=new FormData(); body.append('image',file);
    const result=await api('photo/prepare',body);
    bitmap=new Image(); bitmap.src=result.image; await bitmap.decode();
    if(token!==generation) return;
  } catch(error) { if(token===generation){cancel();notice(error.message)} return; }
  let base=Math.max(512/bitmap.width,512/bitmap.height), scale=base, x=(512-bitmap.width*base)/2, y=(512-bitmap.height*base)/2;
  function draw(){x=Math.min(0,Math.max(512-bitmap.width*scale,x));y=Math.min(0,Math.max(512-bitmap.height*scale,y));ctx.clearRect(0,0,512,512);ctx.drawImage(bitmap,x,y,bitmap.width*scale,bitmap.height*scale)}
  function resize(next,cx=256,cy=256){next=Math.max(base,Math.min(base*5,next));const ratio=next/scale;x=cx-(cx-x)*ratio;y=cy-(cy-y)*ratio;scale=next;draw()}

  const pointers=new Map();
  const point=e=>{const r=stage.getBoundingClientRect();return{x:(e.clientX-r.left)*512/r.width,y:(e.clientY-r.top)*512/r.height}};
  stage.onpointerdown=e=>{stage.setPointerCapture(e.pointerId);pointers.set(e.pointerId,point(e));};
  stage.onpointermove=e=>{
    if(!pointers.has(e.pointerId))return;
    const before=[...pointers.values()], old=pointers.get(e.pointerId), now=point(e);
    pointers.set(e.pointerId,now);
    if(pointers.size===1){x+=now.x-old.x;y+=now.y-old.y;draw()}
    else{const after=[...pointers.values()], distance=p=>Math.hypot(p[0].x-p[1].x,p[0].y-p[1].y);const d=distance(before);if(d>0)resize(scale*distance(after)/d,(after[0].x+after[1].x)/2,(after[0].y+after[1].y)/2)}
  };
  stage.onpointerup=stage.onpointercancel=e=>pointers.delete(e.pointerId);
  stage.addEventListener('wheel',e=>{e.preventDefault();resize(scale*Math.exp(-e.deltaY*.001))},{passive:false});
  modal.querySelector('#cropHelp').textContent='Rasmni suring. Ikki barmoq bilan kattalashtiring.';
  draw();confirm.disabled=false;
  confirm.onclick=()=>{const output=document.createElement('canvas');output.width=output.height=Math.max(1,Math.round(512/scale));output.getContext('2d').drawImage(bitmap,-x/scale,-y/scale,512/scale,512/scale,0,0,output.width,output.height);confirmed=output.toDataURL('image/png');selected=file;$('pickPhoto').textContent='Rasm tasdiqlandi';$('photoRequiredMessage').hidden=true;modal.remove();};
});
})();
