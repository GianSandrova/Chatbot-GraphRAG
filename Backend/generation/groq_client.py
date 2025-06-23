# generation/groq_client.py
"""
Send completion request to Groq's LLM API using config values.
"""
import requests
from config import GROQ_API_KEY, GROQ_MODEL

def call_groq_api(prompt):
    """
    Send a chat completion request to Groq API.

    Args:
        prompt (str): The prompt to send.

    Returns:
        str: Generated response or fallback message.
    """
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 10000
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    except Exception as e:
        print(f"❌ Groq API error: {str(e)}")
        return "⚠️ Gagal mendapatkan respons dari AI."
