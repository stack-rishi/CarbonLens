## Get Free Groq API Key

1. Go to https://console.groq.com
2. Sign up (free, no credit card)
3. API Keys → Create API Key
4. Name: "carbonlens-hackathon"
5. Copy key → paste into .env as GROQ_API_KEY
6. Free tier: 14,400 requests/day, 30 req/min on llama-3.1-70b-versatile
   This is more than enough for a hackathon demo.

Verify it works:
  curl -X POST https://api.groq.com/openai/v1/chat/completions \
    -H "Authorization: Bearer $GROQ_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"model":"llama-3.1-70b-versatile","messages":[{"role":"user","content":"hello"}],"max_tokens":10}'
