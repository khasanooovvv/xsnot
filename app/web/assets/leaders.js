function renderLeaders(rows){
  rows=rows.slice(0,150);
  const name=(r)=>'<span class="leader-name-text">'+esc(r.name)+'</span>'+badgeMarkup(r);
  const person=(r,index,kind)=>'<article class="leader-person '+kind+'"><div class="leader-photo">'+avatar(r)+'<span class="leader-place">'+(index+1)+'</span></div><strong class="leader-name">'+name(r)+'</strong><span class="leader-score">'+Number(r.count).toLocaleString('en-US')+' <small>taklif</small></span></article>';
  if(!rows.length)return '<p class="center muted">Hali taklifchilar yo‘q.</p>';
  const top=rows.slice(0,3).map((r,i)=>person(r,i,'podium-'+(i+1))).join('');
  const middle=rows.slice(3,7).map((r,i)=>person(r,i+3,'')).join('');
  const bottom=rows.slice(7,150).map((r,i)=>'<article class="leader-row"><span class="leader-row-place">'+(i+8)+'</span>'+avatar(r)+'<strong>'+name(r)+'</strong><b>'+Number(r.count).toLocaleString('en-US')+'<small>taklif</small></b></article>').join('');
  return '<div class="leader-podium">'+top+'</div>'+(middle?'<div class="leader-middle">'+middle+'</div>':'')+'<p class="leader-reward-note">Top 10 ishtirokchi administrator tomonidan mukofotlanadi.</p>'+(bottom?'<div class="leader-bottom">'+bottom+'</div>':'');
}
