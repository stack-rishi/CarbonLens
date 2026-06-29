## Step 1: Create Supabase Project
1. Go to https://supabase.com → New Project
2. Name: "carbonlens-prod"
3. Database password: generate strong one, save it
4. Region: Southeast Asia (Singapore) — closest to India
5. Wait for project to provision (~2 min)

## Step 2: Get credentials
Project Settings → API:
  - Project URL → SUPABASE_URL
  - anon public → SUPABASE_ANON_KEY  
  - service_role → SUPABASE_SERVICE_ROLE_KEY
Project Settings → Database → Connection string (URI mode, Transaction pooler):
  - Replace [YOUR-PASSWORD] with your password → DATABASE_URL
  - Change postgresql:// to postgresql+asyncpg://

## Step 3: Enable required extensions
Go to Database → Extensions → Enable:
  - uuid-ossp (for gen_random_uuid())
  - pg_trgm (for text search later)

## Step 4: Run migrations
In your local terminal with .env filled:
  cd backend
  poetry run alembic upgrade head

## Step 5: Seed data
  poetry run python seed.py

## Step 6: Verify in Supabase dashboard
Table Editor → check these tables exist with data:
  organizations, users, suppliers, emission_records, 
  supply_chain_edges, reports, ai_conversations
