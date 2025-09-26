const TOKEN_TTL_SECS = 15 * 60; // 15 minutes
const CREDITS_PER_PURCHASE = 10;

function b64url(input){
  return btoa(String.fromCharCode(...new Uint8Array(input)))
    .replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
}

async function signJwt(payload, secret){
  const enc = new TextEncoder();
  const header = { alg: "HS256", typ: "JWT" };
  const headerB64 = b64url(enc.encode(JSON.stringify(header)));
  const payloadB64 = b64url(enc.encode(JSON.stringify(payload)));
  const data = `${headerB64}.${payloadB64}`;
  const key = await crypto.subtle.importKey('raw', enc.encode(secret), { name:'HMAC', hash:'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, enc.encode(data));
  const sigB64 = b64url(sig);
  return `${data}.${sigB64}`;
}

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

async function verifyStripeSession(env, sessionId){
  const res = await fetch(`https://api.stripe.com/v1/checkout/sessions/${encodeURIComponent(sessionId)}`, {
    headers: { 'authorization': `Bearer ${env.STRIPE_SECRET_KEY}` }
  });
  if (!res.ok) return null;
  const data = await res.json();
  if (data && (data.payment_status === 'paid' || data.status === 'complete')) return data;
  return null;
}

async function createCheckoutSession(env, request){
  const origin = request.headers.get('origin');
  const base = origin || (new URL(request.url)).origin;
  const success = `${base}/index.html?session_id={CHECKOUT_SESSION_ID}`;
  const cancel = `${base}/index.html`;
  const form = new URLSearchParams();
  form.set('mode', 'payment');
  form.set('success_url', success);
  form.set('cancel_url', cancel);
  if (env.STRIPE_PRICE_ID && env.STRIPE_PRICE_ID.startsWith('price_')){
    form.set('line_items[0][price]', env.STRIPE_PRICE_ID);
    form.set('line_items[0][quantity]', '1');
  } else if (env.STRIPE_PRODUCT_ID && env.STRIPE_PRODUCT_ID.startsWith('prod_')){
    form.set('line_items[0][price_data][product]', env.STRIPE_PRODUCT_ID);
    form.set('line_items[0][price_data][currency]', 'gbp');
    form.set('line_items[0][price_data][unit_amount]', '100');
    form.set('line_items[0][quantity]', '1');
  } else {
    return bad(env, request, 'Stripe price or product not configured', 500);
  }
  const r = await fetch('https://api.stripe.com/v1/checkout/sessions', {
    method: 'POST',
    headers: { 'authorization': `Bearer ${env.STRIPE_SECRET_KEY}`, 'content-type':'application/x-www-form-urlencoded' },
    body: form
  });
  if (!r.ok){
    const t = await r.text();
    return bad(env, request, `stripe_error: ${t}`, 502);
  }
  const d = await r.json();
  return json(env, request, { url: d.url });
}

async function grantToken(env, request, url){
  const sessionId = url.searchParams.get('session_id');
  if (!sessionId) return bad(env, request, 'missing session_id', 400);
  const session = await verifyStripeSession(env, sessionId);
  if (!session) return bad(env, request, 'invalid session', 400);
  const expMs = Date.now() + TOKEN_TTL_SECS * 1000;
  const payload = { credits: CREDITS_PER_PURCHASE, exp: expMs, session_id: sessionId };
  const token = await signJwt(payload, env.JWT_SIGNING_KEY);
  await env.USAGE_TOKENS.put(token, JSON.stringify({ credits: CREDITS_PER_PURCHASE, exp: expMs, used: 0, sessionId }), { expirationTtl: TOKEN_TTL_SECS });
  return json(env, request, { token });
}

async function callSnowflake(env, prompt){
  const account = env.SNOWFLAKE_ACCOUNT;
  const host = account.includes('.') ? account : `${account}.snowflakecomputing.com`;
  const url = `https://${host}/api/v2/statements`;
  const body = {
    statement: "select snowflake.cortex.complete('MODEL_OR_VIEW', {prompt => :1});",
    binds: [prompt],
    timeout: 60,
    database: env.SNOWFLAKE_DATABASE,
    schema: env.SNOWFLAKE_SCHEMA,
    warehouse: env.SNOWFLAKE_WAREHOUSE
  };
  const headers = { 'content-type':'application/json' };
  if (env.SNOWFLAKE_OAUTH_TOKEN){
    headers['authorization'] = `Snowflake Token=\"${env.SNOWFLAKE_OAUTH_TOKEN}\"`;
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
  const demoFree = String(env.ALLOW_DEMO_FREE || '').toLowerCase() === 'true';

  const auth = request.headers.get('authorization') || '';
  const token = auth.toLowerCase().startsWith('bearer ') ? auth.slice(7) : '';
  let entry = null;

  if (!demoFree){
    if (!token) return bad(env, request, 'missing token', 401);
    const raw = await env.USAGE_TOKENS.get(token);
    if (!raw) return bad(env, request, 'invalid or expired token', 401);
    entry = JSON.parse(raw);
    if (entry.credits <= 0) return bad(env, request, 'token exhausted', 403);
    if (Date.now() > entry.exp) return bad(env, request, 'token expired', 401);
  }

  const body = await request.json().catch(()=>({}));
  const q = typeof body.query === 'string' ? body.query : (typeof body.question === 'string' ? body.question : '');
  if (!q) return bad(env, request, 'missing query', 400);

  let text = 'Stubbed answer.';
  try{
    if (env.SNOWFLAKE_ACCOUNT && env.SNOWFLAKE_OAUTH_TOKEN){
      text = await callSnowflake(env, q);
    }
  } catch(e){
    text = 'Cortex backend currently unavailable.';
  }

  if (!demoFree && entry){
    entry.credits -= 1;
    await env.USAGE_TOKENS.put(token, JSON.stringify(entry), { expirationTtl: Math.max(1, Math.floor((entry.exp - Date.now())/1000)) });
  }

  // Return both `answer` (preferred by frontend) and `text` for backward compatibility
  const resp = { answer: text, text };
  if (entry && Number.isFinite(entry.credits)) resp.remaining = entry.credits;
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
    if (request.method === 'POST' && p === '/api/create-checkout-session') return createCheckoutSession(env, request);
    if (request.method === 'GET' && p === '/api/grant') return grantToken(env, request, url);
    if (request.method === 'POST' && p === '/api/chat') return chat(env, request);
    return new Response('ok', { headers: corsHeaders(env, request) });
  }
};
