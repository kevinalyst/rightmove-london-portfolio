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
  
  // Clear existing content for progressive updates
  parent.innerHTML = '';
  
  const details = document.createElement('details');
  details.className = 'sql-details';
  details.open = false; // Collapsed by default after answer shown
  
  const summary = document.createElement('summary');
  summary.textContent = `⚡ Cortex Analyst Queries (${sqlArray.length})`;
  summary.style.cursor = 'pointer';
  summary.style.color = '#58a6ff';
  summary.style.fontSize = '0.9em';
  summary.style.marginBottom = '8px';
  summary.style.fontWeight = '600';
  
  const container = document.createElement('div');
  container.style.marginTop = '8px';
  
  const intro = document.createElement('div');
  intro.style.fontSize = '0.85em';
  intro.style.color = '#6b7280';
  intro.style.marginBottom = '12px';
  intro.textContent = 'The agent used these queries to analyze your data:';
  container.appendChild(intro);
  
  sqlArray.forEach((item, idx) => {
    const wrapper = document.createElement('div');
    wrapper.style.marginBottom = '16px';
    
    const header = document.createElement('div');
    header.style.display = 'flex';
    header.style.justifyContent = 'space-between';
    header.style.alignItems = 'center';
    header.style.marginBottom = '6px';
    
    const label = document.createElement('div');
    const toolName = item.tool || 'analyst';
    const typeLabel = item.type === 'query' ? 'Natural Language Query → SQL' : 
                      item.type === 'generated' ? 'Generated SQL' :
                      item.type === 'executed' ? 'Executed SQL' : 'SQL';
    label.textContent = `${typeLabel} (${toolName})`;
    label.style.fontSize = '0.8em';
    label.style.color = '#6b7280';
    
    const badge = document.createElement('span');
    badge.textContent = `Query ${idx + 1}`;
    badge.style.fontSize = '0.75em';
    badge.style.color = '#58a6ff';
    badge.style.padding = '2px 8px';
    badge.style.backgroundColor = 'rgba(88, 166, 255, 0.1)';
    badge.style.borderRadius = '12px';
    
    header.appendChild(label);
    header.appendChild(badge);
    
    const pre = document.createElement('pre');
    pre.style.fontSize = '0.85em';
    pre.style.color = '#c9d1d9';
    pre.style.backgroundColor = '#0d1117';
    pre.style.padding = '12px';
    pre.style.borderRadius = '6px';
    pre.style.borderLeft = '3px solid #58a6ff';
    pre.style.overflowX = 'auto';
    pre.style.whiteSpace = 'pre-wrap';
    pre.style.wordBreak = 'break-word';
    pre.textContent = item.sql || 'No query captured';
    
    wrapper.appendChild(header);
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

// Render Vega-Lite chart spec (native Cortex Agent format)
function renderVegaChart(container, vegaLiteSpec) {
  // Clear container
  container.innerHTML = '';
  
  // Create wrapper for Vega chart
  const wrapper = document.createElement('div');
  wrapper.className = 'vega-chart-wrapper';
  wrapper.style.width = '100%';
  wrapper.style.minHeight = '400px';
  wrapper.style.backgroundColor = '#0d1117';
  wrapper.style.padding = '16px';
  wrapper.style.borderRadius = '8px';
  wrapper.style.border = '1px solid #1f2328';
  container.appendChild(wrapper);
  
  // Configure Vega-Embed options for dark theme
  const embedOptions = {
    theme: 'dark',
    actions: {
      export: { svg: true, png: true },
      source: false,
      compiled: false,
      editor: false
    },
    config: {
      background: '#0d1117',
      axis: {
        domainColor: '#2d333b',
        gridColor: '#1f2328',
        tickColor: '#2d333b',
        labelColor: '#9da7b3',
        titleColor: '#e6edf3'
      },
      legend: {
        labelColor: '#9da7b3',
        titleColor: '#e6edf3'
      },
      title: {
        color: '#e6edf3'
      }
    }
  };
  
  // Render Vega-Lite chart
  // eslint-disable-next-line no-undef
  vegaEmbed(wrapper, vegaLiteSpec, embedOptions)
    .then(result => {
      console.log('[Vega] Chart rendered successfully');
    })
    .catch(error => {
      console.error('[Vega] Rendering error:', error);
      wrapper.innerHTML = '<p style="color: #ff6b6b;">Chart rendering failed. See console for details.</p>';
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

// Render Vega-Lite visualization from Cortex Agent chart spec
function renderVizBelow(messageEl, vegaSpec){
  if (!vegaSpec) return;
  
  const wrap = document.createElement('div');
  wrap.className = 'viz';
  wrap.style.marginTop = '16px';
  
  const header = document.createElement('div');
  header.className = 'viz-header';
  header.style.display = 'flex';
  header.style.justifyContent = 'space-between';
  header.style.alignItems = 'center';
  header.style.marginBottom = '12px';
  
  const title = document.createElement('strong');
  title.textContent = vegaSpec.title || '📊 Visualization';
  title.style.color = '#58a6ff';
  title.style.fontSize = '1.1em';
  
  header.appendChild(title);
  wrap.appendChild(header);

  // Render the Vega-Lite chart
  renderVegaChart(wrap, vegaSpec);

  messageEl.appendChild(wrap);
}

// Note: Removed inferVizFromResponse - Cortex Agent sends Vega-Lite specs directly via response.chart event

// Default mode for manual questions when no pill is used
function currentMode(){ return 'analyst'; }

// Create streaming message container with single-column layout
function createStreamingMessage(){
  const msg = document.createElement('div');
  msg.className = 'message assistant';
  
  const badge = document.createElement('span');
  badge.className = 'role-badge';
  badge.textContent = 'Assistant';
  msg.appendChild(badge);
  
  // NEW: Content wrapper to force vertical stacking
  const contentWrapper = document.createElement('div');
  contentWrapper.className = 'message-content-wrapper';
  contentWrapper.style.display = 'flex';
  contentWrapper.style.flexDirection = 'column';
  contentWrapper.style.gap = '12px';
  contentWrapper.style.width = '100%';
  contentWrapper.style.minWidth = '0';
  
  // Row 1: Thinking section
  const thinkingSection = document.createElement('details');
  thinkingSection.className = 'thinking-live';
  thinkingSection.open = true;  // Expanded during streaming
  
  const thinkingSummary = document.createElement('summary');
  thinkingSummary.textContent = '🤔 Thinking...';
  thinkingSummary.style.cursor = 'pointer';
  thinkingSummary.style.color = '#58a6ff';
  thinkingSummary.style.fontSize = '0.9em';
  thinkingSummary.style.fontWeight = '600';
  
  const thinkingContent = document.createElement('div');
  thinkingContent.className = 'thinking-content';
  thinkingContent.style.fontSize = '0.85em';
  thinkingContent.style.color = '#9da7b3';
  thinkingContent.style.backgroundColor = '#161b22';
  thinkingContent.style.padding = '12px';
  thinkingContent.style.borderRadius = '6px';
  thinkingContent.style.marginTop = '8px';
  thinkingContent.style.whiteSpace = 'pre-wrap';
  thinkingContent.style.fontFamily = 'monospace';
  
  thinkingSection.appendChild(thinkingSummary);
  thinkingSection.appendChild(thinkingContent);
  
  // Row 2: SQL section
  const sqlSection = document.createElement('div');
  sqlSection.className = 'sql-section';
  sqlSection.style.display = 'none';  // Hidden until SQL arrives
  
  // Row 3: Answer + Viz section
  const outputSection = document.createElement('div');
  outputSection.className = 'output-section';
  outputSection.style.display = 'flex';
  outputSection.style.flexDirection = 'column';
  outputSection.style.gap = '12px';
  
  const answerDiv = document.createElement('div');
  answerDiv.className = 'message-text';
  answerDiv.style.display = 'none';  // Hidden until answer arrives
  
  const vizPlaceholder = document.createElement('div');
  vizPlaceholder.className = 'viz-placeholder';
  
  outputSection.appendChild(answerDiv);
  outputSection.appendChild(vizPlaceholder);
  
  // Add all sections to wrapper in order
  contentWrapper.appendChild(thinkingSection);
  contentWrapper.appendChild(sqlSection);
  contentWrapper.appendChild(outputSection);
  
  msg.appendChild(contentWrapper);
  els.messages.appendChild(msg);
  els.messages.scrollTop = els.messages.scrollHeight;
  
  return { msg, thinkingSection, thinkingSummary, thinkingContent, answerDiv, sqlSection, vizPlaceholder };
}

async function sendChatStreaming({ overrideMode = null, overrideViz = null } = {}){
  const text = els.input.value.trim();
  if (!text) return;
  if (getRemainingUses() <= 0){
    updateUsesUI();
    return;
  }
  if (!config.backend_base_url){
    setState(State.error);
    addMessage('assistant', 'Setup incomplete: backend URL not configured.');
    return;
  }
  
  // Safety check: Verify Vega-Lite library loaded
  if (typeof vegaEmbed === 'undefined') {
    console.error('[Chart] Vega-Lite library not loaded! Charts will not render.');
    console.error('[Chart] Check if CDN scripts loaded successfully.');
  }
  
  const mode = overrideMode || currentMode();
  const viz = overrideViz;

  addMessage('user', text);
  els.input.value='';
  setState(State.querying);

  const { msg, thinkingSection, thinkingSummary, thinkingContent, answerDiv, sqlSection, vizPlaceholder } = createStreamingMessage();
  
  const streamUrl = joinUrl(config.backend_base_url, `/api/chat/stream?question=${encodeURIComponent(text)}&mode=${mode}`);
  
  let thinkingText = '';
  let statusText = '';
  let answerText = '';
  let sqlQueries = [];
  let tableData = null;
  
  try {
    const eventSource = new EventSource(streamUrl);
    
    eventSource.addEventListener('response.status', (e) => {
      const data = JSON.parse(e.data);
      statusText = `[${data.status}] ${data.message}`;
      thinkingContent.textContent = statusText + '\n\n' + thinkingText;
      els.messages.scrollTop = els.messages.scrollHeight;
    });
    
    eventSource.addEventListener('response.thinking.delta', (e) => {
      const data = JSON.parse(e.data);
      thinkingText += data.text || '';
      thinkingContent.textContent = statusText + '\n\n' + thinkingText;
      els.messages.scrollTop = els.messages.scrollHeight;
    });
    
    eventSource.addEventListener('execution_trace', (e) => {
      const traces = JSON.parse(e.data);
      if (!Array.isArray(traces)) return;
      
      for (const traceStr of traces) {
        try {
          const trace = JSON.parse(traceStr);
          const attrs = trace.attributes || [];
          
          const sqlAttr = attrs.find(a => a.key === 'snow.ai.observability.agent.tool.cortex_analyst.sql_query');
          if (sqlAttr?.value?.stringValue) {
            const sql = sqlAttr.value.stringValue;
            if (!sqlQueries.find(q => q.sql === sql)) {
              sqlQueries.push({
                tool: 'Cortex Analyst',
                sql: sql
              });
              // Show SQL immediately
              sqlSection.style.display = 'block';
              renderSQLCommands(sqlSection, sqlQueries);
            }
          }
        } catch (err) {
          console.error('trace parse error:', err);
        }
      }
    });
    
    eventSource.addEventListener('response.text.delta', (e) => {
      const data = JSON.parse(e.data);
      answerText += data.text || '';
      answerDiv.textContent = answerText;
      answerDiv.style.display = 'block';
      els.messages.scrollTop = els.messages.scrollHeight;
    });
    
    // Listen for Vega-Lite charts from Cortex Agent
    eventSource.addEventListener('response.chart', (e) => {
      try {
        const data = JSON.parse(e.data);
        console.log('[response.chart] Event received, content_index:', data.content_index);
        
        if (!data.chart_spec) {
          console.warn('[response.chart] No chart_spec in event data');
          return;
        }
        
        const vegaSpec = JSON.parse(data.chart_spec);
        console.log('[response.chart] Rendering Vega chart:', vegaSpec.title || 'Untitled');
        console.log('[response.chart] Chart type:', vegaSpec.mark);
        console.log('[response.chart] Data points:', vegaSpec.data?.values?.length || 0);
        
        // Render chart immediately in vizPlaceholder
        renderVizBelow(vizPlaceholder, vegaSpec);
        
      } catch (err) {
        console.error('[response.chart] Parse/render error:', err);
        console.error('[response.chart] Event data preview:', e.data?.substring(0, 200));
      }
    });
    
    // Listen for table data in response.table event
    eventSource.addEventListener('response.table', (e) => {
      const data = JSON.parse(e.data);
      if (data.table?.rows) {
        tableData = data.table.rows;
        console.log('[response.table] Received table data:', tableData.length, 'rows');
      }
    });
    
    eventSource.addEventListener('response', (e) => {
      const data = JSON.parse(e.data);
      const content = data.content || [];
      
      // Extract final answer and table data if not already shown
      if (!answerText) {
        for (const item of content) {
          if (item.type === 'text') {
            answerText += item.text || '';
          } else if (item.type === 'table' && item.table?.rows) {
            tableData = item.table.rows;
            console.log('[response] Extracted table data:', tableData.length, 'rows');
          }
        }
        answerDiv.textContent = answerText;
        answerDiv.style.display = 'block';
      }
      
      // Auto-collapse thinking and SQL
      thinkingSection.open = false;
      thinkingSummary.textContent = '🤔 Thinking Process (click to expand)';
      
      // Note: Charts are rendered via response.chart event (not here)
      // This ensures charts appear as soon as agent generates them
      
      eventSource.close();
      setState(State.idle);
      setRemainingUses(getRemainingUses() - 1);
      updateUsesUI();
      announceUses();
    });
    
    eventSource.addEventListener('error', (e) => {
      console.error('SSE error:', e);
      eventSource.close();
      if (msg && !answerText) {
        answerDiv.textContent = 'Service error. Please try again.';
        answerDiv.style.display = 'block';
      }
      setState(State.error);
    });
    
    eventSource.addEventListener('done', (e) => {
      eventSource.close();
    });
    
  } catch(err){
    console.error(err);
    if (msg) {
      answerDiv.textContent = 'Service error. Try again.';
      answerDiv.style.display = 'block';
    }
    setState(State.error);
  }
}

// Wrapper function to choose between streaming (analyst) and batch (search)
async function sendChat({ overrideMode = null, overrideViz = null } = {}){
  const mode = overrideMode || currentMode();
  
  // Use streaming for analyst mode, batch for search mode
  if (mode === 'analyst') {
    return sendChatStreaming({ overrideMode, overrideViz });
  }
  
  // Original batch mode for search
  const text = els.input.value.trim();
  if (!text) return;
  if (getRemainingUses() <= 0){
    updateUsesUI();
    return;
  }
  if (!config.backend_base_url){
    setState(State.error);
    addMessage('assistant', 'Setup incomplete: backend URL not configured.');
    return;
  }
  const viz = overrideViz;

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
    
    // Note: Search mode doesn't support charts via Cortex (text-only results)
    
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


