(()=>{
  const input = document.getElementById('pricing-search');
  if (!input) return;
  const cards = [...document.querySelectorAll('.pricing-directory-card')];
  const summary = document.getElementById('pricing-search-summary');
  const en = (document.documentElement.lang || '').toLowerCase().startsWith('en');
  input.addEventListener('input', () => {
    let n = 0;
    const q = input.value.trim().toLocaleLowerCase();
    for (const card of cards) {
      const show = (card.dataset.name || '').includes(q);
      card.hidden = !show;
      if (show) n++;
    }
    if (summary) {
      summary.textContent = en
        ? 'Showing ' + n + ' / ' + cards.length + ' products'
        : '显示 ' + n + ' / ' + cards.length + ' 款产品';
    }
  });
})();
