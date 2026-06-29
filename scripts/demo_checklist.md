## CarbonLens Demo Checklist

### Before the demo (30 min before):
- [ ] Open http://localhost:5173 and verify it loads
- [ ] Sign in with admin@acmecorp.com
- [ ] Verify Dashboard shows KPI cards with real data (not zeros)
- [ ] Open Supply Chain map → all 5 supplier nodes visible
- [ ] Click one node → drawer opens with charts
- [ ] Run route optimizer: select two suppliers, click optimize
      → should show mode comparison table
- [ ] Go to Chat → ask "Which supplier has highest emissions?"
      → Groq should respond within 2 seconds
- [ ] Go to Reports → generate a new report
      → wait 30-60 seconds → Download PDF
      → open PDF and verify it has all 5 pages
- [ ] Check /health endpoint returns {"status":"ok","db":"connected"}

### Demo flow (5 minutes):
1. (30s) Open dashboard — "This is our real-time emission dashboard"
   Point to Scope 1/2/3 KPIs and the trend chart

2. (60s) Go to Supply Chain map
   "Here's our supply chain — each node is a supplier, 
   color shows emission intensity"
   Click on the reddest node → show drawer with history + forecast
   "This supplier's emissions are projected to increase 15% next quarter"

3. (60s) Run route optimizer
   "We can optimize any shipment for carbon"
   Select two suppliers, submit
   "Switching from air to sea freight saves X kg CO2 — that's Y% reduction"

4. (60s) Ask AI copilot a question
   Type: "Which 3 actions would reduce our Scope 3 by 20%?"
   Wait for Groq response
   "Our AI analyst, powered by real emission data"

5. (60s) Generate PDF report
   Click Generate, select this year
   "One click generates a GHG Protocol compliant report"
   Show the PDF — cover page, charts, supplier table

6. (30s) Closing
   "This is production-ready — live database, real optimization, 
   deployed on Fly.io and Vercel. Zero infrastructure cost."
