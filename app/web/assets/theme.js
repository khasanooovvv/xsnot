(function(){
  const root=document.documentElement, body=document.body;
  const saved=localStorage.getItem('pvp-theme');
  const initial=saved||((window.Telegram&&Telegram.WebApp&&Telegram.WebApp.colorScheme)||'light');
  body.classList.toggle('theme-dark',initial==='dark');
  const header=document.querySelector('header'); if(!header)return;
  const button=document.createElement('button'); button.className='theme-toggle'; button.type='button';
  const sync=()=>{const dark=body.classList.toggle('theme-dark');localStorage.setItem('pvp-theme',dark?'dark':'light');button.textContent=dark?'☀':'☾';button.setAttribute('aria-label',dark?'Yorug‘ rejim':'Qorong‘u rejim')};
  button.onclick=sync; button.textContent=initial==='dark'?'☀':'☾'; header.append(button);
})();
