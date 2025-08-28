# services/llm.py
from openai import OpenAI
from config import settings
from logger_config import logger  # Import the logger

openai = OpenAI(
    api_key=settings.llm_api_key,
    base_url=settings.BASE_URL,
)

DEFAULT_LLM_MODEL = "openai/gpt-oss-120b"

def generate_response(user_message: str, context: str) -> str:
    """
    Generate a response from the LLM based on the user message and context.
    Defensive parsing for multiple possible SDK response shapes.
    """
    logger.info("Generating LLM response")
    try:
        prompt = f"Context:\n{context}\n\nUser: {user_message}\nAssistant:"
        logger.debug("Prepared prompt to LLM (len=%d)", len(prompt))

        # Use chat/completions API if available
        completion = openai.chat.completions.create(
            model=DEFAULT_LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Use the context to answer concisely."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=None,
        )

        # extract text robustly
        try:
            result = completion.choices[0].message.content
        except Exception:
            # fallback to dict-like shape
            if isinstance(completion, dict):
                choices = completion.get("choices", [])
                if choices:
                    # some responses put text under 'text'
                    result = choices[0].get("message", {}).get("content") or choices[0].get("text")
                else:
                    result = ""
            else:
                result = str(completion)

        result = result or "Sorry, I couldn't generate a response."
        logger.info("LLM response generated (len=%d)", len(result))
        return str(result)
    except Exception as e:
        logger.exception("Error generating LLM response: %s", e)
        return "Sorry, I'm having trouble generating a response right now."
