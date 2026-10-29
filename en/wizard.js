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
   title='Codex · '+(third?'Ofox publishes a guide; JXZNE has not verified a paid call':'Official config pointer');
   detail='Codex uses a model-provider config. A Chat Completions endpoint may not be enough. Confirm Responses API support, and check the official docs for your version.';
   code=third
     ? '# Checklist (not a ready-to-run config)\n# 1. Confirm Ofox exposes a Responses API Codex can call\n# 2. Confirm the model id, auth and tool calls\n# 3. Test with a small balance before a large top-up\n# Config file: '+file
     : '# Official config file: '+file+'\n# Fill model and provider fields from the official docs\n# Do not commit an API key';
 } else if(t==='claude'){
   title='Claude Code · '+(third?'Ofox publishes a guide; JXZNE has not verified a paid call':'Gateway variables');
   detail='Claude Code’s gateway has to speak the Anthropic API. The variables below match the official shape. They do not prove a third-party endpoint works.';
   code = platform==='windows'
   ? '# PowerShell (replace the placeholders only after the gateway is confirmed)\n$env:ANTHROPIC_BASE_URL="https://YOUR-COMPATIBLE-GATEWAY"\n$env:ANTHROPIC_AUTH_TOKEN="YOUR_API_KEY"'
   : '# Terminal (replace the placeholders only after the gateway is confirmed)\nexport ANTHROPIC_BASE_URL="https://YOUR-COMPATIBLE-GATEWAY"\nexport ANTHROPIC_AUTH_TOKEN="YOUR_API_KEY"';
 } else {
   title='Cursor · '+(third?'Ofox marks a direct connection as unsuitable':'Official API key settings');
   detail=third
     ? 'Ofox’s own notice says not to connect Cursor directly. You can run a separately configured Codex CLI or Claude Code in Cursor’s terminal. API credit is not a Cursor Pro subscription.'
     : 'Open Cursor Settings → Models and read which API keys the current version accepts. Third-party endpoints are limited.';
   code='# Cursor UI\n# 1. Cursor Settings → Models\n# 2. Pick a provider the official docs support\n# 3. Check whether a custom base URL is supported\n# 4. Verify the key, then test the actions you use\n# Ofox direct Cursor use: see https://ofox.ai/docs/integrations/cursor';
 }
 $('wizard-status').textContent=title;
 $('wizard-description').textContent=detail+(third?' JXZNE has not completed a real Ofox compatibility test. Do not top up on the basis of this helper alone.':'');
 $('wizard-code').textContent=code;
 $('wizard-docs').href=docs[t];
}
[tool,os,provider].forEach(x=>x.addEventListener('change',render));
$('wizard-copy').addEventListener('click',async()=>{try{await navigator.clipboard.writeText($('wizard-code').textContent);$('wizard-copy').textContent='Copied';}catch(e){$('wizard-copy').textContent='Select the code and copy it';}});
render();
})();
