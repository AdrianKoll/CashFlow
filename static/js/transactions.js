/* CashFlow — Movimentações (CRUD) */

let txRowsCache = [];
let editingTxId = null;

async function loadTransactions() {
  const body = qs('#txTable');
  if (!body) return;
  const rows = await getJSON('/api/transactions' + periodQuery());
  txRowsCache = rows.transactions || rows || [];
  if (!txRowsCache.length) {
    body.innerHTML = '<tr><td colspan="6" class="muted">Nenhuma movimentação nesse período.</td></tr>';
    return;
  }
  body.innerHTML = txRowsCache.map(t => `
    <tr>
      <td data-label="Tipo">${t.kind === 'entrada' ? 'Entrada' : 'Saída'}</td>
      <td data-label="Descrição"><b>${escapeAttr(t.title)}</b><p class="muted">${escapeAttr(t.entity || t.payment_method)}</p></td>
      <td data-label="Categoria">${escapeAttr(t.category)}</td>
      <td data-label="Valor" class="tx-value ${t.kind}">${t.kind === 'saida' ? '- ' : ''}${brl(t.amount)}</td>
      <td data-label="Data">${escapeAttr(t.created_at)}</td>
      <td data-label="Ação" class="action-cell"><div class="action-buttons">
        <button class="del soft action-icon edit" type="button" title="Editar" aria-label="Editar movimentação" onclick="editTx(${t.id})">${ICON_EDIT}</button>
        <button class="del action-icon remove" type="button" title="Remover" aria-label="Remover movimentação" onclick="deleteTx(${t.id})">${ICON_TRASH}</button>
      </div></td>
    </tr>`).join('');
}

async function loadSummary() {
  const d = await getJSON('/api/summary/' + periodQuery());
  const c = d.cards || d;

  ['Entradas', 'Saidas', 'Saldo', 'Mes'].forEach(k => {
    const el  = qs('#card' + k);
    const key = k.toLowerCase() === 'saidas' ? 'saidas'
              : k.toLowerCase() === 'mes'    ? 'saldo_mes'
              : k.toLowerCase();
    if (el) el.textContent = brl(c[key] ?? d[key.replace('_mes', '')] ?? d[key]);
  });

  const ms = qs('#mobileSaldo');
  if (ms) ms.textContent = brl(d.saldo ?? (c && c.saldo));

  renderTx(qs('#latestEntries'), (d.recent || d.transactions || []).filter(x => x.kind === 'entrada').slice(0, 4));
  renderTx(qs('#latestOut'),     (d.recent || d.transactions || []).filter(x => x.kind === 'saida').slice(0, 4));

  ['rEntradas', 'rSaidas', 'rSaldo'].forEach(id => {
    const el = qs('#' + id);
    if (el) el.textContent = brl(d[id.replace('r', '').toLowerCase()] ?? (c && c[id.replace('r', '').toLowerCase()]));
  });

  drawCashChart(qs('#cashChart'), d.chart);
  drawDonut(qs('#donutChart'), d.distribution);

  const legend = qs('#distributionLegend');
  if (legend && d.distribution) {
    legend.innerHTML = d.distribution.map((x, i) =>
      `<div class="legend-row"><span><b style="color:${['#20d583','#5361ff','#ff4d55'][i]}">●</b> ${escapeAttr(x.label)}</span><span><b>${x.value}%</b><br>${brl(x.amount)}</span></div>`
    ).join('');
  }
}

async function loadTxCategories(selectedId) {
  const cats   = await getJSON('/api/products/categories');
  const select = qs('#categorySelect');
  if (select) {
    select.innerHTML = cats.map(c => `<option value="${Number(c.id)}">${escapeAttr(c.name)}</option>`).join('');
    if (selectedId) select.value = String(selectedId);
  }
}

async function openModal(kind) {
  editingTxId = null;
  const form = qs('#txForm');
  if (form) form.reset();
  kind = kind || 'entrada';
  const m = qs('#txModal');
  if (!m) return;
  requestAnimationFrame(() => m.classList.add('show'));
  if (kind) qs('#txKind').value = kind;
  const title = m.querySelector('h2');
  if (title) title.textContent = 'Nova Movimentação';
  const submit = m.querySelector('button[type="submit"]');
  if (submit) submit.textContent = 'Salvar movimentação';
  await loadTxCategories();
}

async function editTx(id) {
  const item = txRowsCache.find(t => Number(t.id) === Number(id));
  if (!item) return;
  editingTxId = id;
  const m    = qs('#txModal');
  const form = qs('#txForm');
  if (!m || !form) return;
  await loadTxCategories(item.category_id);
  form.kind.value           = item.kind           || 'entrada';
  form.amount.value         = Number(item.amount  || 0);
  form.title.value          = item.title          || '';
  form.entity.value         = item.entity         || '';
  form.payment_method.value = item.method         || 'PIX';
  const title  = m.querySelector('h2');
  if (title) title.textContent = 'Editar Movimentação';
  const submit = m.querySelector('button[type="submit"]');
  if (submit) submit.textContent = 'Salvar edição';
  requestAnimationFrame(() => m.classList.add('show'));
}

function closeModal() {
  qs('#txModal')?.classList.remove('show');
  editingTxId = null;
}

async function deleteTx(id) {
  await fetch('/api/transactions/' + id, { method: 'DELETE' });
  await loadTransactions();
  await loadSummary();
}

async function submitTx(e) {
  e.preventDefault();
  const f       = new FormData(e.target);
  const payload = Object.fromEntries(f.entries());
  const url     = editingTxId ? '/api/transactions/' + editingTxId : '/api/transactions/';
  const method  = editingTxId ? 'PATCH' : 'POST';
  const res     = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.ok === false) {
    showToast(data.error || 'Não foi possível salvar a movimentação.', 'error');
    return;
  }
  showToast(editingTxId ? 'Movimentação editada com sucesso.' : 'Movimentação inserida com sucesso.');
  e.target.reset();
  closeModal();
  await setPeriod(window.currentPeriod);
}

async function resetAllData() {
  const ok = confirm('Tem certeza que deseja resetar todos os dados? O sistema criará uma cópia de segurança antes de apagar.');
  if (!ok) return;
  const password = prompt('Digite a senha atual para confirmar o reset:');
  if (!password) return;
  const res  = await fetch('/api/reset-data', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  });
  const data = await res.json();
  if (!res.ok || !data.ok) {
    alert(data.error || 'Não foi possível resetar os dados.');
    return;
  }
  alert(`Dados resetados. Movimentações removidas: ${data.removed || 0}. Cópia: ${data.copia || 'não disponível'}`);
  await setPeriod(window.currentPeriod);
}
