(function(){
  function init(){
    const body=document.body;
    const saved=localStorage.getItem('pvp-theme');
    const telegramTheme=window.Telegram?.WebApp?.colorScheme;
    const initial=saved||(telegramTheme==='dark'?'dark':'light');
    body.classList.toggle('theme-dark',initial==='dark');
    const target=()=>document.querySelector('#profileEditor form')||document.querySelector('header');
    if(!target())return;
    const button=document.createElement('button');
    button.className='theme-toggle'; button.type='button'; button.setAttribute('role','switch');
    const label=document.createElement('span'); label.className='theme-toggle-label';
    const track=document.createElement('span'); track.className='theme-toggle-track';
    const knob=document.createElement('span'); knob.className='theme-toggle-knob';
    track.append(knob); button.append(label,track);
    const sync=dark=>{
      body.classList.toggle('theme-dark',dark);
      localStorage.setItem('pvp-theme',dark?'dark':'light');
      label.textContent=dark?'Dark mode':'Light mode';
      button.setAttribute('aria-checked',dark?'true':'false');
      button.setAttribute('aria-label',dark?'Dark mode yoqilgan':'Light mode yoqilgan');
    };
    button.onclick=()=>sync(!body.classList.contains('theme-dark'));
    sync(initial==='dark');
    const mount=()=>{const host=target();if(host&&button.parentElement!==host)host.append(button)};
    mount();if(!button.parentElement)setTimeout(mount,0);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
