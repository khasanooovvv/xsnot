/* Open the system photo picker directly, then use the existing crop flow. */
(() => {
  const pick = document.getElementById('pickPhoto');
  const input = document.getElementById('photo');
  if (!pick || !input) return;
  input.removeAttribute('capture');
  pick.onclick = () => input.click();
  const style = document.createElement('style');
  style.textContent = '#registration #pickPhoto{background:#248ddd;color:#fff;border:1px solid #248ddd}#registration #pickPhoto:focus-visible{outline:2px solid #fff;outline-offset:3px}';
  document.head.append(style);
})();
