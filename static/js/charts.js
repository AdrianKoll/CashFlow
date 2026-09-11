/* CashFlow — Renderização de gráficos (Canvas 2D) */

function cssVar(name) {
  return getComputedStyle(document.body).getPropertyValue(name).trim();
}

function fitCanvas(canvas) {
  const rect = canvas.getBoundingClientRect();
  const dpr  = window.devicePixelRatio || 1;
  canvas.width  = Math.max(1, Math.floor(rect.width  * dpr));
  canvas.height = Math.max(1, Math.floor(rect.height * dpr));
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, w: rect.width, h: rect.height };
}

function drawCashChart(canvas, chart) {
  if (!canvas || !chart) return;
  const { ctx, w, h } = fitCanvas(canvas);
  ctx.clearRect(0, 0, w, h);

  const pad = { l: 34, r: 12, t: 18, b: 30 };
  const values = [...chart.entradas, ...chart.saidas, ...chart.saldo, 0];
  const min    = Math.min(...values);
  const max    = Math.max(...values);
  const range  = (max - min) || 1;
  const plotW  = w - pad.l - pad.r;
  const plotH  = h - pad.t - pad.b;

  const x = i => pad.l + (plotW * i / Math.max(1, chart.labels.length - 1));
  const y = v => pad.t + plotH - ((v - min) / range) * plotH;

  /* Grid lines */
  ctx.strokeStyle = 'rgba(143,155,176,.16)';
  ctx.lineWidth = 1;
  for (let i = 0; i < 4; i++) {
    const gy = pad.t + (plotH / 3) * i;
    ctx.beginPath();
    ctx.moveTo(pad.l, gy);
    ctx.lineTo(w - pad.r, gy);
    ctx.stroke();
  }

  /* Bars */
  const barW = Math.min(18, plotW / Math.max(8, chart.labels.length * 3));

  chart.labels.forEach((label, i) => {
    const base = y(0);
    const xi   = x(i);
    const ent  = chart.entradas[i] || 0;
    const sai  = chart.saidas[i]  || 0;

    ctx.fillStyle = 'rgba(32,213,131,.75)';
    ctx.fillRect(xi - barW - 2, Math.min(y(ent), base), barW, Math.abs(base - y(ent)) || 2);

    ctx.fillStyle = 'rgba(255,77,85,.78)';
    ctx.fillRect(xi + 2, Math.min(y(sai), base), barW, Math.abs(base - y(sai)) || 2);

    ctx.fillStyle = '#8f9bb0';
    ctx.font = '10px system-ui';
    ctx.textAlign = 'center';
    ctx.fillText(label, xi, h - 9);
  });

  /* Saldo line */
  const blue = '#5361ff';
  ctx.strokeStyle = blue;
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  chart.saldo.forEach((v, i) => {
    const xi = x(i), yi = y(v);
    i ? ctx.lineTo(xi, yi) : ctx.moveTo(xi, yi);
  });
  ctx.stroke();

  /* Saldo dots */
  chart.saldo.forEach((v, i) => {
    ctx.fillStyle = blue;
    ctx.beginPath();
    ctx.arc(x(i), y(v), 3, 0, Math.PI * 2);
    ctx.fill();
  });
}

function drawDonut(canvas, distribution) {
  if (!canvas || !distribution) return;
  const { ctx, w, h } = fitCanvas(canvas);
  ctx.clearRect(0, 0, w, h);

  const cx = w / 2, cy = h / 2;
  const r  = Math.min(w, h) * .38;
  const inner = r * .62;

  const vals  = distribution.map(x => Math.max(0, Number(x.value) || 0));
  const total = vals.reduce((a, b) => a + b, 0) || 1;
  const colors = ['#20d583', '#5361ff', '#ff4d55'];

  let start = -Math.PI / 2;
  vals.forEach((val, i) => {
    const ang = (val / total) * Math.PI * 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, r, start, start + ang);
    ctx.closePath();
    ctx.fillStyle = colors[i % colors.length];
    ctx.fill();
    start += ang;
  });

  /* Hole */
  ctx.globalCompositeOperation = 'destination-out';
  ctx.beginPath();
  ctx.arc(cx, cy, inner, 0, Math.PI * 2);
  ctx.fill();
  ctx.globalCompositeOperation = 'source-over';

  /* Label */
  ctx.fillStyle = cssVar('--text') || '#fff';
  ctx.font = '700 18px system-ui';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('CashFlow', cx, cy);
}
