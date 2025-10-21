import os
import google.generativeai as genai
from .base_agent import BaseAgent
from core.mcp_protocol import create_mcp_message

# --- Configure the Gemini API ---
# IMPORTANT: PASTE YOUR PRIVATE API KEY AND MODEL NAME HERE
try:
    GOOGLE_API_KEY = "AIzaSyAz39c7NPFcJ4LE1wdg0oGT0xK_TSLDMpM"
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('models/gemini-pro-latest')
except Exception as e:
    print(f"Error configuring Google AI: {e}")
    model = None

def get_llm_response(query, context):
    """Generates a response using the Gemini LLM."""
    if model is None:
        return "The AI model is not configured. Please check your API key.", []
    if not context:
        return "I could not find any relevant information in the documents to answer your question.", []

    context_str = "\n".join([f"Source: {os.path.basename(chunk['source'])}\nContent: {chunk['text']}\n---" for chunk in context])
    prompt = f"""
    You are a helpful assistant. Answer the user's question based ONLY on the context provided below.
    If the information is not in the context, say "I could not find the answer in the provided documents."
    Do not make up answers. Be concise and directly answer the question.

    CONTEXT:
    {context_str}

    QUESTION:
    {query}

    ANSWER:
    """
    try:
        response = model.generate_content(prompt)
        answer = response.text
    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        answer = "Sorry, I encountered an error while generating a response."
    
    sources = list(set([os.path.basename(chunk['source']) for chunk in context]))
    return answer, sources

class LLMResponseAgent(BaseAgent):
    """Agent that generates a final answer using a real LLM and retrieved context."""
    def __init__(self, name="LLMResponseAgent"):
        super().__init__(name)

    def process_message(self, message):
        if message['type'] == 'CONTEXT_RESPONSE':
            query = message['payload']['query']
            context = message['payload']['retrieved_context']
            answer, sources = get_llm_response(query, context)
            return create_mcp_message(
                sender=self.name,
                receiver="Coordinator",
                msg_type="FINAL_RESPONSE",
                payload={"answer": answer, "sources": sources},
                trace_id=message['trace_id']
            )
        return None