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

async function callSnowflake(env, prompt){
  const account = env.SNOWFLAKE_ACCOUNT;
  const host = account.includes('.') ? account : `${account}.snowflakecomputing.com`;
  const url = `https://${host}/api/v2/statements`;
  const resource = env.SNOWFLAKE_CORTEX_RESOURCE || 'RIGHTMOVE_ANALYSIS';
  const statement = "select snowflake.cortex.complete(:1, {prompt => :2});";
  const binds = [resource, prompt];
  const body = {
    statement,
    binds,
    timeout: 60,
    database: env.SNOWFLAKE_DATABASE,
    schema: env.SNOWFLAKE_SCHEMA,
    warehouse: env.SNOWFLAKE_WAREHOUSE
  };
  const headers = {
    'Content-Type':'application/json',
    'Accept':'application/json',
    'User-Agent':'london-portfolio-worker/1.0'
  };
  if (env.SNOWFLAKE_OAUTH_TOKEN){
    headers['authorization'] = `Bearer ${env.SNOWFLAKE_OAUTH_TOKEN}`;
  } else if (env.SNOWFLAKE_USER && env.SNOWFLAKE_PASSWORD){
    // Basic auth session token flow is not implemented; prefer OAuth token
    throw new Error('Snowflake token not configured');
  } else {
    throw new Error('Snowflake credentials missing');
  }
  const res = await fetch(url, { method:'POST', headers, body: JSON.stringify(body) });
  if (!res.ok){
    const t = await res.text();
    throw new Error(`snowflake_error: ${t}`);
  }
  const d = await res.json();
  const rows = d?.result?.data || d?.data || [];
  const text = Array.isArray(rows) && rows.length ? String(rows[0][0]) : 'No response';
  return text;
}

async function chat(env, request){
  const body = await request.json().catch(()=>({}));
  const q = typeof body.query === 'string' ? body.query : (typeof body.question === 'string' ? body.question : '');
  if (!q) return bad(env, request, 'missing query', 400);

  let text = 'Stubbed answer.';
  try{
    if (env.SNOWFLAKE_ACCOUNT && env.SNOWFLAKE_OAUTH_TOKEN){
      text = await callSnowflake(env, q);
    }
  } catch(e){
    console.error('cortex_error', e?.message || e);
    text = 'Cortex backend currently unavailable.';
  }

  // Return both `answer` (preferred by frontend) and `text` for backward compatibility
  const resp = { answer: text, text };
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
