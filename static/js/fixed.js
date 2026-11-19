/* CashFlow — Registros fixos mensais (CRUD + filtros) */

let fixedRowsCache = [];

/* ---- Item row builder ---- */
function fixedItemRow(name = '', quantity = 1, unit = 'un', unit_price = '') {
  const wrap = document.createElement('div');
  wrap.className = 'fixed-item-row fixed-item-card';
  wrap.innerHTML = `
    <label class="fixed-field fixed-product-field fixed-item-name"><small>Produto</small><input class="fixed-item-name-input" placeholder="Ex.: arroz" value="${escapeAttr(name)}"></label>
    <label class="fixed-field"><small>Qtd.</small><input class="fixed-item-quantity" type="number" step="0.01" min="0" placeholder="0" value="${quantity || ''}"></label>
    <label class="fixed-field"><small>Unidade</small><select class="fixed-item-unit">
      <option value="un">un</option>
      <option value="pacote">pacote</option>
      <option value="kg">kg</option>
      <option value="g">g</option>
      <option value="litro">litro</option>
      <option value="caixa">caixa</option>
      <option value="fardo">fardo</option>
    </select></label>
    <label class="fixed-field"><small>Valor unit.</small><input class="fixed-item-unit-price" type="number" step="0.01" min="0" placeholder="0,00" value="${unit_price || ''}"></label>
    <label class="fixed-field fixed-subtotal-field"><small>Subtotal</small><input class="fixed-item-subtotal" type="text" placeholder="R$ 0,00" readonly></label>
    <button class="del fixed-remove-item" type="button" title="Remover item" aria-label="Remover item">${ICON_TRASH}</button>`;

  const unitSelect = wrap.querySelector('.fixed-item-unit');
  if (unitSelect) unitSelect.value = unit || 'un';

  wrap.querySelector('.del').addEventListener('click', () => { wrap.remove(); updateFixedTotal(); });
  wrap.querySelectorAll('input, select').forEach(input => input.addEventListener('input', updateFixedTotal));
  updateFixedRowSubtotal(wrap);
  return wrap;
}

function updateFixedRowSubtotal(row) {
  const qty       = Number(row.querySelector('.fixed-item-quantity')?.value   || 0);
  const unitPrice = Number(row.querySelector('.fixed-item-unit-price')?.value || 0);
  const subtotal  = qty * unitPrice;
  const field     = row.querySelector('.fixed-item-subtotal');
  if (field) field.value = subtotal ? brl(subtotal) : '';
  return subtotal;
}

function updateFixedTotal() {
  const rows  = qsa('.fixed-item-row');
  const total = rows.reduce((sum, row) => sum + updateFixedRowSubtotal(row), 0);
  const field = qs('#fixedAmount');
  if (field) field.value = total ? total.toFixed(2) : '';
  const label = qs('#fixedAmountLabel');
  if (label) label.textContent = brl(total || 0);
  const preview = qs('#fixedTotalPreview');
  if (preview) preview.textContent = brl(total || 0);
  const count = qs('#fixedItemCount');
  if (count) count.textContent = rows.length;
}

function addFixedItem(name = '', quantity = 1, unit = 'un', unit_price = '') {
  const list = qs('#fixedItemsList');
  if (!list) return;
  list.appendChild(fixedItemRow(name, quantity, unit, unit_price));
  updateFixedTotal();
}

/* ---- Payload helpers ---- */
function collectFixedPayload(form) {
  const data  = Object.fromEntries(new FormData(form).entries());
  data.items  = qsa('.fixed-item-row').map(row => {
    const quantity   = Number(row.querySelector('.fixed-item-quantity')?.value   || 0);
    const unit_price = Number(row.querySelector('.fixed-item-unit-price')?.value || 0);
    return {
      name:       (row.querySelector('.fixed-item-name-input')?.value || '').trim(),
      quantity,
      unit:       row.querySelector('.fixed-item-unit')?.value || 'un',
      unit_price,
      amount:     quantity * unit_price,
    };
  }).filter(item => item.name && item.quantity > 0 && item.unit_price > 0);
  data.amount = data.items.reduce((sum, item) => sum + Number(item.amount || 0), 0);
  return data;
}

/* ---- Form reset ---- */
function resetFixedForm() {
  const form = qs('#fixedForm');
  if (!form) return;
  form.reset();
  if (qs('#fixedId'))      qs('#fixedId').value = '';
  if (qs('#fixedDay'))     qs('#fixedDay').value = 1;
  if (qs('#fixedPayment')) qs('#fixedPayment').value = 'PIX';
  if (qs('#fixedSubmitBtn')) {
    qs('#fixedSubmitBtn').textContent = 'Salvar despesa';
    qs('#fixedSubmitBtn').classList.remove('loading');
  }
  if (qs('#cancelFixedEditBtn')) qs('#cancelFixedEditBtn').hidden = true;
  const list = qs('#fixedItemsList');
  if (list) list.innerHTML = '';
  addFixedItem();
}

/* ---- Edit ---- */
function editFixed(id) {
  if (!id) { showToast('Não foi possível identificar a despesa para edição.', 'error'); return; }
  if (!qs('#fixedForm')) {
    localStorage.setItem('cashEditFixedId', String(id));
    location.href = '/registros-fixos/despesa-mensal';
    return;
  }
  const item = fixedRowsCache.find(x => Number(x.id) === Number(id));
  if (!item) { showToast('Despesa não encontrada. Recarregando dados...', 'error'); loadFixedRecords(); return; }

  qs('#fixedId').value = item.id;
  qs('#fixedKind').value = item.kind || 'saida';
  qs('#fixedTitle').value = item.title || '';
  qs('#fixedEntity').value = item.entity || '';
  if (qs('#fixedCategorySelect')) qs('#fixedCategorySelect').value = item.category_id || '';
  if (qs('#fixedDay'))     qs('#fixedDay').value = item.day_of_month || 1;
  if (qs('#fixedPayment')) qs('#fixedPayment').value = item.method || 'PIX';

  const list = qs('#fixedItemsList');
  if (list) list.innerHTML = '';
  if (item.items && item.items.length) {
    item.items.forEach(child => addFixedItem(child.name, child.quantity || 1, child.unit || 'un', Number(child.unit_price || child.amount || 0).toFixed(2)));
  } else {
    addFixedItem(item.title || 'Item', 1, 'un', Number(item.amount || 0).toFixed(2));
  }

  if (qs('#fixedSubmitBtn')) qs('#fixedSubmitBtn').textContent = 'Salvar alterações';
  if (qs('#cancelFixedEditBtn')) qs('#cancelFixedEditBtn').hidden = false;
  qs('#fixedForm')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  updateFixedTotal();
}

/* ---- Filters ---- */
function getFixedFilteredRows() {
  let rows    = [...(fixedRowsCache || [])];
  const term    = (qs('#fixedSearch')?.value       || '').trim().toLowerCase();
  const type    = qs('#fixedTypeFilter')?.value    || 'all';
  const status  = qs('#fixedStatusFilter')?.value  || 'all';
  const payment = qs('#fixedPaymentFilter')?.value || 'all';
  const sort    = qs('#fixedSort')?.value          || 'day';

  if (term) {
    rows = rows.filter(item => {
      const itemsText = (item.items || []).map(x => `${x.name} ${x.unit} ${x.notes || ''}`).join(' ');
      return `${item.title} ${item.entity || ''} ${item.method || ''} ${itemsText}`.toLowerCase().includes(term);
    });
  }
  if (type    !== 'all') rows = rows.filter(item => item.kind === type);
  if (status  !== 'all') rows = rows.filter(item => status === 'active' ? item.active : !item.active);
  if (payment !== 'all') rows = rows.filter(item => (item.method || '') === payment);

  rows.sort((a, b) => {
    if (sort === 'amount_desc') return Number(b.amount || 0) - Number(a.amount || 0);
    if (sort === 'amount_asc')  return Number(a.amount || 0) - Number(b.amount || 0);
    if (sort === 'title')       return String(a.title || '').localeCompare(String(b.title || ''), 'pt-BR');
    return Number(a.day_of_month || 1) - Number(b.day_of_month || 1) || String(a.title || '').localeCompare(String(b.title || ''), 'pt-BR');
  });
  return rows;
}

function syncFixedStatusChips() {
  const value = qs('#fixedStatusFilter')?.value || 'all';
  qsa('[data-fixed-status]').forEach(btn => btn.classList.toggle('active', btn.dataset.fixedStatus === value));
}

function clearFixedFilters() {
  if (qs('#fixedSearch'))        qs('#fixedSearch').value        = '';
  if (qs('#fixedTypeFilter'))    qs('#fixedTypeFilter').value    = 'all';
  if (qs('#fixedStatusFilter'))  qs('#fixedStatusFilter').value  = 'all';
  if (qs('#fixedPaymentFilter')) qs('#fixedPaymentFilter').value = 'all';
  if (qs('#fixedSort'))          qs('#fixedSort').value          = 'day';
  syncFixedStatusChips();
  renderFixedRows(getFixedFilteredRows());
}

/* ---- Rendering ---- */
function renderFixedInsights(rows) {
  const box = qs('#fixedInsights');
  if (!box) return;
  const ativos   = rows.filter(x => x.active);
  const despesas = ativos.filter(x => x.kind === 'saida').reduce((s, x) => s + Number(x.amount || 0), 0);
  const rendas   = ativos.filter(x => x.kind === 'entrada').reduce((s, x) => s + Number(x.amount || 0), 0);
  const itens    = ativos.reduce((s, x) => s + Number(x.items_count || (x.items || []).length || 0), 0);
  box.innerHTML = `
    <div class="fixed-insight-card"><small>Ativos</small><strong>${ativos.length}</strong></div>
    <div class="fixed-insight-card"><small>Despesa mensal</small><strong>${brl(despesas)}</strong></div>
    <div class="fixed-insight-card"><small>Renda mensal</small><strong>${brl(rendas)}</strong></div>
    <div class="fixed-insight-card"><small>Itens controlados</small><strong>${itens}</strong></div>`;
}

function updateFixedFilterResult(total, visible) {
  const el = qs('#fixedFilterResult');
  if (!el) return;
  const term    = (qs('#fixedSearch')?.value       || '').trim();
  const status  = qs('#fixedStatusFilter')?.value  || 'all';
  const type    = qs('#fixedTypeFilter')?.value    || 'all';
  const payment = qs('#fixedPaymentFilter')?.value || 'all';
  const active  = [term ? 'busca' : '', status !== 'all' ? 'status' : '', type !== 'all' ? 'tipo' : '', payment !== 'all' ? 'pagamento' : ''].filter(Boolean);
  el.textContent = active.length
    ? `Mostrando ${visible} de ${total} despesa(s) com filtro aplicado.`
    : `Mostrando todas as ${total} despesa(s) cadastrada(s).`;
}

function renderFixedRows(rows) {
  const body = qs('#fixedTable');
  if (!body) return;
  const viewRows = rows || getFixedFilteredRows();
  renderFixedInsights(fixedRowsCache || []);
  updateFixedFilterResult((fixedRowsCache || []).length, viewRows.length);

  if (!viewRows.length) {
    body.innerHTML = '<tr><td colspan="7" class="muted">Nenhuma despesa encontrada com os filtros atuais.</td></tr>';
    return;
  }

  body.innerHTML = viewRows.map(item => {
    const preview = (item.items || []).slice(0, 3).map(x =>
      `${escapeAttr(x.name)}: ${Number(x.quantity || 1).toLocaleString('pt-BR')} ${escapeAttr(x.unit || 'un')} x ${brl(x.unit_price || 0)}`
    ).join(' · ');
    const more = item.items_count > 3 ? ` +${item.items_count - 3} item(ns)` : '';
    return `
    <tr>
      <td data-label="Tipo">${item.kind === 'entrada' ? 'Renda fixa' : 'Despesa fixa'}</td>
      <td data-label="Descrição"><b>${escapeAttr(item.title)}</b>
        <p class="muted">${escapeAttr(item.entity || item.method || 'Automático')} · último mês: ${escapeAttr(item.last_generated_month)}</p>
        <span class="item-counter-pill">${item.items_count || 0} item(ns)</span></td>
      <td data-label="Total" class="tx-value ${item.kind}">${item.kind === 'saida' ? '- ' : ''}${brl(item.amount)}</td>
      <td data-label="Itens"><span class="items-preview">${preview || 'Sem itens detalhados'}${more}</span></td>
      <td data-label="Dia">${item.day_of_month}</td>
      <td data-label="Status"><span class="status-pill ${item.active ? 'active' : 'inactive'}">${item.active ? 'Ativo' : 'Pausado'}</span></td>
      <td data-label="Ação" class="action-cell"><div class="action-buttons">
        <button class="del soft action-icon edit" type="button" onclick="editFixed(${item.id})">${ICON_EDIT}</button>
        <button class="del soft action-icon toggle" type="button" onclick="toggleFixed(${item.id})">${item.active ? ICON_PAUSE : ICON_PLAY}</button>
        <button class="del action-icon remove" type="button" onclick="deleteFixed(${item.id})">${ICON_TRASH}</button>
      </div></td>
    </tr>`;
  }).join('');
}

/* ---- API calls ---- */
async function loadFixedRecords() {
  const body = qs('#fixedTable');
  if (!body && !qs('#fixedForm')) return;
  const rows = await getJSON('/api/fixed-records/');
  fixedRowsCache = rows || [];
  if (body) renderFixedRows(getFixedFilteredRows());
}

async function loadFixedCategories() {
  const select = qs('#fixedCategorySelect');
  if (!select) return;
  const cats = await getJSON('/api/products/categories');
  select.innerHTML = cats.map(c =>
    `<option value="${Number(c.id)}" ${c.name === 'Fixas' ? 'selected' : ''}>${escapeAttr(c.name)}</option>`
  ).join('');
}

async function submitFixed(e) {
  e.preventDefault();
  const payload = collectFixedPayload(e.target);
  if (!payload.items.length) { showToast('Adicione pelo menos um item com quantidade e valor.', 'error'); return; }
  const id        = qs('#fixedId')?.value;
  const url       = id ? '/api/fixed-records/' + id : '/api/fixed-records/';
  const method    = id ? 'PATCH' : 'POST';
  const submitBtn = qs('#fixedSubmitBtn');
  submitBtn?.classList.add('loading');
  if (submitBtn) submitBtn.textContent = id ? 'Salvando...' : 'Inserindo...';

  const res  = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  const data = await res.json();

  if (!res.ok) {
    submitBtn?.classList.remove('loading');
    if (submitBtn) submitBtn.textContent = id ? 'Salvar alterações' : 'Salvar despesa';
    showToast(data.error || 'Não foi possível salvar a despesa.', 'error');
    return;
  }
  showToast(id ? 'Despesa recorrente atualizada com sucesso.' : 'Despesa recorrente criada com sucesso.');
  resetFixedForm();
  await loadFixedRecords();
}

async function toggleFixed(id) {
  const item = fixedRowsCache.find(x => Number(x.id) === Number(id));
  if (!item) return;
  const res  = await fetch('/api/fixed-records/' + id, {
    method:  'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ active: !item.active }),
  });
  const data = await res.json();
  showToast(data.active ? 'Despesa recorrente ativada.' : 'Despesa recorrente pausada.');
  await loadFixedRecords();
}

async function deleteFixed(id) {
  if (!confirm('Remover esta despesa recorrente? As movimentações já lançadas não serão apagadas.')) return;
  await fetch('/api/fixed-records/' + id, { method: 'DELETE' });
  showToast('Despesa recorrente removida com sucesso.');
  await loadFixedRecords();
}

async function generateFixedNow() {
  const res  = await fetch('/api/fixed-records/generate-now', { method: 'POST' });
  const data = await res.json();
  showToast(data.generated
    ? `${data.generated} despesa(s) gerada(s) para este mês.`
    : 'Nenhuma despesa nova para gerar neste mês.'
  );
  await loadFixedRecords();
  if (qs('#txTable')) await loadTransactions();
  await loadSummary();
}

async function copyFixedList() {
  const rows = getFixedFilteredRows();
  if (!rows.length) { showToast('Nenhuma despesa para copiar.', 'error'); return; }
  const text = rows.map(item => {
    const itens = (item.items || []).map(x =>
      `- ${x.name}: ${Number(x.quantity || 1).toLocaleString('pt-BR')} ${x.unit || 'un'} x ${brl(x.unit_price || 0)} = ${brl(x.amount || 0)}`
    ).join('\n');
    return `${item.title} | ${item.kind === 'entrada' ? 'Renda' : 'Despesa'} | ${item.method || 'Sem pagamento'} | dia ${item.day_of_month} | total ${brl(item.amount)}\n${itens}`;
  }).join('\n\n');
  try {
    await navigator.clipboard.writeText(text);
    showToast('Lista copiada para a área de transferência.');
  } catch {
    showToast('Não foi possível copiar automaticamente.', 'error');
  }
}
