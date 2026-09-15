(function(){
  function init(){
    const body=document.body;
    const saved=localStorage.getItem('pvp-theme');
    const telegramTheme=window.Telegram?.WebApp?.colorScheme;
    const initial=saved||(telegramTheme==='dark'?'dark':'light');
    body.classList.toggle('theme-dark',initial==='dark');
    const header=document.querySelector('header'); if(!header)return;
    const button=document.createElement('button');
    button.className='theme-toggle'; button.type='button'; button.title='Mavzuni almashtirish';
    const sync=()=>{const dark=body.classList.toggle('theme-dark');localStorage.setItem('pvp-theme',dark?'dark':'light');button.textContent=dark?'☀':'☾';button.setAttribute('aria-label',dark?'Yorug‘ rejimga o‘tish':'Qorong‘u rejimga o‘tish')};
    button.onclick=sync; button.textContent=initial==='dark'?'☀':'☾'; header.append(button);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
