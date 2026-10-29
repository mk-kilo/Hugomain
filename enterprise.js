(()=>{'use strict';
const $=x=>document.getElementById(x);
const number=x=>Math.max(0,Math.min(10000000,Number(x)||0));
const money=x=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2}).format(x);
function calculate(){
 const base=number($('base').value);
 const fee=Math.min(100,number($('aggregate-fee').value));
 const rebate=Math.min(100,number($('ofox-rebate').value));
 const discount=Math.min(100,number($('direct-discount').value));
 const direct=base*(1-discount/100);
 const aggregation=base*(1+fee/100);
 const ofox=base*(1-rebate/100);
 $('direct-cost').textContent=money(direct);
 $('aggregate-cost').textContent=money(aggregation);
 $('ofox-cost').textContent=money(ofox);
 const diff=ofox-direct;
 $('delta').textContent=(diff>0?'+':'')+money(diff);
 $('delta').style.color=diff<=0?'#77e1b5':'#f8b09c';
}
['base','aggregate-fee','ofox-rebate','direct-discount'].forEach(id=>$(id).addEventListener('input',calculate));
const makeBrief=()=>['企业 AI API 采购需求','月预算：'+$('brief-budget').value,'业务场景：'+$('brief-workload').value,'主要关注：'+$('brief-priority').value,'请提供具体模型分项价格、API 兼容性、速率限制、SLA、数据处理条款、返还条件和企业付款方式。'].join('\n');
$('copy-brief').addEventListener('click',async()=>{
 const brief=makeBrief();
 try{await navigator.clipboard.writeText(brief);$('copy-status').textContent='需求说明已复制，可粘贴到企业邮件或供应商咨询。';}
 catch(e){$('copy-status').textContent='自动复制失败，请检查浏览器剪贴板权限。';}
});
$('download-brief')?.addEventListener('click',()=>{const blob=new Blob(['\ufeff'+makeBrief()],{type:'text/plain;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='JXZNE-enterprise-api-requirements.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);$('copy-status').textContent='已生成本地 TXT 需求说明；未上传任何数据。';});
function mailtoHref(){
 const subject='企业 AI API 采购咨询（来自 jxzne.com）';
 const body=['你好 JXZNE，','','我们希望咨询企业 AI API 采购（Ofox / 官方 API / 其他聚合）。','月预算：'+$('brief-budget').value,'业务场景：'+$('brief-workload').value,'主要关注：'+$('brief-priority').value,'','请协助核对分项报价、协议兼容（OpenAI / Anthropic / Gemini）、SLA、数据处理与发票。','此邮件由 jxzne.com/enterprise.html 生成，没有经过站内表单。'].join('\n');
 return 'mailto:hello@jxzne.com?subject='+encodeURIComponent(subject)+'&body='+encodeURIComponent(body);
}
function refreshMailto(){const link=$('mailto-brief'); if(link) link.href=mailtoHref();}
['brief-budget','brief-workload','brief-priority'].forEach(id=>{const node=$(id); if(node) node.addEventListener('change',refreshMailto);});
refreshMailto();
calculate();
})();