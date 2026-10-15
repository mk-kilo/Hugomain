const PARTNER_URL = 'https://ofox.ai/';

document.querySelectorAll('.js-partner').forEach((el) => {
  el.href = PARTNER_URL;
  el.target = '_blank';
  el.rel = 'noopener noreferrer';
});
