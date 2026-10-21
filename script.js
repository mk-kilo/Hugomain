// JXZNE AI partner referral destination. Do not place private credentials here.
const PARTNER_URL = 'https://ofox.ai/x/itoken';
document.querySelectorAll('a.js-partner').forEach((link) => {
  link.href = PARTNER_URL;
  link.target = '_blank';
  link.rel = 'noopener noreferrer sponsored';
});
