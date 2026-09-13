/* Colored verification seals beside names; no public enrollment UI. */
function badgeMarkup(user) {
  if (!user || user.anonymous) return '';
  function seal(kind, label) {
    return '<svg class="name-badge badge-' + kind + '" viewBox="0 0 24 24" role="img" aria-label="' + label + '"><path fill="currentColor" d="M12 1.5 15 3l3.3.3 1.4 3 2.3 2.4-.6 3.3.6 3.3-2.3 2.4-1.4 3-3.3.3-3 1.5-3-1.5-3.3-.3-1.4-3L2 15.3l.6-3.3L2 8.7l2.3-2.4 1.4-3L9 3Z"/><path class="badge-check" d="m7.4 12.1 3 3 6.2-6.2" fill="none" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  }
  let result = Number(user.gold) > 0 ? seal('gold', 'Gold') : Number(user.silver) > 0 ? seal('silver', 'Silver') : '';
  if (user.verified === true) result += seal('blue', 'Verified');
  return result;
}
