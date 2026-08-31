"""LLM providers and the unified fallback client (§7)."""

# The system prompt asks for answers under 250 words (~350 tokens), so this is
# roughly 2x headroom. It is deliberately not larger: Groq's free tier budgets
# 8000 tokens per minute and counts max_tokens as a reservation, so every token
# reserved here is one fewer available for the next question.
DEFAULT_MAX_TOKENS = 700
