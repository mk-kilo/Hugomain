(()=>{
'use strict';
const models=[['chatgpt','ChatGPT'],['claude','Claude'],['gemini','Gemini'],['grok','Grok'],['perplexity','Perplexity'],['kimi','Kimi'],['glm','GLM'],['microsoft-copilot','Microsoft Copilot'],['deepseek','DeepSeek'],['qwen','Qwen']];
const en=(document.documentElement.lang||'').toLowerCase().startsWith('en');
const countryEn={AR:'Argentina',AU:'Australia',BR:'Brazil',CA:'Canada',CH:'Switzerland',CN:'China',DE:'Germany',DK:'Denmark',EG:'Egypt',FR:'France',GB:'United Kingdom',ID:'Indonesia',IN:'India',JP:'Japan',KR:'South Korea',MX:'Mexico',NG:'Nigeria',PH:'Philippines',PK:'Pakistan',TR:'Turkey',US:'United States'};
const $=id=>document.getElementById(id),product=$('matrix-product'),country=$('matrix-country'),plan=$('matrix-plan'),channel=$('matrix-channel'),body=$('matrix-body'),status=$('matrix-status');
const fmt=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n);
const countryLabel=x=>en?(countryEn[x.code]||x.country):x.country;
const channelLabel=c=>{
  const key=String(c).toLowerCase();
  if(key==='app_store')return 'App Store';
  if(key==='google_play')return 'Google Play';
  if(key==='official_website')return en?'Official site':'官网';
  return c;
};
const copy=en?{
  source:'Source ↗',
  empty:'No verified price for this product, plan, or country. Open the product page for the official link.',
  shown:n=>'Showing '+n+' sourced historical rows. Compare a price only when the plan and the channel match.',
  cov:(countries,plans,count)=>countries+' countries/regions · '+plans+' '+(plans===1?'plan':'plans')+' · '+count+' rows',
  none:'No verified price yet',
  fail:'Could not load the price file. The rows in the HTML are the last published sample.',
  fresh:d=>'Last successful automatic collection: '+d+' UTC. Each row keeps its own observation date.',
  freshNone:'No verified automatic collection yet. The table is the last reviewed historical sample.'
}:{
  source:'来源 ↗',
  empty:'该产品／套餐／地区暂无经核验的价格；可以点击下方对应产品查看官方定价。',
  shown:n=>'已展示 '+n+' 条带来源的历史记录 · 套餐和渠道必须相同才能比较',
  cov:(countries,plans,count)=>countries+' 国/地区 · '+plans+' 套餐 · '+count+' 条记录',
  none:'暂无可核验价格',
  fail:'数据读取失败。表格里仍是页面上预置的最近一次样本。',
  fresh:d=>'上次自动采集成功：'+d+' UTC。每条记录的观测日期见表格。',
  freshNone:'尚无已验证的自动采集结果；表中为原先整理的历史样本。'
};
for(const [id,name] of models){product.add(new Option(name,id))}
let rows=[];const params=new URLSearchParams(location.search);product.value=params.get('model')||'';
const allowed=new Set(models.map(x=>x[0]));
function filterRows(){return rows.filter(x=>allowed.has(x.id)&&(!product.value||x.id===product.value)&&(!plan.value||x.plan===plan.value)&&(!country.value||x.code===country.value)&&(!channel.value||x.channel===channel.value))}
function setOptions(select,options){const current=select.value;select.length=1;for(const [value,label] of options){select.add(new Option(label,value))}select.value=[...select.options].some(x=>x.value===current)?current:''}
function rebuild(){const subset=rows.filter(x=>allowed.has(x.id)&&(!product.value||x.id===product.value));setOptions(plan,[...new Set(subset.map(x=>x.plan))].sort().map(x=>[x,x]));const chosenPlan=subset.filter(x=>!plan.value||x.plan===plan.value);setOptions(country,[...new Map(chosenPlan.map(x=>[x.code,countryLabel(x)])).entries()].sort((a,b)=>a[1].localeCompare(b[1],en?'en':'zh')));setOptions(channel,[...new Set(chosenPlan.map(x=>x.channel))].sort().map(x=>[x,x]));render()}
function render(){const selected=filterRows().sort((a,b)=>a.usd-b.usd);body.replaceChildren();for(const x of selected){const tr=document.createElement('tr');for(const value of [x.product,x.plan,countryLabel(x),x.channel,fmt(x.usd),x.localAmount&&x.currency?x.localAmount+' '+x.currency:'—',x.date]){const td=document.createElement('td');td.textContent=value;tr.append(td)}const td=document.createElement('td'),a=document.createElement('a');a.href=x.source;a.target='_blank';a.rel='noopener noreferrer';a.textContent=copy.source;td.append(a);tr.append(td);body.append(tr)}
if(!selected.length){const tr=document.createElement('tr'),td=document.createElement('td');td.colSpan=8;td.textContent=copy.empty;tr.append(td);body.append(tr)}
$('matrix-count').textContent=String(selected.length);$('matrix-low').textContent=selected.length?fmt(selected[0].usd):'—';$('matrix-high').textContent=selected.length?fmt(selected[selected.length-1].usd):'—';status.textContent=copy.shown(selected.length);
const coverage=$('matrix-coverage');if(coverage){coverage.replaceChildren();for(const [id,name] of models){const mine=rows.filter(x=>x.id===id);const count=mine.length;const plans=new Set(mine.map(x=>x.plan)).size;const countries=new Set(mine.map(x=>x.code)).size;const a=document.createElement('a');a.href='ai-pricing/'+id+'.html';a.className='matrix-coverage-card';const title=document.createElement('strong');title.textContent=name;const small=document.createElement('small');small.textContent=count?copy.cov(countries,plans,count):copy.none;a.append(title,small);coverage.append(a)}}}
product.addEventListener('change',()=>{plan.value='';country.value='';channel.value='';const url=new URL(location.href);if(product.value)url.searchParams.set('model',product.value);else url.searchParams.delete('model');history.replaceState(null,'',url);rebuild()});
plan.addEventListener('change',()=>{country.value='';channel.value='';rebuild()});country.addEventListener('change',render);channel.addEventListener('change',render);
const dataUrl=new URL(en?'../pricing-snapshots.json':'pricing-snapshots.json',location.href);
fetch(dataUrl,{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json()}).then(data=>{const latest=new Map();for(const original of (data.rows||[])){if(!original||!Number.isFinite(original.usd)||!original.source||!original.date)continue;const x={...original};x.plan=({plus:'Plus',pro:'Pro',supergrok:'SuperGrok','google-ai-pro':'Google AI Pro'}[String(x.plan).toLowerCase()]||x.plan);x.channel=channelLabel(x.channel);const key=[x.id,x.plan,x.code,x.channel].join('|');const prior=latest.get(key);if(!prior||x.date>prior.date)latest.set(key,x)}rows=[...latest.values()];const f=$('matrix-freshness');if(f)f.textContent=data.lastSuccessfulFetch?copy.fresh(data.lastSuccessfulFetch):copy.freshNone;rebuild()}).catch(()=>{status.textContent=copy.fail});
})();
