# Wire up Snowflake Cortex and Payments (10 minutes)

This guide connects your static demo to a minimal backend and Snowflake Cortex without exposing secrets on the frontend.

## Choose a backend target
Pick one and deploy the included stubs under `/backend`:
- Option A: Cloud Run (HTTP service)
- Option B: Cloudflare Workers / Pages Functions
- Option C: Vercel / Netlify Functions

The backend exposes three endpoints:
1. POST `/api/create-checkout-session` → creates a $1 Stripe Checkout session (PRICE_ID placeholder).
2. GET `/api/grant?session_id=...` → exchanges a successful Stripe session for a one-time usage token (JWT).
3. POST `/api/chat` (Bearer token) → verifies token, calls Snowflake Cortex, returns JSON.

## Config
- Frontend `/docs/config.json` (no secrets):
{"stripe_public_key":"pk_live_PLACEHOLDER","checkout_price_id":"price_PLACEHOLDER","backend_base_url":"https://YOUR_BACKEND_HOST"}
- Backend `.env.sample` (copy to `.env` in your deployment):
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PRICE_ID=price_...
JWT_SIGNING_KEY=please-change-me
SNOWFLAKE_ACCOUNT=ORG-ACCT
SNOWFLAKE_USER=...
SNOWFLAKE_PASSWORD=...
SNOWFLAKE_WAREHOUSE=...
SNOWFLAKE_DATABASE=...
SNOWFLAKE_SCHEMA=...

## Snowflake Cortex call pattern
- Use Snowflake SQL API or official client to call your Cortex endpoint/SQL.
- Send the user prompt and optionally a grounding table/view (e.g., your transformed sample).
- Return the text output to the frontend.

Flow (described):
1. Backend receives POST `/api/chat` with `{query}` and Bearer token.
2. Verify token → single use, short TTL → mark consumed.
3. Run SQL like: select snowflake.cortex.complete('MODEL_OR_VIEW', {prompt: :prompt});
4. Map result to `{ "text": "..." }` and return.

## Ops notes
- Rate limiting: 1 request per token (credits:1).
- Limits: cap prompt size; truncate overly long inputs.
- Logging: hash any user identifiers; never log raw PII.
- Fallbacks: return a friendly error if Cortex/Stripe is unavailable.

## GitHub Pages
- Settings → Pages → Build from `/docs` on `main`.
- Add `/docs/assets/social-preview.png` for a social card.
