(() => {
'use strict';
const en = (document.documentElement.lang || '').toLowerCase().startsWith('en');
const asset = (file) => (en ? '../' : '') + file;
const t = (zh, english) => (en ? english : zh);
const toolData = {
  codex: {
    name: 'Codex CLI',
    anchor: 'codex',
    info: t('查阅 Responses API 端点、模型及配置格式，注意第三方 API 与官方订阅不同。', 'Read the Responses API endpoint, model id and config format. A third-party API balance is not an official Codex subscription.'),
    caution: t('请先确认提供商支持对应模型、Responses API 和工具调用；Ofox 实际调用测试尚未完成。', 'Confirm the provider supports the model, the Responses API and tool calls. JXZNE has not finished a paid Ofox call test.')
  },
  claude: {
    name: 'Claude Code',
    anchor: 'claude-code',
    info: t('确认 Anthropic Messages 协议、API Base URL 与模型兼容，再安全设置本机环境变量。', 'Confirm Anthropic Messages compatibility, the base URL and the model id before setting local environment variables.'),
    caution: t('第三方网关需要明确支持 Messages API 和工具调用；不要在本网站输入 API Key。', 'A third-party gateway has to support the Messages API and tool calls. Do not enter an API key on this site.')
  },
  cursor: {
    name: 'Cursor',
    anchor: 'cursor',
    info: t('Cursor 的自定义 API 未必兼容全部功能。可使用 Cursor 终端中的 Codex CLI 或 Claude Code。', 'Cursor custom APIs do not cover every feature. You can use Codex CLI or Claude Code in the Cursor terminal.'),
    caution: t('不要将第三方 API 直连 Cursor 宣传成全面支持；Ofox 官方将直接接入标为不兼容。', 'Do not describe a direct Cursor connection as full support. Ofox marks direct Cursor integration as unsuitable.')
  }
};
const osNames = en
  ? {mac: 'macOS', windows: 'Windows', linux: 'Linux'}
  : {mac: 'macOS', windows: 'Windows', linux: 'Linux'};
const getSelected = (name) => document.querySelector('input[name="' + name + '"]:checked')?.value || '';
function update() {
  const tool = toolData[getSelected('dev-tool')] || toolData.codex;
  const os = osNames[getSelected('dev-os')] || 'macOS';
  const title = document.getElementById('dev-result-title');
  if (!title) return;
  title.textContent = tool.name + ' · ' + os;
  document.getElementById('dev-result-text').textContent = tool.info + t('教程中可进一步选择 ', ' The guide has steps for ') + os + t(' 对应步骤。', '.');
  document.getElementById('dev-result-caution').textContent = tool.caution;
  document.getElementById('dev-guide-link').href = 'guides.html#' + tool.anchor;
}
document.querySelectorAll('input[name="dev-tool"],input[name="dev-os"]').forEach((el) => el.addEventListener('change', update));
update();
function track(kind, detail) {
  try {
    if (typeof window.gtag === 'function') window.gtag('event', kind, {event_category: 'developer_funnel', event_label: detail});
    if (typeof window.plausible === 'function') window.plausible(kind, {props: {source: detail}});
  } catch (e) {}
}
document.querySelectorAll('a[href*="ofox.ai/x/itoken"]').forEach((el) => el.addEventListener('click', () => track('referral_click', el.getAttribute('data-cta') || 'developer_page')));
document.querySelectorAll('a[href*="guides.html"]').forEach((el) => el.addEventListener('click', () => track('guide_click', el.getAttribute('href') || 'guides')));

const models = {
  gpt54: {name: 'GPT-5.4', i: 2.5, o: 15, url: 'https://developers.openai.com/api/docs/models/gpt-5.4', ids: ['openai/gpt-5.4']},
  gpt52: {name: 'GPT-5.2', i: 1.75, o: 14, url: 'https://developers.openai.com/api/docs/models/gpt-5.2', ids: ['openai/gpt-5.2']},
  sonnet46: {name: 'Claude Sonnet 4.6', i: 3, o: 15, url: 'https://platform.claude.com/docs/en/models/sonnet-4-6/overview', ids: ['anthropic/claude-sonnet-4.6']},
  gemini25: {name: en ? 'Gemini 2.5 Flash (text)' : 'Gemini 2.5 Flash（文本）', i: 0.30, o: 2.50, url: 'https://ai.google.dev/gemini-api/docs/pricing', ids: ['google/gemini-2.5-flash']}
};
const REQUESTED = ['openai/gpt-5.4', 'openai/gpt-5.2', 'google/gemini-2.5-flash', 'google/gemini-2.5-pro', 'anthropic/claude-sonnet-4.6'];
const el = (id) => document.getElementById(id);
const fmt = (n) => new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD'}).format(n);
const val = (id) => Math.max(0, Math.min(100000, Number(el(id).value) || 0));
let catalog = null;

function calculatePrice() {
  if (!el('price-model')) return;
  const model = models[el('price-model').value] || models.gpt54;
  const official = val('price-in') * model.i + val('price-out') * model.o;
  el('price-official').textContent = fmt(official);
  el('price-model-reference').textContent = t(
    model.name + '：官方输入 $' + model.i + ' / 百万、输出 $' + model.o + ' / 百万 Token。',
    model.name + ': official input $' + model.i + ' / million tokens, output $' + model.o + ' / million tokens.'
  );
  el('price-official-source').href = model.url;
  const pI = el('price-ofox-in').value.trim();
  const pO = el('price-ofox-out').value.trim();
  const hasPrices = pI !== '' && pO !== '' && Number.isFinite(Number(pI)) && Number.isFinite(Number(pO)) && Number(pI) >= 0 && Number(pO) >= 0;
  const verdict = el('price-verdict');
  if (!hasPrices) {
    el('price-ofox-list').textContent = t('待填写', 'Not entered');
    el('price-ofox-net').textContent = t('待填写', 'Not entered');
    el('price-saving').textContent = t('无法计算', 'Cannot calculate');
    el('price-diff-label').textContent = t('与官方费用的差额', 'Difference vs official');
    verdict.className = 'price-verdict';
    verdict.replaceChildren();
    const strong = document.createElement('strong');
    strong.textContent = t('尚不能判断哪边更便宜', 'Not enough to say which is cheaper');
    const p = document.createElement('p');
    p.textContent = t('请用 Ofox 公开目录或账户报价填写该模型的输入和输出单价。未填写时本页不会假设有折扣。', 'Enter this model’s input and output rates from the Ofox public catalog or your account quote. Blank fields are not treated as a discount.');
    verdict.append(strong, p);
    return;
  }
  const list = val('price-in') * Number(pI) + val('price-out') * Number(pO);
  const net = list * (1 - Math.min(100, val('price-rebate')) / 100);
  const diff = official - net;
  el('price-ofox-list').textContent = fmt(list);
  el('price-ofox-net').textContent = fmt(net);
  verdict.className = 'price-verdict ' + (diff > 0.005 ? 'better' : diff < -0.005 ? 'worse' : 'equal');
  const label = diff > 0.005
    ? t('该情景下 Ofox 预计便宜', 'In this scenario Ofox costs less')
    : diff < -0.005
      ? t('该情景下官方 API 预计便宜', 'In this scenario the official API costs less')
      : t('该情景下费用基本相同', 'In this scenario the cost is about the same');
  el('price-diff-label').textContent = Math.abs(diff) <= 0.005
    ? t('与官方费用的差额', 'Difference vs official')
    : diff > 0 ? t('Ofox 相比官方节约', 'Ofox vs official, lower by') : t('Ofox 相比官方多花', 'Ofox vs official, higher by');
  el('price-saving').textContent = fmt(Math.abs(diff));
  verdict.replaceChildren();
  const strong = document.createElement('strong');
  strong.textContent = label;
  const p = document.createElement('p');
  p.textContent = t(
    '预计差额 ' + fmt(Math.abs(diff)) + ' / 月。只根据已填报价计算，不代表折扣已获批准。',
    'Estimated difference ' + fmt(Math.abs(diff)) + ' / month. Calculated only from the rates entered, not an approved discount.'
  );
  verdict.append(strong, p);
}

function ratesFor(key) {
  if (!catalog) return null;
  const ids = (models[key] || {}).ids || [];
  for (const id of ids) {
    if (catalog.byId[id]) return catalog.byId[id];
  }
  return null;
}

function applyRatesToInputs() {
  if (!el('price-model') || !catalog) return;
  const row = ratesFor(el('price-model').value);
  if (!row) {
    el('price-ofox-in').value = '';
    el('price-ofox-out').value = '';
  } else {
    el('price-ofox-in').value = String(row.promptPerMillion);
    el('price-ofox-out').value = String(row.completionPerMillion);
  }
  calculatePrice();
}

function moneyRate(n) {
  if (!Number.isFinite(n)) return '—';
  return '$' + n;
}

function renderTable() {
  const host = el('ofox-catalog');
  if (!host || !catalog) return;
  host.hidden = false;
  host.replaceChildren();
  const table = document.createElement('table');
  table.className = 'matrix-table';
  const caption = document.createElement('caption');
  caption.textContent = catalog.mode === 'live'
    ? t('刚刚从 Ofox 公开目录读到的单价（美元 / 百万 Token）', 'Rates just read from the Ofox public catalog (USD per million tokens)')
    : t('上次成功记录的公开目录单价（美元 / 百万 Token）', 'Last recorded public-catalog rates (USD per million tokens)');
  const thead = document.createElement('thead');
  const hr = document.createElement('tr');
  [t('模型', 'Model'), t('输入', 'Input'), t('输出', 'Output'), t('来源', 'Source')].forEach((label) => {
    const th = document.createElement('th');
    th.textContent = label;
    hr.append(th);
  });
  thead.append(hr);
  const tbody = document.createElement('tbody');
  REQUESTED.forEach((id) => {
    const tr = document.createElement('tr');
    const row = catalog.byId[id];
    const cells = row
      ? [id, moneyRate(row.promptPerMillion), moneyRate(row.completionPerMillion), catalog.mode === 'live' ? t('本次读取', 'This fetch') : catalog.fetchedAt]
      : [id, '—', '—', t('这次目录里没有可用文本单价', 'No usable text rate in this catalog response')];
    cells.forEach((value) => {
      const td = document.createElement('td');
      td.textContent = value;
      tr.append(td);
    });
    tbody.append(tr);
  });
  table.append(caption, thead, tbody);
  host.append(table);
}

function setStatus(text) {
  const status = el('live-price-status');
  if (status) status.textContent = text;
}

function showFallback(message) {
  const box = el('ofox-price-fallback');
  if (!box) return;
  box.hidden = false;
  const lead = box.querySelector('[data-fallback-lead]');
  if (lead && message) lead.textContent = message;
}

function hideFallback() {
  const box = el('ofox-price-fallback');
  if (box) box.hidden = true;
}

function usableRate(prompt, completion) {
  const pi = Number(prompt);
  const po = Number(completion);
  if (!Number.isFinite(pi) || !Number.isFinite(po) || pi < 0 || po < 0) return null;
  if (pi === 0 && po === 0) return null;
  return {promptPerMillion: Number((pi * 1000000).toFixed(6)), completionPerMillion: Number((po * 1000000).toFixed(6))};
}

function catalogFromLive(data) {
  const byId = {};
  (data.data || []).forEach((model) => {
    const pricing = model && model.pricing;
    if (!model || !model.id || !pricing) return;
    const rate = usableRate(pricing.prompt, pricing.completion);
    if (!rate) return;
    byId[model.id] = Object.assign({id: model.id}, rate);
  });
  return {mode: 'live', fetchedAt: new Date().toISOString(), source: 'https://api.ofox.ai/v1/models', byId};
}

function catalogFromSnapshot(data) {
  if (!data || !Array.isArray(data.models) || typeof data.fetchedAt !== 'string' || data.source !== 'https://api.ofox.ai/v1/models') {
    throw new Error('bad snapshot');
  }
  const byId = {};
  data.models.forEach((model) => {
    if (!model || typeof model.id !== 'string') return;
    const pi = Number(model.promptPerMillion);
    const po = Number(model.completionPerMillion);
    if (!Number.isFinite(pi) || !Number.isFinite(po) || pi < 0 || po < 0) return;
    if (pi === 0 && po === 0) return;
    byId[model.id] = {id: model.id, promptPerMillion: pi, completionPerMillion: po};
  });
  if (!Object.keys(byId).length) throw new Error('empty snapshot');
  return {mode: 'snapshot', fetchedAt: data.fetchedAt, source: data.source, byId};
}

async function loadOfoxPrices() {
  const button = el('load-ofox-prices');
  if (button) button.disabled = true;
  setStatus(t('正在读取 Ofox 公开模型目录…', 'Reading the Ofox public model catalog…'));
  try {
    const response = await fetch('https://api.ofox.ai/v1/models', {cache: 'no-store'});
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const data = await response.json();
    if (!Array.isArray(data.data)) throw new Error('invalid catalog');
    catalog = catalogFromLive(data);
    hideFallback();
    renderTable();
    applyRatesToInputs();
    const current = ratesFor(el('price-model').value);
    setStatus(current
      ? t('已从公开目录填入 ' + current.id + '：输入 $' + current.promptPerMillion + ' / 百万，输出 $' + current.completionPerMillion + ' / 百万。这不是最终账单。', 'Filled ' + current.id + ' from the public catalog: input $' + current.promptPerMillion + ' / million, output $' + current.completionPerMillion + ' / million. This is not a final invoice.')
      : t('公开目录已读取，但当前所选模型没有可用的文本单价，所以输入框保持空白。', 'The public catalog loaded, but the selected model has no usable text rate, so the inputs stay blank.'));
  } catch (err) {
    try {
      const response = await fetch(asset('ofox-public-prices.json'), {cache: 'no-store'});
      if (!response.ok) throw new Error('no snapshot');
      catalog = catalogFromSnapshot(await response.json());
      showFallback(t(
        '浏览器没能直接读取 Ofox 目录（常见原因是跨域限制）。下表是本仓库记录的上一次成功公开目录观察，时间 ' + catalog.fetchedAt + '。请在付款前打开 Ofox 复核，不要把观察值当成保证。',
        'This browser could not read the Ofox catalog directly (often a cross-origin limit). The table is the last successful public-catalog observation stored in this repo, at ' + catalog.fetchedAt + '. Confirm on Ofox before you pay. An observation is not a guarantee.'
      ));
      renderTable();
      applyRatesToInputs();
      setStatus(t(
        '正在使用 ' + catalog.fetchedAt + ' 的公开目录记录，不是刚刚的实时报价。',
        'Using the public-catalog record from ' + catalog.fetchedAt + ', not a live quote from this page load.'
      ));
    } catch (snapshotError) {
      catalog = null;
      if (el('ofox-catalog')) el('ofox-catalog').hidden = true;
      showFallback(t(
        '没能读取 Ofox 公开目录，也没有可用的已记录观察。输入框保持空白，本页不会编造价格。',
        'The Ofox public catalog could not be read, and there is no recorded observation to show. Inputs stay blank. This page will not invent prices.'
      ));
      setStatus(t(
        '读取失败。请用下面的链接在 Ofox 核对单价后再手工填写。',
        'The fetch failed. Use the links below to check Ofox, then type the rates yourself.'
      ));
    }
  } finally {
    if (button) button.disabled = false;
  }
}

if (el('price-model')) {
  ['price-model', 'price-in', 'price-out', 'price-ofox-in', 'price-ofox-out', 'price-rebate'].forEach((id) => el(id).addEventListener('input', calculatePrice));
  el('price-model').addEventListener('change', () => {
    if (catalog) applyRatesToInputs();
    else {
      el('price-ofox-in').value = '';
      el('price-ofox-out').value = '';
      calculatePrice();
    }
  });
  calculatePrice();
}
if (el('load-ofox-prices')) {
  el('load-ofox-prices').addEventListener('click', loadOfoxPrices);
  loadOfoxPrices();
}

function calcMigration() {
  const cur = el('mig-current');
  const next = el('mig-new');
  const once = el('mig-once');
  if (!cur || !next) return;
  const h = el('mig-headline');
  const p = el('mig-summary');
  const d = el('mig-delta');
  const pay = el('mig-payback');
  if (next.value.trim() === '' || Number(next.value) < 0 || !Number.isFinite(Number(next.value))) {
    h.textContent = t('等待 Ofox 实际报价', 'Waiting for a real Ofox quote');
    p.textContent = t('请输入相同模型和使用量下的真实 Ofox 月成本。', 'Enter the real monthly Ofox cost for the same models and usage.');
    d.textContent = '—';
    pay.textContent = '—';
    return;
  }
  const current = Math.max(0, Number(cur.value) || 0);
  const future = Math.max(0, Number(next.value) || 0);
  const cost = Math.max(0, Number(once.value) || 0);
  const savings = current - future;
  d.textContent = (savings >= 0 ? t('节省 ', 'Lower by ') : t('增加 ', 'Higher by ')) + fmt(Math.abs(savings));
  if (savings > 0) {
    h.textContent = t('有潜在节省，但应先实测', 'Possible savings — still test first');
    p.textContent = t('预计每月节省 ' + fmt(savings) + '；建议小额试用并验证常用功能。', 'About ' + fmt(savings) + ' less per month. Try a small top-up and test the features you actually use.');
    pay.textContent = cost === 0 ? t('立即（仅计算）', 'Immediate (math only)') : (cost / savings).toFixed(1) + t(' 个月', ' months');
  } else {
    h.textContent = savings === 0 ? t('费用基本相同', 'Cost is about the same') : t('Ofox 在此情景下更贵', 'Ofox costs more in this scenario');
    p.textContent = t('单从费用看，暂无迁移收益。请评估统一接入和实际可靠性。', 'On price alone there is no saving. Weigh one-account convenience against reliability.');
    pay.textContent = t('无法回本', 'No payback');
  }
}
if (el('mig-current')) ['mig-current', 'mig-new', 'mig-once'].forEach((id) => el(id).addEventListener('input', calcMigration));
if (el('mig-current')) calcMigration();

function applySmoke(data) {
  if (!data || !data.checks) return;
  document.querySelectorAll('[data-smoke]').forEach((card) => {
    const client = data.checks[card.dataset.smoke];
    const api = card.dataset.api ? data.checks[card.dataset.api] : null;
    const badge = card.querySelector('[data-badge]');
    const detail = card.querySelector('[data-detail]');
    if (!badge || !client) return;
    const apiPassed = api && api.status === 'passed' && typeof api.passedAt === 'string' && api.passedAt;
    if (client.status === 'passed' && client.passedAt) {
      badge.className = 'verify-pass';
      badge.textContent = t('已通过', 'Passed');
      if (detail) detail.textContent = t('测试记录时间 ' + client.passedAt + '。', 'Recorded at ' + client.passedAt + '.');
      return;
    }
    if (apiPassed && client.status !== 'passed') {
      badge.className = 'verify-pending';
      badge.textContent = t('接口已通，客户端未验证', 'API passed, client unverified');
      if (detail) {
        const which = card.dataset.smoke === 'codex_cli' ? 'Codex CLI' : 'Claude Code';
        detail.textContent = t(
          'Ofox 对应 API 冒烟于 ' + api.passedAt + ' 通过。' + which + ' 不在 tests/ofox_smoke.py 的覆盖范围内，客户端仍未验证。',
          which + ' is outside tests/ofox_smoke.py, so the client stays unverified. The related API smoke passed at ' + api.passedAt + '.'
        );
      }
      return;
    }
    if (client.status === 'provider_marked_incompatible') {
      badge.className = 'verify-warning';
      badge.textContent = t('服务商标记不兼容', 'Provider marks this incompatible');
    }
  });
}

fetch(asset('ofox-smoke-status.json'), {cache: 'no-store'})
  .then((response) => response.ok ? response.json() : null)
  .then((data) => { if (data && data.overall !== 'unverified') applySmoke(data); })
  .catch(() => {});
})();
