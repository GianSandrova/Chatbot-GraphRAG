# === generation/__init__.py ===
"""
Unified entry for the answer generation pipeline.
"""
from generation.prompt_builder import build_prompt
from generation.groq_client import call_groq_api
from config import GROQ_API_KEY, GROQ_MODEL

def generate_answer(query_text, context, history=None):
    """
    Generate answer using Groq API based on the provided context and query.

    Args:
        query_text (str): The user's question.
        context (str): Retrieved chunk context.
        history (list): Optional list of previous (question, answer) pairs.

    Returns:
        str: Generated answer.
    """
    prompt = build_prompt(query_text, context, history or [])
    return call_groq_api(prompt)
