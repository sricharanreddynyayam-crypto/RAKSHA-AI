# RakshaAI Deployment Guide

## Deploy to Render

1. Push this repository to GitHub.
2. Go to Render dashboard and connect your GitHub repo.
3. Create a new **Web Service**.
4. Use the following settings:
   - Root directory: `backend`
   - Environment: `Python`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Health check path: `/health`
5. Render will give you a public domain like `https://<your-service>.onrender.com`.
6. Open the public URL and use `/share` to let friends send location data. The live dashboard is admin-only and requires `/dashboard?admin_token=YOUR_SECRET`.

By default, the admin secret is `rakshaai-admin-secret`. Set a stronger value with the `ADMIN_SECRET` environment variable in Render.

## Deploy to Railway

1. Push your repo to GitHub.
2. Connect the repo in Railway.
3. Select `backend` as the deployment folder.
4. Railway usually detects Python automatically. If needed, use the `Procfile`:
   ```text
   web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
   ```
5. Deploy and use the generated Railway URL.
6. Share this URL with friends.

## Public Pages

The app now includes:
- `/` → public landing page
- `/share` → mobile-friendly location sharing page
- `/dashboard?admin_token=YOUR_SECRET` → live tracking dashboard (admin-only)

## Notes

- The backend stores user sessions in memory, so live tracking does not persist after a restart.
- A permanent domain will be assigned by Render or Railway once deployed.
- On deployment, send the public URL to friends so they can use the app from any city.
