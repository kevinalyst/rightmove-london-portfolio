const State = { idle: 'idle', paid: 'paid', querying: 'querying', error: 'error' };
let state = State.idle;
let config = null;

const els = {
  messages: document.getElementById('messages'),
  input: document.getElementById('input'),
  pay: document.getElementById('pay'),
  ask: document.getElementById('ask'),
  reset: document.getElementById('reset'),
};

async function loadConfig(){
  const res = await fetch('config.json', { cache: 'no-store' });
  config = await res.json();
}

function setState(next){
  state = next;
  const token = localStorage.getItem('usage_token');
  if (state === State.paid || token){
    els.input.removeAttribute('disabled');
    els.ask.removeAttribute('disabled');
  } else {
    els.input.setAttribute('disabled','');
    els.ask.setAttribute('disabled','');
  }
}

function addMessage(role, text){
  const div = document.createElement('div');
  div.className = `message ${role}`;
  div.textContent = text;
  els.messages.appendChild(div);
  els.messages.scrollTop = els.messages.scrollHeight;
}

async function createCheckout(){
  try{
    const res = await fetch(`${config.backend_base_url}/api/create-checkout-session`, { method:'POST' });
    const data = await res.json();
    if (data && data.url){
      // For demo: simulate immediate success when placeholder key is present
      if (config.stripe_public_key.includes('PLACEHOLDER')){
        const fakeSession = 'demo_session_' + Math.random().toString(36).slice(2);
        await grant(fakeSession);
        return;
      }
      window.location.href = data.url;
    } else {
      throw new Error('Bad response');
    }
  } catch(err){
    console.error(err);
    addMessage('assistant','Payment service is unavailable right now.');
    setState(State.error);
  }
}

async function grant(sessionId){
  try{
    const res = await fetch(`${config.backend_base_url}/api/grant?session_id=${encodeURIComponent(sessionId)}`);
    const data = await res.json();
    if (data && data.token){
      localStorage.setItem('usage_token', data.token);
      setState(State.paid);
      addMessage('assistant','Payment confirmed. You can ask one question.');
    } else {
      throw new Error('No token');
    }
  } catch(err){
    console.error(err);
    addMessage('assistant','Unable to grant token.');
    setState(State.error);
  }
}

async function sendChat(){
  const text = els.input.value.trim();
  if (!text) return;
  const token = localStorage.getItem('usage_token');
  if (!token){
    addMessage('assistant','Please complete payment first.');
    return;
  }
  addMessage('user', text);
  els.input.value='';
  setState(State.querying);
  try{
    const res = await fetch(`${config.backend_base_url}/api/chat`,{
      method:'POST',
      headers:{ 'Content-Type':'application/json', 'Authorization':`Bearer ${token}` },
      body: JSON.stringify({query:text})
    });
    const data = await res.json();
    if (data && data.text){
      addMessage('assistant', data.text);
      // Consume token on first use
      localStorage.removeItem('usage_token');
      setState(State.idle);
    } else {
      throw new Error('No text');
    }
  } catch(err){
    console.error(err);
    addMessage('assistant','Service error. Please try again later.');
    setState(State.error);
  }
}

function resetAll(){
  localStorage.removeItem('usage_token');
  els.messages.innerHTML='';
  setState(State.idle);
}

window.addEventListener('DOMContentLoaded', async () => {
  await loadConfig();
  setState(State.idle);
  // If redirected from real payment: ?session_id=...
  const url = new URL(window.location.href);
  const sid = url.searchParams.get('session_id');
  if (sid){
    await grant(sid);
    url.searchParams.delete('session_id');
    history.replaceState({},'',url.toString());
  }
  els.pay.addEventListener('click', createCheckout);
  els.ask.addEventListener('click', sendChat);
  els.input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)){
      e.preventDefault();
      sendChat();
    }
  });
  els.reset.addEventListener('click', resetAll);
});


