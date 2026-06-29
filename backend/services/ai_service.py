
import structlog
from anthropic import Anthropic
from groq import Groq

from backend.core.config import settings

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are CarbonLens AI, an expert carbon accountant and supply chain optimization virtual assistant.
You help sustainability officers, supply chain analysts, and business executives understand their carbon footprint, analyze Scope 1, 2, and 3 emissions, and run optimization scenarios to reduce their greenhouse gas emissions.

Use realistic numbers and terms (e.g. DEFRA factors, tCO2e, ESG scoring, transport intensity).
Keep your answers professional, actionable, and structured with clear headings or bullet points where appropriate.
If the user asks about calculations, explain that CarbonLens uses DEFRA factors:
- Road freight: 0.10621 kg CO2e/tonne-km
- Air freight: 0.60210 kg CO2e/tonne-km
- Sea freight: 0.01570 kg CO2e/tonne-km
- Rail freight: 0.02750 kg CO2e/tonne-km
"""


class AIService:
    @staticmethod
    async def generate_response(
        messages: list[dict[str, str]], provider: str = "groq"
    ) -> str:
        """Generate AI chat response using Groq or Anthropic, with a mock fallback if keys are missing."""
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({"role": msg["role"], "content": msg["content"]})

        # Check Groq provider
        if provider == "groq" and settings.GROQ_API_KEY and settings.GROQ_API_KEY != "gsk_your_groq_api_key_here":
            try:
                client = Groq(api_key=settings.GROQ_API_KEY)
                full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + formatted_messages
                
                chat_completion = client.chat.completions.create(
                    messages=full_messages, # type: ignore
                    model="llama-3.3-70b-versatile",
                    temperature=0.7,
                    max_tokens=1024,
                )
                return chat_completion.choices[0].message.content or "No response received."
            except Exception as e:
                logger.error("groq_api_error", error=str(e))
                # Fall back to Anthropic or Mock if Groq fails
                if not settings.ANTHROPIC_API_KEY:
                    return AIService._mock_response(messages[-1]["content"])

        # Check Anthropic provider
        if (provider == "anthropic" or not settings.GROQ_API_KEY) and settings.ANTHROPIC_API_KEY:
            try:
                anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                
                # Format system prompt separate for Anthropic
                response = anthropic_client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=1024,
                    system=SYSTEM_PROMPT,
                    messages=formatted_messages, # type: ignore
                    temperature=0.7,
                )
                return response.content[0].text
            except Exception as e:
                logger.error("anthropic_api_error", error=str(e))
                return AIService._mock_response(messages[-1]["content"])

        # Mock fallback (when no API keys are configured)
        return AIService._mock_response(messages[-1]["content"])

    @staticmethod
    def _mock_response(user_query: str) -> str:
        """Returns realistic sustainability answers when LLM keys are absent."""
        query = user_query.lower()
        if "scope" in query:
            return (
                "### Scope 1, 2, and 3 Breakdown\n\n"
                "Based on the standards, your emissions are classified as:\n"
                "- **Scope 1 (Direct)**: Fuel combustion, company vehicle emissions, and fugitive gases.\n"
                "- **Scope 2 (Indirect - Purchased Energy)**: Emissions from electricity, steam, and cooling purchased by your offices.\n"
                "- **Scope 3 (Value Chain)**: Upstream and downstream logistics, supplier production impact, and employee commutes.\n\n"
                "In CarbonLens, you can monitor this split in the **Dashboard** page and download an executive report under **Reports**."
            )
        elif "supplier" in query or "esg" in query or "acme" in query:
            return (
                "### Supplier Emissions and ESG Metrics\n\n"
                "Analyzing your supply chain partners shows that:\n"
                "- **Sourcing locally** (e.g. within country boundaries) reduces transport Scope 3 emissions significantly.\n"
                "- Implementing ESG audits (with goals to raise ESG scores above 80) can reduce carbon intensity by up to **22%**.\n"
                "- Converting air freight routes to rail/sea reduces freight emissions by up to **95%** (DEFRA factor for air: `0.60210 kg/t-km` vs sea: `0.01570 kg/t-km`)."
            )
        elif "optimize" in query or "path" in query or "transport" in query:
            return (
                "### Supply Chain Carbon Optimization\n\n"
                "Using our operations-research models, we recommend:\n"
                "1. **Route Consolidation**: Group shipments to shift from road freight (`0.10621 kg CO2e/t-km`) to rail (`0.02750 kg CO2e/t-km`).\n"
                "2. **Alternative Sourcing**: Source materials like steel (intensity: `1.85 kg CO2e/kg`) or cement (`0.92 kg CO2e/kg`) from suppliers with active decarbonization plans.\n"
                "3. **Supplier Relocation**: Move critical nodes closer to ports or regions with green energy grids (e.g. UK grid: `0.20710 kg CO2e/kWh` vs IN grid: `0.71000 kg CO2e/kWh`)."
            )
        else:
            return (
                "### Welcome to CarbonLens AI Support\n\n"
                "I am here to help you audit and optimize your carbon footprint. You can ask me:\n"
                "- *'How can I optimize our supply chain transport carbon?'*\n"
                "- *'What are the carbon differences between UK and India electricity grids?'*\n"
                "- *'Explain my Scope 3 emissions calculations.'*\n\n"
                "*(Please note: AI is running in offline simulation mode. Add `GROQ_API_KEY` in `.env` to enable live LLM integration).*"
            )
        
