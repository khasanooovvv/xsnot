const assert=require('node:assert/strict');
const fs=require('node:fs');
const css=fs.readFileSync('app/web/assets/theme.css','utf8');
const rule=css.match(/#chatMenu\.chat-menu>button\{([^}]+)\}/);
assert.ok(rule,'Shared chat menu button rule is required');
for(const property of ['width:100%!important','min-width:0!important','box-sizing:border-box','height:36px','padding:8px 10px!important','transform:none!important']){
  assert.ok(rule[1].includes(property),'Missing menu layout constraint: '+property);
}
const html=fs.readFileSync('app/web/index.html','utf8');
const menu=html.match(/<div id="chatMenu"[^>]*>(.*?)<\/div>/s);
assert.ok(menu);
for(const id of ['next','stop','report'])assert.ok(menu[1].includes('id="'+id+'"'));
console.log('PASS: compact chat menu constraints and all three actions preserved');
