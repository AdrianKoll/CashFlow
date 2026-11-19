/* CashFlow — Cadastro de produtos e dashboard de registros fixos */

let productsCache = [];

/* ---- Product form helpers ---- */
function resetProductForm() {
  const form = qs('#productForm');
  if (!form) return;
  form.reset();
  if (qs('#productId'))        qs('#productId').value        = '';
  if (qs('#productQty'))       qs('#productQty').value       = 1;
  if (qs('#productSubmitBtn')) qs('#productSubmitBtn').textContent = 'Salvar produto';
  if (qs('#cancelProductEditBtn')) qs('#cancelProductEditBtn').hidden = true;
}

function renderProducts() {
  const list = qs('#productsList');
  if (!list) return;
  const term = (qs('#productSearch')?.value || '').toLowerCase().trim();
  const rows = productsCache.filter(p => `${p.name} ${p.unit} ${p.notes || ''}`.toLowerCase().includes(term));
  if (!rows.length) {
    list.innerHTML = '<p class="empty-state">Nenhum produto encontrado.</p>';
    return;
  }
  list.innerHTML = rows.map(p => `
    <div class="product-card ${p.active ? '' : 'inactive'}">
      <div>
        <b>${escapeAttr(p.name)}</b>
        <p class="muted">${Number(p.default_quantity || 1).toLocaleString('pt-BR')} ${escapeAttr(p.unit || 'un')} · ${brl(p.unit_price)} un.${p.notes ? ' · ' + escapeAttr(p.notes) : ''}</p>
      </div>
      <div class="product-actions"><div class="action-buttons">
        <button class="del soft action-icon edit"   type="button" title="Editar"  aria-label="Editar produto"  onclick="editProduct(${p.id})">${ICON_EDIT}</button>
        <button class="del soft action-icon toggle" type="button" title="${p.active ? 'Pausar' : 'Ativar'}" onclick="toggleProduct(${p.id})">${p.active ? ICON_PAUSE : ICON_PLAY}</button>
        <button class="del action-icon remove"      type="button" title="Remover" aria-label="Remover produto" onclick="deleteProduct(${p.id})">${ICON_TRASH}</button>
      </div></div>
    </div>`).join('');
}

function renderBuilderProducts() {
  const list = qs('#builderProductsList');
  if (!list) return;
  const term = (qs('#builderProductSearch')?.value || '').toLowerCase().trim();
  const rows = productsCache.filter(p => p.active && `${p.name} ${p.unit} ${p.notes || ''}`.toLowerCase().includes(term));
  if (!rows.length) {
    list.innerHTML = '<p class="empty-state">Nenhum produto ativo. Cadastre em Produtos.</p>';
    return;
  }
  list.innerHTML = rows.map(p => `
    <button class="product-pick-card" type="button" onclick="addProductToFixed(${p.id})">
      <span><b>${escapeAttr(p.name)}</b><small>${Number(p.default_quantity || 1).toLocaleString('pt-BR')} ${escapeAttr(p.unit || 'un')} · ${brl(p.unit_price)}</small></span>
      <em>+</em>
    </button>`).join('');
}

async function loadProducts() {
  if (!qs('#productsList') && !qs('#builderProductsList')) return;
  productsCache = await getJSON('/api/products/');
  renderProducts();
  renderBuilderProducts();
}

function addProductToFixed(id) {
  const p = productsCache.find(x => Number(x.id) === Number(id));
  if (!p) return;
  addFixedItem(p.name, p.default_quantity || 1, p.unit || 'un', Number(p.unit_price || 0).toFixed(2));
  showToast(`${p.name} adicionado à despesa.`);
}

function editProduct(id) {
  const p = productsCache.find(x => Number(x.id) === Number(id));
  if (!p) return;
  if (qs('#productId'))    qs('#productId').value    = p.id;
  if (qs('#productName'))  qs('#productName').value  = p.name  || '';
  if (qs('#productUnit'))  qs('#productUnit').value  = p.unit  || 'un';
  if (qs('#productQty'))   qs('#productQty').value   = p.default_quantity || 1;
  if (qs('#productPrice')) qs('#productPrice').value = Number(p.unit_price || 0).toFixed(2);
  if (qs('#productNotes')) qs('#productNotes').value = p.notes || '';
  if (qs('#productSubmitBtn'))      qs('#productSubmitBtn').textContent = 'Salvar alterações';
  if (qs('#cancelProductEditBtn'))  qs('#cancelProductEditBtn').hidden  = false;
  qs('#productForm')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function submitProduct(e) {
  e.preventDefault();
  const id     = qs('#productId')?.value;
  const url    = id ? '/api/products/' + id : '/api/products/';
  const method = id ? 'PATCH' : 'POST';
  const payload = Object.fromEntries(new FormData(e.target).entries());
  const res    = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    showToast(data.error || 'Não foi possível salvar produto.', 'error');
    return;
  }
  showToast(id ? 'Produto atualizado com sucesso.' : 'Produto inserido com sucesso.');
  resetProductForm();
  await loadProducts();
}

async function toggleProduct(id) {
  const p = productsCache.find(x => Number(x.id) === Number(id));
  if (!p) return;
  const res  = await fetch('/api/products/' + id, {
    method:  'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ active: !p.active }),
  });
  const data = await res.json();
  showToast(data.active ? 'Produto ativado.' : 'Produto pausado.');
  await loadProducts();
}

async function deleteProduct(id) {
  if (!confirm('Remover este produto? Despesas já criadas não serão apagadas.')) return;
  await fetch('/api/products/' + id, { method: 'DELETE' });
  showToast('Produto removido.');
  await loadProducts();
}

/* ---- Dashboard de registros fixos ---- */
async function loadFixedDashboard() {
  if (!qs('#fxDashExpense')) return;
  const d = await getJSON('/api/fixed-records/summary');

  if (qs('#fxDashExpense'))  qs('#fxDashExpense').textContent  = brl(d.monthly_expense);
  if (qs('#fxDashIncome'))   qs('#fxDashIncome').textContent   = brl(d.monthly_income);
  if (qs('#fxDashActive'))   qs('#fxDashActive').textContent   = d.active_total;
  if (qs('#fxDashInactive')) qs('#fxDashInactive').textContent = `${d.inactive_total} pausados`;
  if (qs('#fxDashItems'))    qs('#fxDashItems').textContent    = d.items_total;

  const bars = qs('#fxCategoryBars');
  if (bars) {
    const max = Math.max(...(d.categories || []).map(x => Number(x.amount || 0)), 1);
    bars.innerHTML = (d.categories || []).length
      ? d.categories.map(x =>
          `<div class="fx-bar-row"><div><b>${escapeAttr(x.label)}</b><span>${brl(x.amount)}</span></div><i style="width:${Math.max(6, Number(x.amount || 0) / max * 100)}%"></i></div>`
        ).join('')
      : '<p class="empty-state">Nenhuma despesa ativa ainda.</p>';
  }

  const top = qs('#fxDashTopRecords');
  if (top) {
    top.innerHTML = (d.top_records || []).length
      ? d.top_records.map(x =>
          `<tr><td><b>${escapeAttr(x.title)}</b><p class="muted">${Number(x.items_count || 0)} item(ns)</p></td><td>${escapeAttr(x.method || '-')}</td><td>${Number(x.day_of_month)}</td><td class="tx-value ${x.kind}">${x.kind === 'saida' ? '- ' : ''}${brl(x.amount)}</td></tr>`
        ).join('')
      : '<tr><td colspan="4" class="muted">Nenhuma despesa ativa.</td></tr>';
  }
}
