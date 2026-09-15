/* Records a fresh front-camera clip. No gallery/file input. */
function createVerificationCamera({preview, playback, onState, onError}) {
  let stream=null,recorder=null,chunks=[],blob=null,url=null,timer=null,started=0,version=0,state='idle';
  const emit=(next,seconds=0)=>{state=next;onState(next,seconds)};
  function release(){if(timer){clearInterval(timer);timer=null}if(stream){stream.getTracks().forEach(track=>track.stop());stream=null}preview.srcObject=null;}
  function clearClip(){blob=null;if(url){URL.revokeObjectURL(url);url=null}playback.removeAttribute('src');playback.load();}
  function cancel(){version++;if(recorder&&recorder.state!=='inactive'){recorder.onstop=null;recorder.ondataavailable=null;recorder.stop()}recorder=null;release();clearClip();emit('idle');}
  function fail(message){cancel();onError(message)}
  async function open(){
    cancel();const current=version;emit('opening');
    if(!navigator.mediaDevices?.getUserMedia||typeof MediaRecorder==='undefined'){fail('Kamera bu qurilmada qo‘llanmaydi. Telegramni yangilab qayta urinib ko‘ring.');return}
    try{
      const acquired=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user',width:{ideal:640},height:{ideal:480},frameRate:{ideal:24,max:30}},audio:false});
      if(current!==version){acquired.getTracks().forEach(track=>track.stop());return}
      stream=acquired;preview.srcObject=stream;await preview.play();
      if(current!==version)return;
      emit('ready');
    }catch(error){if(current!==version)return;fail(error.name==='NotAllowedError'?'Kameraga ruxsat bering va qayta urinib ko‘ring.':error.name==='NotFoundError'?'Kamera topilmadi.':'Kamera ochilmadi. Boshqa ilovada band emasligini tekshiring.');}
  }
  function stop(){if(recorder?.state==='recording')recorder.stop()}
  function record(){
    if(state!=='ready'||!stream)return;
    const mime=['video/mp4','video/webm;codecs=vp8','video/webm'].find(type=>MediaRecorder.isTypeSupported(type));
    if(!mime){fail('Kamera bu qurilmada qo‘llanmaydi. Telegramni yangilab qayta urinib ko‘ring.');return}
    const current=version;chunks=[];let size=0;
    try{
      recorder=new MediaRecorder(stream,{mimeType:mime,videoBitsPerSecond:600000});
      recorder.ondataavailable=e=>{if(current!==version||!e.data.size)return;size+=e.data.size;if(size>15*1024*1024){fail('Video hajmi oshib ketdi. Qayta yozing.');return}chunks.push(e.data)};
      recorder.onerror=()=>{if(current===version)fail('Video yozilmadi. Qayta urinib ko‘ring.')};
      recorder.onstop=()=>{
        if(current!==version)return;
        const duration=performance.now()-started;release();
        if(duration<5000||!chunks.length){fail('Kamida 5 soniya video yozing.');return}
        blob=new Blob(chunks,{type:recorder.mimeType||mime});
        url=URL.createObjectURL(blob);playback.src=url;emit('review');
      };
      recorder.start(250);started=performance.now();emit('recording',0);
      timer=setInterval(()=>{const seconds=Math.floor((performance.now()-started)/1000);emit('recording',seconds);if(seconds>=15)stop()},200);
    }catch{fail('Video yozilmadi. Qayta urinib ko‘ring.')}
  }
  return {open,record,stop,cancel,getBlob:()=>blob,getState:()=>state};
}
