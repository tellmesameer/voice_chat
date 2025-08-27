# services/llm.py
from openai import OpenAI
from config import settings
from logger_config import logger  # Import the logger

# Create an OpenAI client with your deepinfra token and endpoint
openai = OpenAI(
    api_key=settings.llm_api_key,
    base_url=settings.BASE_URL,
)

def generate_response(user_message: str, context: str) -> str:
    """
    Generate a response from the LLM based on the user message and context.
    """
    logger.info("Generating LLM response")
    
    try:
        prompt = f"""
        Context: {context}
        User: {user_message}
        Assistant:
        """
        logger.debug(f"Sending prompt to LLM: {prompt[:10]}...")
        
        chat_completion = openai.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Use the provided context to answer the user's question. Do not include emojis in your response."},
                {"role": "user", "content": prompt}
            ],
        )
        result = str(chat_completion.choices[0].message.content)
        logger.info(f"Generated LLM response: {result[:10]}...")
        return result
    except Exception as e:
        logger.error(f"Error generating LLM response: {e}")
        return "Sorry, I'm having trouble generating a response right now."