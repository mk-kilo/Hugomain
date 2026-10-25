(()=>{'use strict';
const toolData={codex:{name:'Codex CLI',anchor:'codex',info:'查阅 Responses API 端点、模型及配置格式，注意第三方 API 与官方订阅不同。',caution:'请先确认提供商支持对应模型、Responses API 和工具调用；Ofox 实际调用测试尚未完成。'},claude:{name:'Claude Code',anchor:'claude-code',info:'确认 Anthropic Messages 协议、API Base URL 与模型兼容，再安全设置本机环境变量。',caution:'第三方网关需要明确支持 Messages API 和工具调用；不要在本网站输入 API Key。'},cursor:{name:'Cursor',anchor:'cursor',info:'Cursor 的自定义 API 未必兼容全部功能。可使用 Cursor 终端中的 Codex CLI 或 Claude Code。',caution:'不要将第三方 API 直连 Cursor 宣传成全面支持；请先阅读限制。'}};
const osNames={mac:'macOS',windows:'Windows',linux:'Linux'};
const getSelected=name=>document.querySelector('input[name="'+name+'"]:checked')?.value||'';
function update(){const t=toolData[getSelected('dev-tool')]||toolData.codex;const os=osNames[getSelected('dev-os')]||'macOS';document.getElementById('dev-result-title').textContent=t.name+' · '+os;document.getElementById('dev-result-text').textContent=t.info+'教程中可进一步选择 '+os+' 对应步骤。';document.getElementById('dev-result-caution').textContent=t.caution;document.getElementById('dev-guide-link').href='guides.html#'+t.anchor;}
document.querySelectorAll('input[name="dev-tool"],input[name="dev-os"]').forEach(el=>el.addEventListener('change',update));update();
function track(kind,detail){try{if(typeof window.gtag==='function')window.gtag('event',kind,{event_category:'developer_funnel',event_label:detail});if(typeof window.plausible==='function')window.plausible(kind,{props:{source:detail}})}catch(e){}}
document.querySelectorAll('a[href*="ofox.ai/x/itoken"]').forEach(el=>el.addEventListener('click',()=>track('referral_click',el.getAttribute('data-cta')||'developer_page')));
document.querySelectorAll('a[href*="guides.html"]').forEach(el=>el.addEventListener('click',()=>track('guide_click',el.getAttribute('href')||'guides')));

const models={
 gpt54:{name:'GPT-5.4',i:2.5,o:15,url:'https://developers.openai.com/api/docs/models/gpt-5.4'},
 gpt52:{name:'GPT-5.2',i:1.75,o:14,url:'https://developers.openai.com/api/docs/models/gpt-5.2'},
 sonnet46:{name:'Claude Sonnet 4.6',i:3,o:15,url:'https://platform.claude.com/docs/en/models/sonnet-4-6/overview'},
 gemini25:{name:'Gemini 2.5 Flash（文本）',i:.30,o:2.50,url:'https://ai.google.dev/gemini-api/docs/pricing'}};
const el=id=>document.getElementById(id),fmt=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n);
const val=id=>Math.max(0,Math.min(100000,Number(el(id).value)||0));
function calculatePrice(){
 const m=models[el('price-model').value]||models.gpt54;
 const official=val('price-in')*m.i+val('price-out')*m.o;
 el('price-official').textContent=fmt(official);
 el('price-model-reference').textContent=m.name+'：官方输入 $'+m.i+' / 百万、输出 $'+m.o+' / 百万 Token。';
 el('price-official-source').href=m.url;
 const pI=el('price-ofox-in').value.trim(),pO=el('price-ofox-out').value.trim();
 const hasPrices=pI!==''&&pO!==''&&Number.isFinite(Number(pI))&&Number.isFinite(Number(pO))&&Number(pI)>=0&&Number(pO)>=0;
 const verdict=el('price-verdict');
 if(!hasPrices){
 el('price-ofox-list').textContent='待填写';el('price-ofox-net').textContent='待填写';
 el('price-saving').textContent='无法计算';el('price-diff-label').textContent='与官方费用的差额';
 verdict.className='price-verdict';verdict.innerHTML='<strong>尚不能判断哪边更便宜</strong><p>请从 Ofox 报价页核实该模型输入和输出单价，再填入左侧。</p>';return;}
 const list=val('price-in')*Number(pI)+val('price-out')*Number(pO);
 const net=list*(1-Math.min(100,val('price-rebate'))/100);
 const diff=official-net;el('price-ofox-list').textContent=fmt(list);el('price-ofox-net').textContent=fmt(net);
 verdict.className='price-verdict '+(diff>0.005?'better':diff<-.005?'worse':'equal');
 let label=diff>.005?'该情景下 Ofox 预计便宜':diff<-.005?'该情景下官方 API 预计便宜':'该情景下费用基本相同';
 el('price-diff-label').textContent=diff>=0?'Ofox 相比官方节约':'Ofox 相比官方多花';
 el('price-saving').textContent=fmt(Math.abs(diff));
 verdict.replaceChildren();const strong=document.createElement('strong');strong.textContent=label;const p=document.createElement('p');p.textContent='预计差额 '+fmt(Math.abs(diff))+' / 月。仅根据输入的报价计算，不代表实际优惠已获批准。';verdict.append(strong,p);
}
if(el('price-model')){['price-model','price-in','price-out','price-ofox-in','price-ofox-out','price-rebate'].forEach(id=>el(id).addEventListener('input',calculatePrice));el('price-model').addEventListener('change',()=>{el('price-ofox-in').value='';el('price-ofox-out').value='';calculatePrice();});calculatePrice();}

function calcMigration(){
 const cur=el('mig-current'),next=el('mig-new'),once=el('mig-once');if(!cur||!next)return;
 const h=el('mig-headline'),p=el('mig-summary'),d=el('mig-delta'),pay=el('mig-payback');
 if(next.value.trim()===''||Number(next.value)<0||!Number.isFinite(Number(next.value))){
 h.textContent='等待 Ofox 实际报价';p.textContent='请输入相同模型和使用量下的真实 Ofox 月成本。';d.textContent='—';pay.textContent='—';return;}
 const current=Math.max(0,Number(cur.value)||0),future=Math.max(0,Number(next.value)||0),cost=Math.max(0,Number(once.value)||0),savings=current-future;
 d.textContent=(savings>=0?'节省 ':'增加 ')+fmt(Math.abs(savings));
 if(savings>0){h.textContent='有潜在节省，但应先实测';p.textContent='预计每月节省 '+fmt(savings)+'；建议小额试用并验证常用功能。';pay.textContent=cost===0?'立即（仅计算）':(cost/savings).toFixed(1)+' 个月';}
 else{h.textContent=savings===0?'费用基本相同':'Ofox 在此情景下更贵';p.textContent='单从费用看，暂无迁移收益。请评估统一接入和实际可靠性。';pay.textContent='无法回本';}
}
if(el('mig-current'))['mig-current','mig-new','mig-once'].forEach(id=>el(id).addEventListener('input',calcMigration));if(el('mig-current'))calcMigration();

async function loadOfoxPrices(){
 const status=el('live-price-status'),btn=el('load-ofox-prices');btn.disabled=true;status.textContent='正在读取 Ofox 公开模型目录…';
 try{
 const response=await fetch('https://api.ofox.ai/v1/models',{cache:'no-store'});
 if(!response.ok)throw new Error('HTTP '+response.status);
 const data=await response.json();if(!Array.isArray(data.data))throw new Error('Invalid catalog');
 const wanted={gpt54:['openai/gpt-5.4'],gpt52:['openai/gpt-5.2'],sonnet46:['anthropic/claude-sonnet-4.6'],gemini25:['google/gemini-2.5-flash']};
 const key=el('price-model').value;const match=data.data.find(x=>(wanted[key]||[]).includes(x.id));
 if(!match||!match.pricing)throw new Error('Selected model has no public price');
 const pi=Number(match.pricing.prompt),po=Number(match.pricing.completion);
 if(!Number.isFinite(pi)||!Number.isFinite(po)||pi<0||po<0)throw new Error('Missing per-token rate');
 el('price-ofox-in').value=String(Number((pi*1000000).toFixed(6)));el('price-ofox-out').value=String(Number((po*1000000).toFixed(6)));
 calculatePrice();status.textContent='已获取 '+match.id+' 的公开标价。输入 +el('price-ofox-in').value+' / 百万，输出 +el('price-ofox-out').value+' / 百万；请以最终账单为准。';
 }catch(err){status.textContent='未能读取该模型公开价格（可能是浏览器跨域限制、模型缺失或接口异常）。请直接在 Ofox 核实后手动输入。';}
 finally{btn.disabled=false;}
}
if(el('load-ofox-prices'))el('load-ofox-prices').addEventListener('click',loadOfoxPrices);
})();