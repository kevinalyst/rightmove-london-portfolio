# Wire up Snowflake Cortex and Payments (10 minutes)

This guide connects your static demo to a minimal backend and Snowflake Cortex without exposing secrets on the frontend.

## Choose a backend target
Pick one and deploy the included stubs under `/backend`:
- Option A: Cloud Run (HTTP service)
- Option B: Cloudflare Workers / Pages Functions
- Option C: Vercel / Netlify Functions

The backend exposes three endpoints:
1. POST `/api/create-checkout-session` → creates a Stripe Checkout session (PRICE_ID placeholder).
2. GET `/api/grant?session_id=...` → verifies session, mints a 10‑query token (KV‑backed).
3. POST `/api/chat` (Bearer token) → verifies token, decrements credits, calls Snowflake Cortex.

## Cloudflare Workers quick steps
1) Install/login
- `npm i -g wrangler`
- `wrangler login`
2) KV binding
- `cd backend/cloudflare`
- `wrangler kv:namespace create USAGE_TOKENS` → paste id in `wrangler.toml`
3) Secrets (no quotes)
- `wrangler secret put STRIPE_SECRET_KEY`
- `wrangler secret put STRIPE_PRICE_ID` (use your price id)
- `wrangler secret put JWT_SIGNING_KEY`
- Snowflake: `wrangler secret put SNOWFLAKE_ACCOUNT`, `..._USER`, `..._WAREHOUSE`, `..._DATABASE`, `..._SCHEMA`, and either `..._PASSWORD` or key‑pair
4) Deploy
- `wrangler deploy`
- Take the Worker URL → put in `docs/config.json` as `backend_base_url`

## Stripe setup
- Product: “London Property Chat — 10‑Query Pack”
- Description: “One‑time purchase of 10 questions to the London Property AI assistant.”
- Use your Price ID in Worker secret `STRIPE_PRICE_ID`.
- Flow: frontend calls `/api/create-checkout-session` → redirect → back to Pages with `session_id` → call `/api/grant` → store token.

## Snowflake Cortex call pattern
- Use Snowflake SQL API from the Worker.
- Example statement: `select snowflake.cortex.complete('MODEL_OR_VIEW', {prompt => :1});`
- Bind `:1` with user prompt; set `warehouse`, `database`, `schema` in payload.
- Return the text to the frontend; log only timings and sizes.

## Ops notes
- Tokens: KV with `{credits:10, exp, sessionId}`; one token per checkout.
- Limits: trim prompt length; reject empty inputs.
- Privacy: do not log raw prompts or PII.
- CORS: allow your Pages origin only.
