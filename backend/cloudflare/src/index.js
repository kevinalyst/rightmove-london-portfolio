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

// Retry configuration
const REQUEST_TIMEOUT_MS = 30000; // 30 seconds
const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 1000;

async function withRetry(fn, retries = MAX_RETRIES) {
  let lastError;
  for (let i = 0; i <= retries; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      const isRetryable = error.status === 429 || error.status === 503 || 
                         error.status === 504 || error.message?.includes('timeout');
      
      if (i < retries && isRetryable) {
        const delay = RETRY_DELAY_MS * Math.pow(2, i) * (0.5 + Math.random() * 0.5);
        console.warn(`Retry ${i + 1}/${retries} after ${delay}ms: ${error.message}`);
        await new Promise(resolve => setTimeout(resolve, delay));
      } else {
        throw error;
      }
    }
  }
  throw lastError;
}

async function callCortexSearch(env, query) {
  const account = requiredString(env.SNOWFLAKE_ACCOUNT, 'SNOWFLAKE_ACCOUNT');
  const host = account.includes('.') ? account : `${account}.snowflakecomputing.com`;
  const database = env.SNOWFLAKE_SEARCH_DATABASE || 'RIGHTMOVE_LONDON_SELL';
  const schema = env.SNOWFLAKE_SEARCH_SCHEMA || 'CLOUDRUN_DXLVF';
  const serviceName = env.SNOWFLAKE_SEARCH_SERVICE || 'UNSTRUCTURED_RAG';
  const token = requiredString(env.SNOWFLAKE_PAT_TOKEN, 'SNOWFLAKE_PAT_TOKEN');

  const encodedParts = [database, schema, serviceName].map((p) => encodeURIComponent(p));
  const url = `https://${host}/api/v0/services/${encodedParts[0]}/${encodedParts[1]}/${encodedParts[2]}:query`;

  const body = {
    query: query,
    columns: ["*"], // Return all columns
    limit: 10
  };

  // Use Bearer token format for PAT
  const headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Authorization': `Bearer ${token}`,
    'User-Agent': 'london-portfolio-worker/1.1'
  };

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  
  try {
    const res = await fetch(url, { 
      method: 'POST', 
      headers, 
      body: JSON.stringify(body),
      signal: controller.signal 
    });
    
    clearTimeout(timeout);
    
    if (!res.ok){
      const requestId = res.headers.get('sf-query-id') || res.headers.get('x-snowflake-request-id');
      const errorPayload = await res.text();
      const message = requestId ? `${res.status} ${errorPayload} (requestId=${requestId})` : `${res.status} ${errorPayload}`;
      const error = new Error(`snowflake_search_error: ${message}`);
      error.status = res.status;
      error.requestId = requestId;
      throw error;
    }
    
    const json = await res.json();
    
    // Parse search results
    const results = json?.results || [];
    const text = results.length > 0 
      ? `Found ${results.length} properties matching your search.` 
      : 'No properties found matching your search criteria.';
    
    return { 
      text, 
      records: results.map(r => r.body || r), 
      viz: null 
    };
  } catch (error) {
    clearTimeout(timeout);
    if (error.name === 'AbortError') {
      const timeoutError = new Error(`Request timeout after ${REQUEST_TIMEOUT_MS}ms`);
      timeoutError.status = 504;
      throw timeoutError;
    }
    throw error;
  }
}

async function callCortexAgent(env, prompt, mode = 'analyst'){
  if (mode === 'search') {
    return callCortexSearch(env, prompt);
  }
  
  const account = requiredString(env.SNOWFLAKE_ACCOUNT, 'SNOWFLAKE_ACCOUNT');
  const host = account.includes('.') ? account : `${account}.snowflakecomputing.com`;
  const database = env.SNOWFLAKE_AGENT_DATABASE || 'SNOWFLAKE_INTELLIGENCE';
  const schema = env.SNOWFLAKE_AGENT_SCHEMA || 'AGENTS';
  const agentName = env.SNOWFLAKE_AGENT_NAME || 'RIGHTMOVE_ANALYSIS';
  const token = requiredString(env.SNOWFLAKE_PAT_TOKEN, 'SNOWFLAKE_PAT_TOKEN');

  // Try with v2 API endpoint instead of v0
  const encodedParts = [database, schema, agentName].map((p) => encodeURIComponent(p));
  const url = `https://${host}/api/v2/databases/${encodedParts[0]}/schemas/${encodedParts[1]}/agents/${encodedParts[2]}/actions/runs?sync=true`;
  
  console.log(`[callCortexAgent] URL: ${url}`);
  console.log(`[callCortexAgent] Host: ${host}`);

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

  // Use Bearer token format - try without the X-Snowflake header first
  // Some Snowflake REST endpoints auto-detect token type
  const headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Authorization': `Bearer ${token}`,
    'User-Agent': 'london-portfolio-worker/1.1'
  };
  
  console.log(`[callCortexAgent] Using Bearer auth (PAT auto-detect)`);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  
  try {
    const res = await fetch(url, { 
      method: 'POST', 
      headers, 
      body: JSON.stringify(body),
      signal: controller.signal 
    });
    
    clearTimeout(timeout);
    
    if (!res.ok){
      const requestId = res.headers.get('sf-query-id') || res.headers.get('x-snowflake-request-id');
      let errorPayload;
      try {
        errorPayload = await res.text();
      } catch (e) {
        errorPayload = 'Unable to read error response';
      }
      
      console.error(`[Snowflake Response] Status: ${res.status}, Body: ${errorPayload}, RequestId: ${requestId}`);
      
      const message = requestId ? `${res.status} ${errorPayload} (requestId=${requestId})` : `${res.status} ${errorPayload}`;
      const error = new Error(`snowflake_agent_error: ${message}`);
      error.status = res.status;
      error.requestId = requestId;
      throw error;
    }
    const json = await res.json();
    return parseAgentResponse(json);
  } catch (error) {
    clearTimeout(timeout);
    if (error.name === 'AbortError') {
      const timeoutError = new Error(`Request timeout after ${REQUEST_TIMEOUT_MS}ms`);
      timeoutError.status = 504;
      throw timeoutError;
    }
    
    console.error(`[Fetch Error] Name: ${error.name}, Message: ${error.message}, Stack: ${error.stack}`);
    
    throw error;
  }
}

async function chat(env, request){
  const body = await request.json().catch(()=>({}));
  const q = typeof body.query === 'string' ? body.query : (typeof body.question === 'string' ? body.question : '');
  const mode = body.mode || 'analyst'; // Default to analyst mode
  
  if (!q) return bad(env, request, 'missing query', 400);
  if (!['analyst', 'search'].includes(mode)) {
    return bad(env, request, 'invalid mode: must be "analyst" or "search"', 400);
  }

  let result = { text: 'Stubbed answer.', records: null, viz: null };
  const correlationId = crypto.randomUUID();
  
  try{
    console.log(`[${correlationId}] Starting ${mode} request for query: ${q.substring(0, 100)}...`);
    
    result = await withRetry(() => callCortexAgent(env, q, mode));
    
    console.log(`[${correlationId}] Success: ${mode} request completed`);
  } catch(e){
    console.error(`[${correlationId}] Error in ${mode} request:`, {
      message: e?.message || String(e),
      status: e?.status,
      requestId: e?.requestId,
      stack: e?.stack
    });
    
    // Return more specific error codes based on the error type
    if (e?.status === 401 || e?.message?.includes('auth')) {
      return bad(env, request, 'Authentication failed. Please check credentials.', 401);
    }
    if (e?.status === 404) {
      return bad(env, request, 'Snowflake agent not found. Please check configuration.', 404);
    }
    if (e?.status === 504 || e?.message?.includes('timeout')) {
      return bad(env, request, 'Request timed out. Please try again.', 504);
    }
    
    // Generic error with details
    const errorDetails = e?.requestId ? ` (requestId: ${e.requestId})` : '';
    return bad(env, request, `Cortex backend error: ${e?.message || 'Unknown error'}${errorDetails}`, 502);
  }

  // Return both `answer` (preferred by frontend) and `text` for backward compatibility
  const resp = { answer: result.text, text: result.text };
  if (result.records) resp.data = result.records;
  if (result.viz) resp.viz = result.viz;
  if (body && body.viz) resp.viz = body.viz;
  return json(env, request, resp);
}

async function health(env, request) {
  const correlationId = crypto.randomUUID();
  
  try {
    // Check required environment variables
    const account = env.SNOWFLAKE_ACCOUNT;
    const token = env.SNOWFLAKE_PAT_TOKEN;
    const database = env.SNOWFLAKE_AGENT_DATABASE || 'SNOWFLAKE_INTELLIGENCE';
    const schema = env.SNOWFLAKE_AGENT_SCHEMA || 'AGENTS';
    const agentName = env.SNOWFLAKE_AGENT_NAME || 'RIGHTMOVE_ANALYSIS';
    
    if (!account) {
      return json(env, request, { 
        ok: false, 
        error: 'SNOWFLAKE_ACCOUNT not configured' 
      }, { status: 503 });
    }
    
    if (!token) {
      return json(env, request, { 
        ok: false, 
        error: 'SNOWFLAKE_PAT_TOKEN not configured' 
      }, { status: 503 });
    }
    
    // Simple connectivity check - we could do a lightweight API call here
    // For now, just verify configuration is present
    console.log(`[${correlationId}] Health check passed`);
    
    return json(env, request, { 
      ok: true,
      config: {
        account: account.split('.')[0], // Don't expose full account URL
        database,
        schema,
        agent: agentName
      }
    });
  } catch (error) {
    console.error(`[${correlationId}] Health check failed:`, error);
    return json(env, request, { 
      ok: false, 
      error: error.message 
    }, { status: 503 });
  }
}

export default {
  async fetch(request, env){
    const url = new URL(request.url);
    const p = url.pathname;
    
    // Handle OPTIONS for CORS preflight
    if (request.method === 'OPTIONS'){
      return new Response(null, { status: 204, headers: corsHeaders(env, request) });
    }
    
    // Health check endpoint
    if (request.method === 'GET' && p === '/api/health') {
      return health(env, request);
    }
    
    // Chat endpoint
    if (request.method === 'POST' && p === '/api/chat') {
      return chat(env, request);
    }
    
    // Default response
    return new Response('ok', { headers: corsHeaders(env, request) });
  }
};
