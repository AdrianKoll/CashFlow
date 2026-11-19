/* CashFlow — Utilitários globais */

/* Proteção CSRF: anexa o token da página (meta csrf-token) a toda requisição
   do mesmo domínio que altera dados (POST, PATCH, PUT, DELETE). */
(function installCsrfFetch() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  const token = meta ? meta.content : '';
  if (!token) return;
  const originalFetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    init = init || {};
    const request = input instanceof Request ? input : null;
    const method = String(init.method || (request && request.method) || 'GET').toUpperCase();
    const url = new URL(request ? request.url : input, window.location.href);
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method) && url.origin === window.location.origin) {
      const headers = new Headers(init.headers || (request && request.headers) || {});
      if (!headers.has('X-CSRFToken')) headers.set('X-CSRFToken', token);
      init = Object.assign({}, init, { headers });
    }
    return originalFetch(input, init);
  };
})();

function brl(v) {
  return Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function qs(s)  { return document.querySelector(s); }
function qsa(s) { return [...document.querySelectorAll(s)]; }

async function getJSON(url) {
  const r = await fetch(url);
  return r.json();
}

function periodQuery() {
  return '?period=' + encodeURIComponent(window.currentPeriod || 'today');
}

function txIcon(kind) {
  return kind === 'entrada' ? '↑' : '↓';
}

function renderTx(container, rows) {
  if (!container) return;
  if (!rows.length) {
    container.innerHTML = '<p class="empty-state">Nenhuma movimentação nesse período.</p>';
    return;
  }
  container.innerHTML = rows.map(t => `
    <div class="tx-item">
      <span class="tx-icon ${t.kind}">${txIcon(t.kind)}</span>
      <div><h3>${escapeAttr(t.title)}</h3><p>${escapeAttr(t.entity || t.method)}</p></div>
      <div class="tx-value ${t.kind}">${t.kind === 'saida' ? '- ' : ''}${brl(t.amount)}<p>${escapeAttr(t.time || t.created_at)}</p></div>
    </div>`).join('');
}

function escapeAttr(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('"', '&quot;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll("'", '&#39;');
}

function showToast(message, type = 'success') {
  let stack = qs('#toastStack');
  if (!stack) {
    stack = document.createElement('div');
    stack.id = 'toastStack';
    stack.className = 'toast-stack';
    document.body.appendChild(stack);
  }
  const card = document.createElement('div');
  card.className = `toast-card ${type}`;
  const strong = document.createElement('strong');
  strong.textContent = message;  // texto puro: nunca interpretar HTML
  card.appendChild(strong);
  stack.appendChild(card);
  setTimeout(() => card.classList.add('show'), 20);
  setTimeout(() => {
    card.classList.remove('show');
    setTimeout(() => card.remove(), 250);
  }, 2600);
}

const ICON_EDIT  = `<svg class="ui-action-svg" aria-hidden="true" viewBox="0 0 24 24" fill="none"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>`;
const ICON_PAUSE = `<svg class="ui-action-svg" aria-hidden="true" viewBox="0 0 24 24" fill="none"><path d="M10 5v14"/><path d="M14 5v14"/></svg>`;
const ICON_TRASH = `<svg class="ui-action-svg" aria-hidden="true" viewBox="0 0 24 24" fill="none"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>`;
const ICON_PLAY  = `<svg class="ui-action-svg" aria-hidden="true" viewBox="0 0 24 24" fill="none"><polygon points="7 4 19 12 7 20 7 4"/></svg>`;
