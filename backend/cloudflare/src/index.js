function parseAllowedOrigins(raw){
  if (!raw || raw === '*') return ['*'];
  return String(raw)
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function matchesOrigin(origin, patterns){
  if (!origin) return '';
  if (!patterns || patterns.length === 0) return '';
  if (patterns.includes('*')) return '*';
  for (const pattern of patterns){
    if (pattern === origin) return origin;
    if (pattern.startsWith('*.')){
      const suffix = pattern.slice(1); // keep leading dot
      if (origin.endsWith(suffix)) return origin;
    }
  }
  return '';
}

function corsHeaders(env, request){
  const origin = request.headers.get('Origin');
  const patterns = parseAllowedOrigins(env.ALLOW_ORIGIN || '*');
  const allow = matchesOrigin(origin, patterns);
  const base = {
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Vary': 'Origin'
  };
  if (allow) {
    base['Access-Control-Allow-Origin'] = allow;
    if (allow !== '*') {
      base['Access-Control-Allow-Credentials'] = 'true';
    }
  }
  return base;
}

function json(env, request, data, init={}){
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { 'content-type':'application/json', ...corsHeaders(env, request), ...(init.headers||{}) },
    ...init
  });
}
function bad(env, request, msg, code=400){
  return new Response(JSON.stringify({ error: msg }), {
    status: code,
    headers: { 'content-type':'application/json', ...corsHeaders(env, request) }
  });
}

function requiredString(value, name){
  if (!value || typeof value !== 'string'){
    throw new Error(`${name} is required`);
  }
  return value;
}

function parseAgentResponse(agentPayload){
  if (!agentPayload) return { text: 'No response from agent.', records: null, viz: null };

  const responseEnvelope = agentPayload?.result || agentPayload?.response || agentPayload;

  const messages = responseEnvelope?.messages;
  let answer = '';
  if (Array.isArray(messages)){
    for (const message of messages){
      const contents = message?.content;
      if (!Array.isArray(contents)) continue;
      for (const chunk of contents){
        if (chunk?.type === 'TEXT' && typeof chunk?.text === 'string'){
          answer += chunk.text;
        }
      }
    }
  }
  if (!answer && typeof responseEnvelope?.output_text === 'string'){
    answer = responseEnvelope.output_text;
  }

  let dataRows = null;
  const toolResponses = responseEnvelope?.tool_responses;
  if (Array.isArray(toolResponses)){
    for (const tool of toolResponses){
      const table = tool?.result?.table;
      if (Array.isArray(table?.rows)){
        dataRows = table.rows.map((row) => {
          const obj = {};
          const cols = table.columns || [];
          row.forEach((val, idx) => {
            const key = cols[idx]?.name || `col_${idx}`;
            obj[key] = val;
          });
          return obj;
        });
        break;
      }
    }
  }

  return { text: answer || 'No response from agent.', records: dataRows, viz: null };
}

async function callCortexAgent(env, prompt){
  const account = requiredString(env.SNOWFLAKE_ACCOUNT, 'SNOWFLAKE_ACCOUNT');
  const host = account.includes('.') ? account : `${account}.snowflakecomputing.com`;
  const database = env.SNOWFLAKE_AGENT_DATABASE || 'SNOWFLAKE_INTELLIGENCE';
  const schema = env.SNOWFLAKE_AGENT_SCHEMA || 'AGENTS';
  const agentName = env.SNOWFLAKE_AGENT_NAME || 'RIGHTMOVE_ANALYSIS';
  const token = requiredString(env.SNOWFLAKE_OAUTH_TOKEN, 'SNOWFLAKE_OAUTH_TOKEN');

  const encodedParts = [database, schema, agentName].map((p) => encodeURIComponent(p));
  const url = `https://${host}/api/v0/agents/${encodedParts[0]}/${encodedParts[1]}/${encodedParts[2]}/actions/runs?sync=true`;

  const body = {
    input: {
      messages: [
        {
          role: 'USER',
          content: [
            {
              type: 'TEXT',
              text: prompt
            }
          ]
        }
      ]
    }
  };

  const headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Authorization': `Bearer ${token}`,
    'User-Agent': 'london-portfolio-worker/1.1'
  };

  const res = await fetch(url, { method: 'POST', headers, body: JSON.stringify(body) });
  if (!res.ok){
    const errorPayload = await res.text();
    throw new Error(`snowflake_agent_error: ${res.status} ${errorPayload}`);
  }
  const json = await res.json();
  return parseAgentResponse(json);
}

async function chat(env, request){
  const body = await request.json().catch(()=>({}));
  const q = typeof body.query === 'string' ? body.query : (typeof body.question === 'string' ? body.question : '');
  if (!q) return bad(env, request, 'missing query', 400);

  let result = { text: 'Stubbed answer.', records: null, viz: null };
  try{
    result = await callCortexAgent(env, q);
  } catch(e){
    console.error('cortex_agent_error', e?.message || e);
    return bad(env, request, 'Cortex backend currently unavailable.', 503);
  }

  // Return both `answer` (preferred by frontend) and `text` for backward compatibility
  const resp = { answer: result.text, text: result.text };
  if (result.records) resp.data = result.records;
  if (result.viz) resp.viz = result.viz;
  if (body && body.viz) resp.viz = body.viz;
  return json(env, request, resp);
}

export default {
  async fetch(request, env){
    const url = new URL(request.url);
    const p = url.pathname;
    if (request.method === 'OPTIONS'){
      return new Response(null, { status: 204, headers: corsHeaders(env, request) });
    }
    if (request.method === 'POST' && p === '/api/chat') return chat(env, request);
    return new Response('ok', { headers: corsHeaders(env, request) });
  }
};
