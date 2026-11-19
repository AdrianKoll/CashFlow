/* CashFlow — Inicialização e binding de eventos globais */

window.currentPeriod = localStorage.getItem('cashPeriod') || 'today';
if (window.currentPeriod === 'all') window.currentPeriod = 'year';

function syncPeriodUI() {
  qsa('[data-period]').forEach(btn => btn.classList.toggle('active', btn.dataset.period === window.currentPeriod));
  const select = qs('#chartPeriod');
  if (select) select.value = window.currentPeriod;
  qsa('#pdfReportBtn, #pdfReportBtn2').forEach(a => {
    a.href = '/relatorios/pdf?period=' + encodeURIComponent(window.currentPeriod);
  });
}

async function setPeriod(period) {
  window.currentPeriod = period || 'today';
  localStorage.setItem('cashPeriod', window.currentPeriod);
  syncPeriodUI();
  await loadSummary();
  await loadTransactions();
}

/* ---- Drawer (sidebar mobile) ---- */
function bindDrawer() {
  const side = qs('.sidebar');
  const back = qs('#backdrop');
  side?.classList.remove('open');
  back?.classList.remove('show');
  document.body.classList.remove('drawer-open');
  let drawerLocked = false;

  function openDrawer() {
    if (drawerLocked) return;
    drawerLocked = true;
    requestAnimationFrame(() => {
      side?.classList.add('open');
      back?.classList.add('show');
      document.body.classList.add('drawer-open');
      setTimeout(() => { drawerLocked = false; }, 190);
    });
  }

  function closeDrawer() {
    if (drawerLocked) return;
    drawerLocked = true;
    requestAnimationFrame(() => {
      side?.classList.remove('open');
      back?.classList.remove('show');
      document.body.classList.remove('drawer-open');
      setTimeout(() => { drawerLocked = false; }, 190);
    });
  }

  function toggleDrawer() {
    side?.classList.contains('open') ? closeDrawer() : openDrawer();
  }

  qs('#drawerBtn')?.addEventListener('click', toggleDrawer);
  qs('#drawerBtn2')?.addEventListener('click', toggleDrawer);
  qs('#moreDrawerBtn')?.addEventListener('click', openDrawer);
  back?.addEventListener('click', closeDrawer);
  qsa('[data-close-drawer]').forEach(b => b.addEventListener('click', closeDrawer));
  qsa('.sidebar a').forEach(a => a.addEventListener('click', closeDrawer));
  qsa('.sidebar [data-open-modal]').forEach(b => b.addEventListener('click', closeDrawer));
}

/* ---- Main bindUI ---- */
function bindUI() {
  /* Modais de transação */
  qsa('[data-open-modal]').forEach(b => b.addEventListener('click', () => openModal(b.dataset.kind)));
  qsa('[data-close-modal]').forEach(b => b.addEventListener('click', closeModal));
  qs('#txForm')?.addEventListener('submit', submitTx);
  qs('#txModal')?.addEventListener('click', e => { if (e.target.id === 'txModal') closeModal(); });

  /* Formulário de registro fixo */
  qs('#fixedForm')?.addEventListener('submit', submitFixed);
  qs('#addFixedItemBtn')?.addEventListener('click', () => addFixedItem());
  qs('#cancelFixedEditBtn')?.addEventListener('click', resetFixedForm);
  qs('#generateFixedBtn')?.addEventListener('click', generateFixedNow);
  qs('#copyFixedBtn')?.addEventListener('click', copyFixedList);

  /* Filtros de registros fixos */
  qsa('#fixedSearch, #fixedTypeFilter, #fixedStatusFilter, #fixedPaymentFilter, #fixedSort').forEach(el =>
    el.addEventListener('input', () => { syncFixedStatusChips(); renderFixedRows(getFixedFilteredRows()); })
  );
  qsa('[data-fixed-status]').forEach(btn => btn.addEventListener('click', () => {
    if (qs('#fixedStatusFilter')) qs('#fixedStatusFilter').value = btn.dataset.fixedStatus || 'all';
    syncFixedStatusChips();
    renderFixedRows(getFixedFilteredRows());
  }));
  qs('#clearFixedFiltersBtn')?.addEventListener('click', clearFixedFilters);

  /* Produtos */
  qs('#productForm')?.addEventListener('submit', submitProduct);
  qs('#productSearch')?.addEventListener('input', renderProducts);
  qs('#builderProductSearch')?.addEventListener('input', renderBuilderProducts);
  qs('#cancelProductEditBtn')?.addEventListener('click', resetProductForm);

  /* Configurações */
  qs('#resetDataBtn')?.addEventListener('click', resetAllData);

  /* Tema */
  qs('#themeToggle')?.addEventListener('change', e => setTheme(!e.target.checked));
  qs('#mobileThemeBtn')?.addEventListener('click', () => setTheme(!document.body.classList.contains('light')));

  /* Período */
  qsa('[data-period]').forEach(btn => btn.addEventListener('click', () => setPeriod(btn.dataset.period)));
  qs('#chartPeriod')?.addEventListener('change', e => setPeriod(e.target.value));

  /* Drawer */
  bindDrawer();

  /* Redimensionamento: redrawing gráficos */
  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => loadSummary(), 180);
  }, { passive: true });

  /* Aplica tema e sincroniza período */
  setTheme(localStorage.getItem('cashTheme') === 'light');
  syncPeriodUI();
}

/* ---- Bootstrap ---- */
document.addEventListener('DOMContentLoaded', async () => {
  bindUI();

  await Promise.all([
    loadSummary(),
    loadTransactions(),
    loadFixedCategories(),
  ]);

  await loadFixedRecords();
  await loadProducts();
  await loadFixedDashboard();

  /* Auto-edição ao retornar da página de despesa mensal */
  if (qs('#fixedItemsList')) {
    const editId = localStorage.getItem('cashEditFixedId');
    if (editId) {
      localStorage.removeItem('cashEditFixedId');
      await loadFixedRecords();
      editFixed(editId);
    } else {
      addFixedItem();
    }
  }
});


/* ---- Sair da conta: POST com token CSRF (um link GET poderia ser acionado por terceiros) ---- */
document.addEventListener('click', event => {
  const link = event.target.closest('[data-logout]');
  if (!link) return;
  event.preventDefault();
  const form = document.createElement('form');
  form.method = 'post';
  form.action = '/logout';
  const token = document.querySelector('meta[name="csrf-token"]')?.content;
  if (token) {
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'csrf_token';
    input.value = token;
    form.appendChild(input);
  }
  document.body.appendChild(form);
  form.submit();
});
