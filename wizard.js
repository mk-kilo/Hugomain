(() => {
'use strict';
const $ = id => document.getElementById(id);
const tool = $('wizard-tool'), os = $('wizard-os'), provider = $('wizard-provider');
if (!tool || !os || !provider) return;
const docs = {
 codex:'https://developers.openai.com/docs/config-file/config-basic',
 claude:'https://docs.anthropic.com/en/docs/claude-code/llm-gateway',
 cursor:'https://docs.cursor.com/settings/api-keys'
};
function render() {
 const t=tool.value, platform=os.value, third=provider.value==='ofox';
 const file = platform==='windows' ? '%USERPROFILE%\\.codex\\config.toml' : '~/.codex/config.toml';
 let code='',detail='',title='';
 if(t==='codex') {
   title='Codex · '+(third?'Ofox 官方有接入指南，本站实测待完成':'官方配置指引');
   detail='Codex 使用模型提供商配置。仅有 Chat Completions 接口可能不够，需确认 Responses 协议支持；不同版本请以官方文档为准。';
   code=third ? '# 检查清单（不是可直接运行的配置）\n# 1. 确认 Ofox 是否提供 Codex 可用的 Responses API\n# 2. 确认模型 ID、鉴权方式和工具调用支持\n# 3. 通过小额测试再使用\n# 配置文件：'+file : '# 官方配置位置：'+file+'\n# 请根据官方文档填写模型与 provider 配置\n# 不要把 API Key 直接写进公开仓库';
 } else if(t==='claude'){
   title='Claude Code · '+(third?'Ofox 官方有接入指南，本站实测待完成':'网关配置说明');
   detail='Claude Code 的网关需要兼容 Anthropic API 格式。下面仅演示官方描述的变量形态，不保证第三方端点可用。';
   code = platform==='windows'
   ? '# PowerShell（仅在确认网关兼容后替换示例值）\n$env:ANTHROPIC_BASE_URL="https://YOUR-COMPATIBLE-GATEWAY"\n$env:ANTHROPIC_AUTH_TOKEN="YOUR_API_KEY"'
   : '# Terminal（仅在确认网关兼容后替换示例值）\nexport ANTHROPIC_BASE_URL="https://YOUR-COMPATIBLE-GATEWAY"\nexport ANTHROPIC_AUTH_TOKEN="YOUR_API_KEY"';
 } else {
   title='Cursor · '+(third?'Ofox 官方标记直接接入不兼容':'官方 API Key 设置');
   detail=third?'Ofox 官方明确不建议直接连接 Cursor。可在 Cursor 内置终端运行已配置 Ofox 的 Codex CLI 或 Claude Code；不要把购买 API 额度当作 Cursor Pro 订阅。':'打开 Cursor Settings → Models 查看官方支持的 API Key 选项；第三方接口限制较多。';
   code='# Cursor 图形界面操作\n# 1. Cursor Settings → Models\n# 2. 选择官方支持的服务提供商\n# 3. 检查是否支持自定义 Base URL\n# 4. Verify Key 并测试常用操作';
 }
 $('wizard-status').textContent=title;
 $('wizard-description').textContent=detail+(third?' 当前未经过 JXZNE AI 的真实 Ofox 兼容性测试；请勿据此直接充值。':'');
 $('wizard-code').textContent=code;
 $('wizard-docs').href=docs[t];
}
[tool,os,provider].forEach(x=>x.addEventListener('change',render));
$('wizard-copy').addEventListener('click',async()=>{try{await navigator.clipboard.writeText($('wizard-code').textContent);$('wizard-copy').textContent='已复制';}catch(e){$('wizard-copy').textContent='请手动选择复制';}});
render();
})();