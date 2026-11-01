(() => {
  'use strict';
  const slot = document.getElementById('detail-country-prices');
  if (!slot) return;
  const id = slot.dataset.model;
  const money = (n) => new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD'}).format(n);
  const countryName = {
    AR: 'Argentina', AU: 'Australia', BR: 'Brazil', CA: 'Canada', CH: 'Switzerland', CN: 'China',
    DE: 'Germany', DK: 'Denmark', EG: 'Egypt', FR: 'France', GB: 'United Kingdom', ID: 'Indonesia',
    IN: 'India', JP: 'Japan', KR: 'South Korea', MX: 'Mexico', NG: 'Nigeria', PH: 'Philippines',
    PK: 'Pakistan', TR: 'Turkey', US: 'United States'
  };
  fetch('../../pricing-snapshots.json', {cache: 'no-store'}).then((r) => {
    if (!r.ok) throw Error('HTTP ' + r.status);
    return r.json();
  }).then((data) => {
    const latest = new Map();
    for (const orig of data.rows || []) {
      if (orig.id !== id || !Number.isFinite(orig.usd)) continue;
      const x = {...orig};
      x.plan = ({plus: 'Plus', pro: 'Pro', supergrok: 'SuperGrok', 'google-ai-pro': 'Google AI Pro'}[String(x.plan).toLowerCase()] || x.plan);
      x.channel = ({app_store: 'App Store', google_play: 'Google Play'}[String(x.channel).toLowerCase()] || x.channel);
      x.countryEn = countryName[x.code] || x.country;
      const key = [x.plan, x.code, x.channel].join('|');
      const prev = latest.get(key);
      if (!prev || x.date > prev.date) latest.set(key, x);
    }
    const rows = [...latest.values()].sort((a, b) => a.countryEn.localeCompare(b.countryEn) || String(a.plan).localeCompare(String(b.plan)) || String(a.channel).localeCompare(String(b.channel)));
    const title = document.createElement('p');
    title.className = 'grok-muted';
    slot.append(title);
    if (!rows.length) {
      title.textContent = 'No sourced cross-country sample is on file. Use the provider checkout. This is not a hidden price.';
      return;
    }
    const plans = [...new Set(rows.map((x) => x.plan))].sort();
    const countries = new Set(rows.map((x) => x.code)).size;
    title.textContent = rows.length + ' historical rows · ' + plans.length + ' plan names · ' + countries + ' countries or regions. Sorted by country name, not a cheapest-country ranking. Past subscription amounts, not a live quote.';
    const label = document.createElement('label');
    label.className = 'pricing-plan-select';
    label.textContent = 'Filter plan ';
    const select = document.createElement('select');
    select.add(new Option('All plans', ''));
    for (const p of plans) select.add(new Option(p, p));
    label.append(select);
    slot.append(label);
    const wrap = document.createElement('div');
    wrap.className = 'matrix-scroll';
    const table = document.createElement('table');
    table.className = 'matrix-table';
    const thead = document.createElement('thead');
    const tr = document.createElement('tr');
    for (const x of ['Country / region', 'Plan', 'Channel', 'USD / month', 'Local amount', 'Observed', 'Source']) {
      const th = document.createElement('th');
      th.textContent = x;
      tr.append(th);
    }
    thead.append(tr);
    table.append(thead);
    const tbody = document.createElement('tbody');
    table.append(tbody);
    wrap.append(table);
    slot.append(wrap);
    function render() {
      tbody.replaceChildren();
      for (const row of rows.filter((x) => !select.value || x.plan === select.value)) {
        const rowEl = document.createElement('tr');
        for (const t of [row.countryEn, row.plan, row.channel, money(row.usd), row.localAmount && row.currency ? row.localAmount + ' ' + row.currency : '—', row.date]) {
          const td = document.createElement('td');
          td.textContent = t;
          rowEl.append(td);
        }
        const td = document.createElement('td');
        const link = document.createElement('a');
        link.href = row.source;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = 'Source ↗';
        td.append(link);
        rowEl.append(td);
        tbody.append(rowEl);
      }
    }
    select.addEventListener('change', render);
    render();
  }).catch(() => {
    const p = document.createElement('p');
    p.textContent = 'The price file did not load. Open the Chinese price matrix and try again.';
    slot.append(p);
  });
})();
