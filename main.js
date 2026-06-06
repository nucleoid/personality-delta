const DIMS = [
  'directness', 'hedge_frequency', 'opinion_volunteering', 'pushback_resilience',
  'explanation_depth', 'risk_tolerance', 'emotional_register', 'conciseness'
];

const DIM_LABELS = {
  directness: 'Directness',
  hedge_frequency: 'Hedge Freq.',
  opinion_volunteering: 'Opinion Vol.',
  pushback_resilience: 'Pushback Res.',
  explanation_depth: 'Explain Depth',
  risk_tolerance: 'Risk Tol.',
  emotional_register: 'Emotional Reg.',
  conciseness: 'Conciseness'
};

const MODEL_NAMES = {
  '4.7': 'Opus 4.7',
  '4.8': 'Opus 4.8',
  'gpt55': 'GPT 5.5',
  'gpt54': 'GPT 5.4 Mini'
};

let DATA = null;
let activeKey = '4.7';
let activeDim = 'risk_tolerance';

async function init() {
  const resp = await fetch('assets/data.json');
  DATA = await resp.json();
  initBars();
  bindTabs();
  bindDimSelect();
  render();
}

function initBars() {
  document.querySelectorAll('.dim-fill').forEach(el => {
    const val = parseInt(el.dataset.value);
    setTimeout(() => { el.style.width = (val / 7 * 100) + '%'; }, 200);
  });
}

function bindTabs() {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
      });
      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');
      activeKey = tab.dataset.key;
      render();
    });
  });
}

function bindDimSelect() {
  const sel = document.getElementById('dimSelect');
  sel.addEventListener('change', () => {
    activeDim = sel.value;
    renderDrilldown();
  });
}

function render() {
  const comp = DATA[activeKey];
  const modelName = MODEL_NAMES[activeKey];

  document.getElementById('legendModelB').textContent = modelName;
  document.getElementById('thModelB').textContent = modelName;

  renderRadar(comp.summary);
  renderDeltaTable(comp.summary);
  renderDrilldown();
}

// ---- RADAR CHART ----

function renderRadar(summary) {
  const canvas = document.getElementById('radarChart');
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const size = 480;

  canvas.width = size * dpr;
  canvas.height = size * dpr;
  canvas.style.width = size + 'px';
  canvas.style.height = size + 'px';
  ctx.scale(dpr, dpr);

  ctx.clearRect(0, 0, size, size);

  const cx = size / 2;
  const cy = size / 2;
  const maxR = 180;
  const n = DIMS.length;
  const step = (2 * Math.PI) / n;
  const startAngle = -Math.PI / 2;

  // Grid rings
  for (let ring = 1; ring <= 7; ring++) {
    const r = (ring / 7) * maxR;
    ctx.beginPath();
    for (let i = 0; i <= n; i++) {
      const angle = startAngle + i * step;
      const x = cx + r * Math.cos(angle);
      const y = cy + r * Math.sin(angle);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
    const cs = getComputedStyle(document.documentElement);
    ctx.strokeStyle = ring === 4 ? cs.getPropertyValue('--radar-grid-mid').trim() : cs.getPropertyValue('--radar-grid').trim();
    ctx.lineWidth = ring === 4 ? 1.5 : 0.5;
    ctx.stroke();
  }

  // Axis lines + labels
  ctx.font = '11px Inter, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  for (let i = 0; i < n; i++) {
    const angle = startAngle + i * step;
    const x1 = cx + maxR * Math.cos(angle);
    const y1 = cy + maxR * Math.sin(angle);
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(x1, y1);
    ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--radar-axis').trim();
    ctx.lineWidth = 0.5;
    ctx.stroke();

    const lx = cx + (maxR + 28) * Math.cos(angle);
    const ly = cy + (maxR + 28) * Math.sin(angle);
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--radar-label').trim();
    ctx.fillText(DIM_LABELS[DIMS[i]], lx, ly);
  }

  const cs = getComputedStyle(document.documentElement);
  const colorA = cs.getPropertyValue('--accent-cyan').trim();
  const colorB = cs.getPropertyValue('--accent-pink').trim();

  // Model A polygon
  const aScores = DIMS.map(d => summary[d] ? summary[d].model_a_median : 4);
  drawPolygon(ctx, cx, cy, maxR, aScores, startAngle, step, hexToRgba(colorA, 0.15), hexToRgba(colorA, 0.8), 2);

  // Model B polygon
  const bScores = DIMS.map(d => summary[d] ? summary[d].model_b_median : 4);
  drawPolygon(ctx, cx, cy, maxR, bScores, startAngle, step, hexToRgba(colorB, 0.12), hexToRgba(colorB, 0.8), 2);

  // Score dots
  for (let i = 0; i < n; i++) {
    const angle = startAngle + i * step;
    const rA = (aScores[i] / 7) * maxR;
    const rB = (bScores[i] / 7) * maxR;

    drawDot(ctx, cx + rA * Math.cos(angle), cy + rA * Math.sin(angle), 4, colorA);
    drawDot(ctx, cx + rB * Math.cos(angle), cy + rB * Math.sin(angle), 4, colorB);
  }
}

function drawPolygon(ctx, cx, cy, maxR, scores, startAngle, step, fill, stroke, lineWidth) {
  const n = scores.length;
  ctx.beginPath();
  for (let i = 0; i <= n; i++) {
    const idx = i % n;
    const angle = startAngle + idx * step;
    const r = (scores[idx] / 7) * maxR;
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.strokeStyle = stroke;
  ctx.lineWidth = lineWidth;
  ctx.stroke();
}

function drawDot(ctx, x, y, r, color) {
  ctx.beginPath();
  ctx.arc(x, y, r, 0, 2 * Math.PI);
  ctx.fillStyle = color;
  ctx.fill();
  ctx.beginPath();
  ctx.arc(x, y, r + 3, 0, 2 * Math.PI);
  ctx.fillStyle = color.replace(')', ', 0.2)').replace('rgb', 'rgba');
  ctx.fill();
}

// ---- DELTA TABLE ----

function renderDeltaTable(summary) {
  const tbody = document.getElementById('deltaTableBody');
  tbody.innerHTML = '';

  for (const dim of DIMS) {
    const data = summary[dim];
    if (!data) continue;

    const delta = data.mean_delta;
    const absDelta = Math.abs(delta);
    let cls = 'delta-ok';
    if (absDelta >= 1.0) cls = 'delta-significant';
    else if (absDelta >= 0.5) cls = 'delta-moderate';

    const sign = delta > 0 ? '+' : '';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="dim-cell">${DIM_LABELS[dim]}</td>
      <td class="score-cell">${data.model_a_median}</td>
      <td class="score-cell">${data.model_b_median}</td>
      <td class="delta-cell ${cls}">${sign}${delta.toFixed(1)}</td>
    `;
    tbody.appendChild(tr);
  }
}

// ---- DRILLDOWN ----

function renderDrilldown() {
  const comp = DATA[activeKey];
  const grid = document.getElementById('promptGrid');
  grid.innerHTML = '';

  for (const ps of comp.prompt_scores) {
    const dimData = ps.dimensions[activeDim];
    const cell = document.createElement('div');
    cell.className = 'prompt-cell';

    if (!dimData) {
      cell.classList.add('na');
      cell.innerHTML = `
        <span class="prompt-id">${ps.prompt_id}</span>
        <span class="prompt-scores" style="color: var(--text-muted)">n/a</span>
      `;
    } else {
      const d = dimData.delta;
      const ad = Math.abs(d);
      if (ad >= 2) cell.classList.add('sig');
      else if (ad >= 1) cell.classList.add('mod');
      else cell.classList.add('ok');

      const sign = d > 0 ? '+' : '';
      cell.innerHTML = `
        <span class="prompt-id">${ps.prompt_id}</span>
        <div class="prompt-scores">
          <span class="prompt-a">${dimData.a}</span>
          <span class="prompt-arrow">&rarr;</span>
          <span class="prompt-b">${dimData.b}</span>
          <span class="prompt-delta">${sign}${d}</span>
        </div>
      `;
    }
    grid.appendChild(cell);
  }
}

function hexToRgba(hex, alpha) {
  hex = hex.replace('#', '');
  if (hex.length === 3) hex = hex.split('').map(c => c + c).join('');
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function initThemeToggle() {
  const btn = document.getElementById('themeToggle');
  const saved = localStorage.getItem('pd-theme');
  if (saved === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
    btn.innerHTML = '&#9788;';
  }
  btn.addEventListener('click', () => {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    if (isDark) {
      document.documentElement.removeAttribute('data-theme');
      btn.innerHTML = '&#9790;';
      localStorage.setItem('pd-theme', 'light');
    } else {
      document.documentElement.setAttribute('data-theme', 'dark');
      btn.innerHTML = '&#9788;';
      localStorage.setItem('pd-theme', 'dark');
    }
    render();
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initThemeToggle();
  init();
});
