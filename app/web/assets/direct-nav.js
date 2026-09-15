(function(){
  document.addEventListener('DOMContentLoaded',function(){
    const box=document.querySelector('.direct-box'),home=document.getElementById('home'),main=document.querySelector('main'),nav=document.querySelector('nav');
    if(!box||!home||!main||!nav)return;
    const page=document.createElement('section');page.id='directSearch';page.hidden=true;page.append(box);main.append(page);
    const item=document.createElement('button');item.dataset.page='directSearch';item.title='Qidirish';item.setAttribute('aria-label','Username qidirish');item.innerHTML='<span class="direct-nav-icon">⌕</span>';
    item.onclick=()=>{main.querySelectorAll(':scope>section').forEach(x=>x.hidden=x.id!=='directSearch');nav.querySelectorAll('button').forEach(x=>x.classList.toggle('selected',x===item));};
    nav.insertBefore(item,nav.firstChild);
  },{once:true});
})();
