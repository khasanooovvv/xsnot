(function(){
  function init(){
    const body=document.body;
    body.classList.add('theme-dark');
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
