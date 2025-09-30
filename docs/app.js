const State = { idle: 'idle', querying: 'querying', error: 'error' };
let state = State.idle;
let configError = '';
let config = { backend_base_url: typeof window !== 'undefined' ? (window.__BACKEND_BASE_URL || '') : '' };

const STORAGE_KEY = 'demoFreeUses';
const INITIAL_USES = 5;

const els = {
  messages: document.getElementById('messages'),
  input: document.getElementById('input'),
  ask: document.getElementById('ask'),
  reset: document.getElementById('reset'),
  usesBadge: document.getElementById('uses-badge'),
  usesCount: document.getElementById('uses-count'),
  pillsRow: document.getElementById('pills-row'),
  announcer: document.getElementById('a11y-announcer'),
};

function setConfigError(message){
  configError = message;
  console.warn('[config]', message);
}

async function loadConfig(){
  if (config.backend_base_url){
    return;
  }
  try{
    const res = await fetch('config.json', { cache: 'no-store' });
    if (!res.ok){
      throw new Error(`config.json status ${res.status}`);
    }
    const text = await res.text();
    try{
      const json = JSON.parse(text);
      if (json && typeof json.backend_base_url === 'string' && json.backend_base_url){
        config.backend_base_url = json.backend_base_url;
        configError = '';
        return;
      }
      throw new Error('backend_base_url missing in config.json');
    } catch(e){
      throw new Error(`config.json parse error: ${e.message}`);
    }
  } catch(err){
    setConfigError(err.message || 'Failed to load config.json');
  }
}

function getRemainingUses(){
  const raw = localStorage.getItem(STORAGE_KEY);
  const n = raw == null ? NaN : Number(raw);
  if (!Number.isFinite(n) || n < 0){
    localStorage.setItem(STORAGE_KEY, String(INITIAL_USES));
    return INITIAL_USES;
  }
  return n;
}

function setRemainingUses(n){
  const v = Math.max(0, Math.floor(Number(n)) || 0);
  localStorage.setItem(STORAGE_KEY, String(v));
}

function updateUsesUI(){
  const remaining = getRemainingUses();
  els.usesCount.textContent = String(remaining);
  const out = remaining <= 0;
  els.ask.disabled = out || state === State.querying;
  els.ask.title = out ? 'Out of free uses for this browser.' : '';
}

function announceUses(){
  els.announcer.textContent = `Free uses remaining: ${getRemainingUses()}`;
}

function setState(next){
  state = next;
  if (state === State.querying){
    els.ask.disabled = true;
    els.input.setAttribute('aria-busy','true');
  } else {
    els.input.removeAttribute('aria-busy');
    updateUsesUI();
  }
}

function renderThinkingProcess(parent, thinking){
  if (!thinking || thinking.trim() === '') return;
  
  const details = document.createElement('details');
  details.className = 'thinking-details';
  details.open = false; // Collapsed by default
  
  const summary = document.createElement('summary');
  summary.textContent = '🤔 Agent Thinking Process';
  summary.style.cursor = 'pointer';
  summary.style.color = '#6b7280';
  summary.style.fontSize = '0.9em';
  summary.style.marginBottom = '8px';
  
  const content = document.createElement('pre');
  content.style.fontSize = '0.85em';
  content.style.color = '#9da7b3';
  content.style.backgroundColor = '#161b22';
  content.style.padding = '12px';
  content.style.borderRadius = '6px';
  content.style.overflowX = 'auto';
  content.style.marginTop = '8px';
  content.textContent = thinking;
  
  details.appendChild(summary);
  details.appendChild(content);
  parent.appendChild(details);
}

function renderSQLCommands(parent, sqlArray){
  if (!sqlArray || sqlArray.length === 0) return;
  
  const details = document.createElement('details');
  details.className = 'sql-details';
  details.open = true; // Expanded by default to show SQL
  
  const summary = document.createElement('summary');
  summary.textContent = `⚡ SQL Commands (${sqlArray.length})`;
  summary.style.cursor = 'pointer';
  summary.style.color = '#58a6ff';
  summary.style.fontSize = '0.9em';
  summary.style.marginBottom = '8px';
  summary.style.fontWeight = '600';
  
  const container = document.createElement('div');
  container.style.marginTop = '8px';
  
  sqlArray.forEach((item, idx) => {
    const wrapper = document.createElement('div');
    wrapper.style.marginBottom = '12px';
    
    const label = document.createElement('div');
    label.textContent = `Tool: ${item.tool || 'unknown'}`;
    label.style.fontSize = '0.8em';
    label.style.color = '#6b7280';
    label.style.marginBottom = '4px';
    
    const pre = document.createElement('pre');
    pre.style.fontSize = '0.85em';
    pre.style.color = '#c9d1d9';
    pre.style.backgroundColor = '#0d1117';
    pre.style.padding = '12px';
    pre.style.borderRadius = '6px';
    pre.style.borderLeft = '3px solid #58a6ff';
    pre.style.overflowX = 'auto';
    pre.textContent = item.sql || 'No SQL captured';
    
    wrapper.appendChild(label);
    wrapper.appendChild(pre);
    container.appendChild(wrapper);
  });
  
  details.appendChild(summary);
  details.appendChild(container);
  parent.appendChild(details);
}

function addMessage(role, text){
  const div = document.createElement('div');
  div.className = `message ${role}`;
  const badge = document.createElement('span');
  badge.className = 'role-badge';
  badge.textContent = role === 'user' ? 'You' : 'Assistant';
  const body = document.createElement('div');
  body.className = 'message-text';
  body.textContent = text;
  div.appendChild(badge);
  div.appendChild(body);
  els.messages.appendChild(div);
  els.messages.scrollTop = els.messages.scrollHeight;
  return div;
}

function joinUrl(base, path){
  if (!base) return path;
  return `${base.replace(/\/$/, '')}${path.startsWith('/') ? '' : '/'}${path}`;
}

function toCSVFromRows(rows){
  if (!Array.isArray(rows) || rows.length === 0) return '';
  const headers = Array.from(rows.reduce((set, r) => {
    Object.keys(r || {}).forEach(k => set.add(k));
    return set;
  }, new Set()));
  const esc = (v) => {
    if (v == null) return '';
    const s = String(v);
    if (s.includes('"') || s.includes(',') || s.includes('\n')){
      return '"' + s.replaceAll('"','""') + '"';
    }
    return s;
  };
  const lines = [headers.join(',')];
  for (const row of rows){
    lines.push(headers.map(h => esc(row[h])).join(','));
  }
  return lines.join('\n');
}

function renderTable(parent, rows){
  if (!Array.isArray(rows) || rows.length === 0){
    const small = document.createElement('small');
    small.className = 'muted';
    small.textContent = 'No rows.';
    parent.appendChild(small);
    return;
  }
  const headers = Array.from(rows.reduce((set, r) => { Object.keys(r || {}).forEach(k => set.add(k)); return set; }, new Set()));
  const wrap = document.createElement('div');
  wrap.className = 'table-wrap';
  const table = document.createElement('table');
  const thead = document.createElement('thead');
  const trh = document.createElement('tr');
  for (const h of headers){
    const th = document.createElement('th');
    th.textContent = h;
    trh.appendChild(th);
  }
  thead.appendChild(trh);
  table.appendChild(thead);
  const tbody = document.createElement('tbody');
  for (const r of rows){
    const tr = document.createElement('tr');
    for (const h of headers){
      const td = document.createElement('td');
      const val = r[h];
      td.textContent = val == null ? '' : String(val);
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  wrap.appendChild(table);
  parent.appendChild(wrap);
}

function buildChartDatasetFromSpec(data, spec){
  const xKey = spec.x;
  const yKey = spec.y;
  const labels = [];
  const values = [];
  for (const row of (data || [])){
    labels.push(row?.[xKey]);
    values.push(Number(row?.[yKey] ?? 0));
  }
  return { labels, datasets: [{ label: yKey || 'value', data: values }] };
}

function computeHistogram(data, spec){
  const xKey = spec.x;
  const nums = (data || []).map(r => Number(r?.[xKey])).filter(n => Number.isFinite(n));
  if (nums.length === 0){
    return { labels: [], datasets: [{ label: 'count', data: [] }] };
  }
  const bins = Math.max(1, Number(spec.bins) || 10);
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const width = (max - min) / bins || 1;
  const edges = Array.from({length: bins}, (_, i) => min + i * width);
  const counts = new Array(bins).fill(0);
  for (const v of nums){
    let idx = Math.floor((v - min) / width);
    if (idx >= bins) idx = bins - 1;
    if (idx < 0) idx = 0;
    counts[idx]++;
  }
  const labels = edges.map((e, i) => `${Math.round(e).toLocaleString()}–${Math.round(e + width).toLocaleString()}`);
  return { labels, datasets: [{ label: 'count', data: counts }] };
}

function renderChart(parent, data, viz){
  const canvas = document.createElement('canvas');
  parent.appendChild(canvas);
  let cfgData;
  if (viz.type === 'histogram'){
    cfgData = computeHistogram(data, viz);
  } else {
    cfgData = buildChartDatasetFromSpec(data, viz);
  }
  const type = viz.type === 'histogram' ? 'bar' : viz.type;
  // eslint-disable-next-line no-undef
  new Chart(canvas.getContext('2d'), {
    type,
    data: cfgData,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#e6edf3' } },
        tooltip: { intersect: false, mode: 'index' },
      },
      scales: {
        x: { ticks: { color: '#9da7b3' }, grid: { color: '#1f2328' } },
        y: { ticks: { color: '#9da7b3' }, grid: { color: '#1f2328' } }
      }
    }
  });
}

function attachCopyCSV(btn, source){
  btn.addEventListener('click', async () => {
    try{
      await navigator.clipboard.writeText(source());
      btn.textContent = 'Copied';
      setTimeout(() => { btn.textContent = 'Copy CSV'; }, 1200);
    } catch{}
  });
}

function renderVizBelow(messageEl, data, viz){
  if (!viz || !data) return;
  const wrap = document.createElement('div');
  wrap.className = 'viz';
  const header = document.createElement('div');
  header.className = 'viz-header';
  const title = document.createElement('strong');
  title.textContent = viz.type === 'table' ? 'Table' : viz.type.toUpperCase();
  const copy = document.createElement('button');
  copy.className = 'copy-btn';
  copy.type = 'button';
  copy.textContent = 'Copy CSV';
  header.appendChild(title);
  header.appendChild(copy);
  wrap.appendChild(header);

  if (viz.type === 'table'){
    renderTable(wrap, data);
    attachCopyCSV(copy, () => toCSVFromRows(data));
  } else if (['bar','line','pie','histogram'].includes(viz.type)){
    const csv = () => {
      if (viz.type === 'histogram'){
        const agg = computeHistogram(data, viz);
        const rows = agg.labels.map((label, i) => ({ bin: label, count: agg.datasets[0].data[i] || 0 }));
        return toCSVFromRows(rows);
      }
      const agg = buildChartDatasetFromSpec(data, viz);
      const rows = agg.labels.map((label, i) => ({ [viz.x || 'x']: label, [viz.y || 'y']: agg.datasets[0].data[i] || 0 }));
      return toCSVFromRows(rows);
    };
    renderChart(wrap, data, viz);
    wrap.style.height = '280px';
    attachCopyCSV(copy, csv);
  }

  messageEl.appendChild(wrap);
}

// Default mode for manual questions when no pill is used
function currentMode(){ return 'analyst'; }

async function sendChat({ overrideMode = null, overrideViz = null } = {}){
  const text = els.input.value.trim();
  if (!text) return;
  if (getRemainingUses() <= 0){
    updateUsesUI();
    return;
  }
  if (!config.backend_base_url){
    setState(State.error);
    addMessage('assistant', 'Setup incomplete: backend URL not configured. Please redeploy the site with docs/config.json or inline backend_base_url.');
    return;
  }
  const mode = overrideMode || currentMode();
  const viz = overrideViz; // may be null

  addMessage('user', text);
  els.input.value='';
  setState(State.querying);

  const payload = { mode, question: text, viz: viz || null, table: 'RIGHTMOVE_TRANSFORMED' };
  const url = joinUrl(config.backend_base_url, '/api/chat');

  try{
    const res = await fetch(url, {
      method:'POST',
      headers:{ 'Content-Type':'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    if (!data) throw new Error('Empty');
    
    const msg = addMessage('assistant', data.answer || '');
    
    // Show SQL commands if available (above the answer for visibility)
    if (data.sql && data.sql.length > 0) {
      renderSQLCommands(msg, data.sql);
    }
    
    // Show thinking process if available
    if (data.thinking) {
      renderThinkingProcess(msg, data.thinking);
    }
    
    // Render visualization if available
    if (data.viz && data.data) renderVizBelow(msg, data.data, data.viz);
    
    // success → decrement free uses
    setRemainingUses(getRemainingUses() - 1);
    updateUsesUI();
    announceUses();
    setState(State.idle);
  } catch(err){
    console.error(err);
    addMessage('assistant','Service error. Try again.');
    setState(State.error);
  }
}

function resetTranscript(){
  els.messages.innerHTML='';
  setState(State.idle);
}

function handlePrepopClick(e){
  const btn = e.target.closest('.pill');
  if (!btn) return;
  const question = btn.textContent.trim();
  const mode = btn.getAttribute('data-mode');
  const viz = btn.getAttribute('data-viz');
  els.input.value = question;
  // brief active style
  btn.classList.add('active');
  setTimeout(() => btn.classList.remove('active'), 900);
  // Auto-send
  sendChat({ overrideMode: mode, overrideViz: viz });
}

window.addEventListener('DOMContentLoaded', async () => {
  await loadConfig();

  // seed free uses if needed
  setRemainingUses(getRemainingUses());
  updateUsesUI();
  announceUses();

  // developer-only: reseed quota via ?debug=1
  const url = new URL(window.location.href);
  if (url.searchParams.get('debug') === '1'){
    setRemainingUses(INITIAL_USES);
    updateUsesUI();
    announceUses();
  }

  els.ask.addEventListener('click', () => sendChat());
  els.input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey){
      e.preventDefault();
      sendChat();
    }
  });
  els.reset.addEventListener('click', resetTranscript);
  if (els.pillsRow) els.pillsRow.addEventListener('click', handlePrepopClick);
});


