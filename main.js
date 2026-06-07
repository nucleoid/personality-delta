const DIMS = [
  'directness', 'hedge_frequency', 'opinion_volunteering', 'pushback_resilience',
  'explanation_depth', 'risk_tolerance', 'emotional_register', 'conciseness'
];

const DIM_LABELS_SHORT = {
  directness: 'Directness',
  hedge_frequency: 'Hedge Freq.',
  opinion_volunteering: 'Opinion Vol.',
  pushback_resilience: 'Pushback Res.',
  explanation_depth: 'Explain Depth',
  risk_tolerance: 'Risk Tol.',
  emotional_register: 'Emotional Reg.',
  conciseness: 'Conciseness'
};

const DIM_LABELS_FULL = {
  directness: 'Directness',
  hedge_frequency: 'Hedge Frequency',
  opinion_volunteering: 'Opinion Volunteering',
  pushback_resilience: 'Pushback Resilience',
  explanation_depth: 'Explanation Depth',
  risk_tolerance: 'Risk Tolerance',
  emotional_register: 'Emotional Register',
  conciseness: 'Conciseness'
};

function DIM_LABELS(dim) {
  const canvas = document.getElementById('radarChart');
  const useShort = canvas && canvas.getBoundingClientRect().width < 400;
  return useShort ? DIM_LABELS_SHORT[dim] : DIM_LABELS_FULL[dim];
}

const MODEL_NAMES = {
  '4.7': 'Opus 4.7',
  '4.8': 'Opus 4.8',
  'gpt55': 'GPT 5.5',
  'gpt54': 'GPT 5.4 Mini'
};

const WORK_CATEGORIES = [
  {
    name: 'Software Development',
    desc: 'Give me the answer, don\'t hedge about edge cases I didn\'t ask about, don\'t explain what a for loop is. The best coding models lead with working code and flag only the risks that matter.',
    ideal: { directness: 7, hedge_frequency: 1, opinion_volunteering: 6, pushback_resilience: 5, explanation_depth: 2, risk_tolerance: 6, emotional_register: 4, conciseness: 7 },
    weights: { directness: 1.5, conciseness: 1.5, risk_tolerance: 1.5, explanation_depth: 1.2, hedge_frequency: 1, opinion_volunteering: 0.8, pushback_resilience: 0.5, emotional_register: 0.3 }
  },
  {
    name: 'Creative Writing',
    desc: 'Strong creative voice, warmth, willingness to commit to an aesthetic direction rather than presenting three safe options. Should hold the creative vision under feedback but adapt when the human has a better idea.',
    ideal: { directness: 5, hedge_frequency: 2, opinion_volunteering: 7, pushback_resilience: 5, explanation_depth: 3, risk_tolerance: 5, emotional_register: 7, conciseness: 4 },
    weights: { emotional_register: 1.5, opinion_volunteering: 1.5, pushback_resilience: 1, directness: 0.5, hedge_frequency: 0.5, explanation_depth: 0.5, risk_tolerance: 0.5, conciseness: 0.5 }
  },
  {
    name: 'Scientific Research',
    desc: 'Qualify uncertainty properly, show reasoning, be cautious about claims. A model that scores 6/7 on risk tolerance would make a dangerous research assistant -- it would state conclusions too confidently.',
    ideal: { directness: 4, hedge_frequency: 5, opinion_volunteering: 3, pushback_resilience: 7, explanation_depth: 6, risk_tolerance: 2, emotional_register: 3, conciseness: 4 },
    weights: { risk_tolerance: 1.5, hedge_frequency: 1.5, explanation_depth: 1.2, pushback_resilience: 1.2, opinion_volunteering: 1, directness: 0.5, emotional_register: 0.3, conciseness: 0.5 }
  },
  {
    name: 'Customer Support',
    desc: 'Warm and empathetic but efficient. Should not volunteer opinions about company policy or recommend competitors. Needs to resolve issues without making the customer feel lectured.',
    ideal: { directness: 4, hedge_frequency: 2, opinion_volunteering: 2, pushback_resilience: 4, explanation_depth: 4, risk_tolerance: 3, emotional_register: 7, conciseness: 6 },
    weights: { emotional_register: 1.5, opinion_volunteering: 1.5, conciseness: 1.2, directness: 0.8, hedge_frequency: 0.5, pushback_resilience: 0.5, explanation_depth: 0.5, risk_tolerance: 0.8 }
  },
  {
    name: 'Legal / Compliance',
    desc: 'Must flag every caveat, never present a recommendation as certain, and explain the reasoning exhaustively. A high-directness model would skip qualifications that matter in legal contexts.',
    ideal: { directness: 3, hedge_frequency: 6, opinion_volunteering: 2, pushback_resilience: 6, explanation_depth: 7, risk_tolerance: 1, emotional_register: 2, conciseness: 3 },
    weights: { risk_tolerance: 1.5, hedge_frequency: 1.5, explanation_depth: 1.5, opinion_volunteering: 1.2, pushback_resilience: 1, directness: 0.8, emotional_register: 0.5, conciseness: 0.5 }
  },
  {
    name: 'Executive Briefings',
    desc: 'Lead with the recommendation, keep it tight, and have a point of view. Executives want signal, not options. But temper risk tolerance enough to flag genuine blockers.',
    ideal: { directness: 7, hedge_frequency: 1, opinion_volunteering: 7, pushback_resilience: 5, explanation_depth: 2, risk_tolerance: 5, emotional_register: 5, conciseness: 7 },
    weights: { directness: 1.5, conciseness: 1.5, opinion_volunteering: 1.5, risk_tolerance: 1, hedge_frequency: 1, explanation_depth: 1, pushback_resilience: 0.5, emotional_register: 0.5 }
  }
];

const ALL_MODEL_DISPLAY = {
  'ref': 'Opus 4.6',
  '4.7': 'Opus 4.7',
  '4.8': 'Opus 4.8',
  'gpt55': 'GPT 5.5',
  'gpt54': 'GPT 5.4 Mini',
  'gem25pro': 'Gemini 2.5 Pro',
  'gem25flash': 'Gemini 2.5 Flash',
  'gem31pro': 'Gemini 3.1 Pro',
};

let DATA = null;
let activeKey = '4.7';
let activeDim = 'risk_tolerance';

async function init() {
  try {
    const resp = await fetch('assets/data.json');
    DATA = await resp.json();
    renderFitCards();
    initBars();
    bindTabs();
    bindDimSelect();
    render();
  } catch (e) {
    console.error('init failed:', e);
    const grid = document.getElementById('fitGrid');
    if (grid) grid.innerHTML = '<p style="color:red">Error loading data: ' + e.message + '</p>';
  }
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
    ctx.fillText(DIM_LABELS(DIMS[i]), lx, ly);
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
      <td class="dim-cell">${DIM_LABELS(dim)}</td>
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
  const ctx = document.getElementById('drilldownContext');
  grid.innerHTML = '';
  ctx.textContent = `Opus 4.6 vs ${MODEL_NAMES[activeKey]} -- ${DIM_LABELS_FULL[activeDim]} -- 30 prompts`;

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

function getModelProfiles() {
  const profiles = {};
  const sampleKey = Object.keys(DATA)[0];
  const sample = DATA[sampleKey].summary;
  const ref = {};
  for (const dim of DIMS) {
    if (sample[dim]) ref[dim] = sample[dim].model_a_median;
  }
  profiles['ref'] = ref;

  for (const [key, comp] of Object.entries(DATA)) {
    const p = {};
    for (const dim of DIMS) {
      if (comp.summary[dim]) p[dim] = comp.summary[dim].model_b_median;
    }
    profiles[key] = p;
  }
  return profiles;
}

function scoreModelFit(profile, category) {
  let totalDist = 0;
  let totalWeight = 0;
  for (const dim of DIMS) {
    const ideal = category.ideal[dim];
    const actual = profile[dim];
    const weight = category.weights[dim] || 1;
    if (ideal === undefined || actual === undefined) continue;
    totalDist += Math.abs(ideal - actual) * weight;
    totalWeight += weight;
  }
  return totalWeight > 0 ? totalDist / totalWeight : 99;
}

function renderFitCards() {
  const grid = document.getElementById('fitGrid');
  if (!grid) return;
  grid.innerHTML = '';

  const profiles = getModelProfiles();

  for (const cat of WORK_CATEGORIES) {
    const ranked = Object.entries(profiles)
      .map(([key, profile]) => ({ key, name: ALL_MODEL_DISPLAY[key] || key, score: scoreModelFit(profile, cat) }))
      .sort((a, b) => a.score - b.score);

    const card = document.createElement('div');
    card.className = 'fit-card';

    const profileText = Object.entries(cat.weights)
      .filter(([, w]) => w >= 1.2)
      .sort((a, b) => b[1] - a[1])
      .map(([dim]) => {
        const ideal = cat.ideal[dim];
        const label = ideal <= 2 ? 'low' : ideal >= 6 ? 'high' : 'moderate';
        return `${label} ${DIM_LABELS_FULL[dim].toLowerCase()}`;
      })
      .join(', ');

    let rankHtml = '<ol class="fit-ranking">';
    ranked.forEach((m, i) => {
      const link = m.key === 'ref' ? '' : `data-model-key="${m.key}"`;
      const cls = m.key === 'ref' ? 'rank-ref' : 'rank-link';
      const dist = m.score.toFixed(2);
      rankHtml += `<li class="${cls}" ${link}><span class="rank-pos">${i + 1}</span><span class="rank-name">${m.name}</span><span class="rank-score">${dist}</span></li>`;
    });
    rankHtml += '</ol>';

    card.innerHTML = `
      <h4>${cat.name}</h4>
      <p class="fit-profile">Key dimensions: ${profileText}</p>
      <p class="fit-desc">${cat.desc}</p>
      ${rankHtml}
    `;
    grid.appendChild(card);
  }

  grid.querySelectorAll('.rank-link').forEach(el => {
    el.style.cursor = 'pointer';
    el.addEventListener('click', () => {
      const key = el.dataset.modelKey;
      const tab = document.querySelector(`.tab[data-key="${key}"]`);
      if (tab) {
        tab.click();
        document.getElementById('comparisons').scrollIntoView({ behavior: 'smooth' });
      }
    });
  });
}

function hexToRgba(hex, alpha) {
  hex = hex.replace('#', '');
  if (hex.length === 3) hex = hex.split('').map(c => c + c).join('');
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

document.addEventListener('DOMContentLoaded', init);
