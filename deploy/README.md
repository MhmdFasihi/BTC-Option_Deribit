# Deployment (qortfolio / Streamlit)

This folder holds the **public-safe** deployment assets for the Streamlit app:

- `docker-compose.vps.yml` — runs the Streamlit app + Redis, published on
  `127.0.0.1:8501` only (a shared host nginx fronts it).
- `nginx/qortfolio.com.conf` — host nginx vhost for `qortfolio.com` / `www`.
- `nginx/snippets/cloudflare-origin.conf` — TLS via a Cloudflare Origin cert.
- `.env.example` — copy to `.env` on the server and fill in (never commit `.env`).

> The full operations runbook (server bootstrap, Cloudflare steps, the new VPS
> origin IP, the shared edge nginx that also fronts `app.qortfolio.com`, and the
> verification scripts) lives in the **private `qortfolio-v2` repo** under
> `deploy/`. Infra details and the origin IP are deliberately kept out of this
> public repo so they don't weaken Cloudflare's origin protection.

## Quick start (on the VPS)
```bash
cp deploy/.env.example .env && nano .env        # fill Deribit creds + SECRET_KEY
docker compose -f deploy/docker-compose.vps.yml --env-file .env up -d --build
curl -fsS http://127.0.0.1:8501/_stcore/health  # -> ok
```
Then enable the `qortfolio.com` vhost in the shared host nginx (see the private
ops runbook).
