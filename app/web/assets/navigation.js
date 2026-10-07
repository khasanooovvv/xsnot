(() => {
 const nav=document.getElementById('nav');if(!nav)return;
 const pages=['dating','home','instagram','leaders'],labels=['Tanishuv','Ruletka','Chat','Leaderboard'];
 const icons=["<svg class=\"dating-brand\" viewBox=\"64 64 384 384\" aria-hidden=\"true\"><g class=\"brand-art\"><path class=\"brand-outline\" pathLength=\"1\" d=\"M256 96 C350 96 416 156 416 244 C416 333 349 394 258 394 C222 394 190 387 166 372 L98 399 L122 329 C104 304 96 276 96 244 C96 157 161 96 256 96 Z\"/><path class=\"brand-heart\" d=\"M256 316 C242 304 186 265 181 233 C174 190 226 176 256 210 C286 176 338 190 331 233 C326 265 270 304 256 316 Z\"/></g></svg>","<svg class=\"roulette-brand\" viewBox=\"0 0 32 32\" aria-hidden=\"true\"><g class=\"roulette-pair\"><g class=\"roulette-bubble\"><path fill=\"currentColor\" stroke=\"none\" d=\"M10 2C15.5 2 20 5.6 20 10S15.5 18 10 18c-1.2 0-2.3-.2-3.3-.5L3 20l.9-4.2C1.5 14.3 0 12.3 0 10c0-4.4 4.5-8 10-8Z\"/></g><g class=\"roulette-bubble\"><path fill=\"currentColor\" stroke=\"#101010\" stroke-width=\"1.6\" d=\"M22 12c5.5 0 10 3.6 10 8s-4.5 8-10 8c-1.2 0-2.3-.2-3.3-.5L15 30l.9-4.2C13.5 24.3 12 22.3 12 20c0-4.4 4.5-8 10-8Z\"/></g></g><path class=\"roulette-spark\" d=\"m16 11 1.3 3.7L21 16l-3.7 1.3L16 21l-1.3-3.7L11 16l3.7-1.3Z\" fill=\"currentColor\" stroke=\"#101010\" stroke-width=\".8\"/></svg>","<svg class=\"dm-brand\" viewBox=\"0 0 32 32\" aria-hidden=\"true\"><g class=\"dm-plane\"><path fill=\"currentColor\" stroke=\"none\" d=\"M27.6 4.4c1.5-.6 2.4.3 2.1 1.8l-4.5 21.2c-.3 1.5-1.2 1.9-2.5 1l-9-6.6c-1.2-.9-1.4-1.5-.4-2.4l10.2-9.3c.6-.6.2-1-.5-.5L10.4 18c-.8.5-1.5.6-2.4.3l-5.8-1.8c-1.5-.5-1.5-1.5.1-2.1L27.6 4.4Z\"/></g><g class=\"dm-wind\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.3\" stroke-linecap=\"round\"><path class=\"wind-one\" d=\"M9 7h13\"/><path class=\"wind-two\" d=\"M6 15h20\"/><path class=\"wind-three\" d=\"M12 23h11\"/></g></svg>","<svg class=\"stats-brand\" viewBox=\"0 0 32 32\" aria-hidden=\"true\"><rect class=\"stats-bar bar-one\" x=\"3\" y=\"17\" width=\"6\" height=\"11\" rx=\"2\" fill=\"currentColor\" stroke=\"none\"/><rect class=\"stats-bar bar-two\" x=\"13\" y=\"10\" width=\"6\" height=\"18\" rx=\"2\" fill=\"currentColor\" stroke=\"none\"/><rect class=\"stats-bar bar-three\" x=\"23\" y=\"3\" width=\"6\" height=\"25\" rx=\"2\" fill=\"currentColor\" stroke=\"none\"/></svg>","<svg viewBox=\"0 0 28 28\" aria-hidden=\"true\"><circle cx=\"14\" cy=\"9\" r=\"4\"/><path d=\"M5 24v-2a9 9 0 0 1 18 0v2\"/><path d=\"M9 23h10\" opacity=\".4\"/></svg>"];
 const buttons=pages.map(p=>nav.querySelector('[data-page="'+p+'"]')),profile=nav.querySelector('[data-page="profile"]');
 if(buttons.some(b=>!b)||!profile)return;
 nav.classList.add('major-nav');[...buttons,profile].forEach(b=>b.classList.add('major-nav-control'));const capsule=document.createElement('div');capsule.className='major-capsule';
 const active=document.createElement('div');active.className='major-active';active.setAttribute('aria-hidden','true');capsule.append(active);nav.prepend(capsule);
 buttons.forEach((b,i)=>{b.innerHTML=icons[i]+'<span>'+labels[i]+'</span>';b.setAttribute('aria-label',labels[i]);b.title=labels[i];capsule.append(b);});nav.append(profile);profile.classList.add('major-profile');profile.title='Profil';profile.setAttribute('aria-label','Profil');
 let photoSource=null;
 function syncPhoto(){
  const source=me?.avatar||null;if(source===photoSource&&profile.firstChild)return;photoSource=source;profile.innerHTML=icons[4];
  if(!source)return;
  const image=document.createElement('img');image.className='nav-own-photo';image.alt='Profil rasmi';image.hidden=true;
  image.onload=()=>{if(image.parentNode!==profile)return;profile.querySelector('svg').setAttribute('hidden','');image.hidden=false;};
  image.onerror=()=>{image.remove();const fallback=profile.querySelector('svg');if(fallback)fallback.removeAttribute('hidden');};
  profile.append(image);image.src=source;
 }
 function syncSelection(){
  const index=buttons.findIndex(b=>b.classList.contains('selected'));nav.classList.toggle('profile-selected',profile.classList.contains('selected'));
  if(index>=0)active.style.transform='translateX('+(index*100)+'%)';
  [...buttons,profile].forEach(b=>{if(b.classList.contains('selected'))b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
 }
 function tapFeedback(){
  const app=globalThis.Telegram?.WebApp;
  try{
   if(typeof app?.HapticFeedback?.selectionChanged==='function'&&(!app.isVersionAtLeast||app.isVersionAtLeast('6.1'))){
    app.HapticFeedback.selectionChanged();return;
   }
  }catch(_){/* Optional haptics must not interrupt navigation. */}
 }
 // Capture the tap before page handlers render or replace navigation content.
 [...buttons,profile].forEach(b=>b.addEventListener('click',tapFeedback,true));
 [...buttons,profile].forEach(b=>b.addEventListener('click',()=>{
  if(b!==profile){buttons.forEach(x=>x.classList.remove('turn'));void b.offsetWidth;b.classList.add('turn');}
  syncSelection();
 }));
 const observer=new MutationObserver(syncSelection);[...buttons,profile].forEach(b=>observer.observe(b,{attributes:true,attributeFilter:['class']}));
 syncDirectIcon=()=>{};syncRouletteIcon=()=>{};syncLeaderboardIcon=()=>{};syncProfileIcon=syncPhoto;
 const originalRender=renderProfile;renderProfile=function(...args){const result=originalRender.apply(this,args);syncPhoto();return result;};
 syncPhoto();syncSelection();
})();
