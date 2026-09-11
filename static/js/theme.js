/* CashFlow — Gerenciamento de tema (claro / escuro) */

function setTheme(light) {
  const root = document.documentElement;
  root.classList.toggle('light', light);
  root.classList.toggle('dark', !light);
  root.style.colorScheme = light ? 'light' : 'dark';
  if (document.body) document.body.classList.toggle('light', light);
  localStorage.setItem('cashTheme', light ? 'light' : 'dark');

  const t = qs('#themeToggle');
  if (t) t.checked = !light;

  const mb = qs('#mobileThemeBtn');
  if (mb) {
    mb.textContent = light ? '☀' : '☾';
    mb.setAttribute('aria-label', light ? 'Tema claro ativo' : 'Tema escuro ativo');
  }
}

/* Aplica o tema salvo imediatamente para evitar flash */
try {
  setTheme(localStorage.getItem('cashTheme') === 'light');
} catch (e) {}
