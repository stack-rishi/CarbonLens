## Deploy Backend to Fly.io (Free tier)

### One-time setup:
1. Install flyctl: https://fly.io/docs/hands-on/install-flyctl/
2. fly auth login
3. cd carbonlens
4. fly launch --name carbonlens-api --region sin --no-deploy
   (say NO to postgres, NO to redis when prompted)

### Set secrets (run once):
fly secrets set \
  DATABASE_URL="your_database_url" \
  SUPABASE_URL="your_supabase_url" \
  SUPABASE_ANON_KEY="your_anon_key" \
  SUPABASE_SERVICE_ROLE_KEY="your_service_role_key" \
  GROQ_API_KEY="your_groq_key" \
  SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
  ENVIRONMENT="production" \
  FRONTEND_URL="https://your-vercel-url.vercel.app"

### Deploy:
fly deploy

### Verify:
curl https://carbonlens-api.fly.dev/health

---

## Deploy Frontend to Vercel (Free tier)

### One-time setup:
1. Push repo to GitHub (public or private)
2. Go to https://vercel.com → New Project
3. Import your GitHub repo
4. Framework: Vite
5. Root directory: frontend
6. Build command: npm run build
7. Output directory: dist

### Environment variables in Vercel dashboard:
VITE_API_URL = https://carbonlens-api.fly.dev/api/v1

### Deploy:
Push to main branch → auto-deploys
