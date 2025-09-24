# Minimal Edge Backend (stubs)

Choose a target and deploy the stubs. Endpoints:
- POST `/api/create-checkout-session`
- GET `/api/grant?session_id=...`
- POST `/api/chat`

Secrets live in `.env` (see `.env.sample`). The frontend never holds secrets.
