// JXZNE AI partner referral destination. Do not place private credentials here.
const PARTNER_URL = 'https://ofox.ai/x/itoken';
document.querySelectorAll('a.js-partner').forEach((link) => {
  link.href = PARTNER_URL;
  link.target = '_blank';
  link.rel = 'noopener noreferrer sponsored';
});

const recommendations = {
  code: ['编程与 Agent','优先比较 GPT 与 Claude 系列，关注代码能力、工具调用、延迟和实际单价。复杂任务也可以测试其他模型。','建议对比：GPT · Claude'],
  write: ['写作与办公','可以从 Claude、GPT、Qwen 系列开始，结合中文表达、长文档能力、输出质量与成本进行试用。','建议对比：Claude · GPT · Qwen'],
  reason: ['复杂推理','从 GPT、DeepSeek 等推理模型开始，使用自己的真实任务对比正确率、响应速度与调用成本。','建议对比：GPT · DeepSeek'],
  budget: ['成本优先','从 Gemini Flash、Qwen、DeepSeek 等系列筛选，先查看实时输入/输出价格及速率限制，再做小样本测试。','建议对比：Gemini · Qwen · DeepSeek']
};
const options = document.querySelectorAll('.usecase');
options.forEach((button) => button.addEventListener('click', () => {
  options.forEach((item) => { const selected = item === button; item.classList.toggle('active',selected); item.setAttribute('aria-pressed',String(selected)); });
  const selected = recommendations[button.dataset.case];
  if (!selected) return;
  document.getElementById('rec-title').textContent = selected[0];
  document.getElementById('rec-desc').textContent = selected[1];
  document.getElementById('rec-tags').textContent = selected[2];
}));
