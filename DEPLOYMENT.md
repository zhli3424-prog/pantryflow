# PantryFlow deployment

The smallest public-demo setup is:

- **Frontend:** Netlify static site
- **Backend:** Render Python web service
- **Database:** SQLite for a disposable demo; a Render persistent disk for durable single-instance storage

## 1. Deploy the API on Render

The repository includes `render.yaml`. Create a Render Blueprint from the GitHub repository, then set:

```text
CORS_ORIGINS=https://YOUR_NETLIFY_SITE.netlify.app
```

Keep `AI_PROVIDER=mock` for a public portfolio demo. This avoids exposing a paid model key to anonymous traffic and keeps the demo reproducible.

The API health check is:

```text
https://YOUR_RENDER_SERVICE.onrender.com/api/v1/health
```

### SQLite persistence

Render's default filesystem is ephemeral. With the included free Blueprint, SQLite data can disappear after a deploy or restart. This is acceptable only for a clearly labeled disposable demo.

For durable single-instance storage, attach a paid Render persistent disk at `/var/data` and set:

```dotenv
DATABASE_URL=sqlite:////var/data/cooking_assistant.db
```

SQLite with a disk cannot safely scale to multiple application instances. A future multi-user product should move to managed PostgreSQL; that migration is intentionally outside this MVP.

## 2. Deploy the frontend on Netlify

Import the same GitHub repository. Netlify reads the included `netlify.toml`, builds `frontend`, and publishes `frontend/dist`. The SPA fallback is already configured for React Router routes.

Set this Netlify environment variable before deploying:

```dotenv
VITE_API_BASE_URL=https://YOUR_RENDER_SERVICE.onrender.com/api/v1
```

Vite embeds `VITE_*` variables at build time. Redeploy the frontend after changing this value.

## 3. Verify the public demo

1. Open the Render health endpoint and confirm `success: true`.
2. Open the Netlify site in a private browser window.
3. Add demo ingredients and generate a menu.
4. Open a recipe, complete it, and confirm inventory/history updates.
5. Refresh a nested URL such as `/recommendations` to verify the SPA redirect.
6. Confirm browser developer tools show no CORS or mixed-content errors.

## Security boundary

- Never place `AI_API_KEY` in Netlify; frontend environment variables are public.
- Store backend secrets only in Render environment settings.
- Do not use a real paid-model key for an unrestricted anonymous demo without rate limiting.
- The current demo has no accounts, so all visitors share one backend inventory. Label it as a disposable sandbox.
