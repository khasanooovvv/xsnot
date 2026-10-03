(function(){
  function init(){
    const body=document.body;
    body.classList.add('theme-dark');
    const telegram=window.Telegram?.WebApp;
    for(const [method,color] of [['setHeaderColor','#101010'],['setBackgroundColor','#101010'],['setBottomBarColor','#171717']]){
      try{telegram?.[method]?.(color)}catch{}
    }
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
