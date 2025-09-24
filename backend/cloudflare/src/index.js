const memory = {
  sessions: new Map(),
  tokens: new Map(), // token -> { credits: 1, exp: epoch_ms, used: false, sessionId }
};

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
  const key = await crypto.subtle.importKey(
    'raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
  );
  const sig = await crypto.subtle.sign('HMAC', key, enc.encode(data));
  const sigB64 = b64url(sig);
  return `${data}.${sigB64}`;
}

function json(data, init={}){
  return new Response(JSON.stringify(data), { status: 200, headers: { 'content-type':'application/json' , ...init.headers }, ...init });
}

function bad(msg, code=400){
  return new Response(JSON.stringify({ error: msg }), { status: code, headers: { 'content-type':'application/json' } });
}

async function handleCreateCheckoutSession(env){
  // Stub: return a placeholder URL; real integration should create Stripe Checkout via secret key
  const sessionId = `sess_${Math.random().toString(36).slice(2)}`;
  memory.sessions.set(sessionId, { created: Date.now() });
  return json({ url: `https://example.com/checkout?session_id=${encodeURIComponent(sessionId)}` });
}

async function handleGrant(url, env){
  const sessionId = url.searchParams.get('session_id');
  if (!sessionId || !memory.sessions.has(sessionId)) return bad('invalid session', 400);
  const exp = Date.now() + 10 * 60 * 1000; // 10 minutes
  const payload = { credits: 1, exp, session_id: sessionId };
  const token = await signJwt(payload, env.JWT_SIGNING_KEY || 'development');
  memory.tokens.set(token, { credits: 1, exp, used: false, sessionId });
  return json({ token });
}

async function handleChat(request, env){
  const auth = request.headers.get('authorization') || '';
  const token = auth.toLowerCase().startsWith('bearer ') ? auth.slice(7) : '';
  if (!token) return bad('missing token', 401);
  const entry = memory.tokens.get(token);
  if (!entry) return bad('invalid token', 401);
  if (entry.used) return bad('token already used', 403);
  if (Date.now() > entry.exp) return bad('token expired', 401);

  const { query } = await request.json().catch(()=>({}));
  if (!query || typeof query !== 'string') return bad('missing query', 400);

  // Placeholder: call Snowflake Cortex here using secure credentials in env
  const text = "Stubbed answer. Wire backend to Snowflake Cortex as documented in docs/wire-up-cortex.md.";

  // consume the token
  entry.used = true; entry.credits = 0; memory.tokens.set(token, entry);
  return json({ text });
}

export default {
  async fetch(request, env){
    const url = new URL(request.url);
    const { pathname } = url;
    if (request.method === 'POST' && pathname === '/api/create-checkout-session'){
      return handleCreateCheckoutSession(env);
    }
    if (request.method === 'GET' && pathname === '/api/grant'){
      return handleGrant(url, env);
    }
    if (request.method === 'POST' && pathname === '/api/chat'){
      return handleChat(request, env);
    }
    return new Response('ok', { status: 200 });
  }
};
