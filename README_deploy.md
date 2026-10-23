# Running frontend + backend as ONE service (single place)

Put these two files in the **same folder** of one repo:
- backend_app.py
- index.html
- requirements.txt

`backend_app.py` now serves `index.html` itself at `/`, so you deploy **only
the backend** (one Render/Railway/Fly service) and there is no separate
Netlify site at all. The page's OTP calls use relative URLs (`/send-otp`,
`/verify-otp`), which automatically hit the same server — no backend URL to
paste in, and no CORS problem, because browser and API share one origin.

## Deploy (Render example)
1. Push this folder to a GitHub repo.
2. Render → New → Web Service → connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn backend_app:app`
5. Add environment variables: `SMTP_EMAIL`, `SMTP_PASSWORD` (a 16-character
   Gmail **App Password**, not your normal Gmail password).
6. Deploy. Your whole app (site + API) is now at the one Render URL.

If you ever DO want to keep them separate again (frontend on Netlify,
backend on Render), open index.html and set:
```js
const OTP_API_BASE = "https://your-backend.onrender.com";
```
