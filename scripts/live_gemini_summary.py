"""Summary transport uses the same bounded Gemini transport with its own wire schema."""

from live_gemini_judge import LiveGeminiJudge

from src.applications.tillegal.agents.response.schemas import LLM_OUTPUT_SCHEMA


class LiveGeminiSummary(LiveGeminiJudge):
    output_schema = LLM_OUTPUT_SCHEMA
