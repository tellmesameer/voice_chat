# services/llm.py

from openai import OpenAI
from config import settings


# Create an OpenAI client with your deepinfra token and endpoint
openai = OpenAI(
    api_key=settings.llm_api_key,
    base_url=settings.BASE_URL,
)

def generate_response(user_message: str, context: str) -> str:
    """
    Generate a response from the LLM based on the user message and context.
    """
    try:
        prompt = f"""
        Context: {context}

        User: {user_message}
        Assistant:
        """

        chat_completion = openai.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Use the provided context to answer the user's question."},
                {"role": "user", "content": prompt}
            ],
        )

        result=str(chat_completion.choices[0].message.content)
        return result
    except Exception as e:
        print(f"Error generating LLM response: {e}")
        return "Sorry, I'm having trouble generating a response right now."