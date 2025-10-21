import os
import shutil
import uuid
from flask import Flask, request, render_template, jsonify
from agents.ingestion_agent import IngestionAgent
from agents.retrieval_agent import RetrievalAgent
from agents.llm_response_agent import LLMResponseAgent
from core.mcp_protocol import create_mcp_message

# --- Cleanup function to delete data on startup ---
def clear_data_on_startup():
    """Wipes the uploads and vector store directories for a clean session."""
    print("--- Clearing previous session data ---")
    uploads_folder = 'data/uploads'
    db_folder = 'data/chroma_db'

    if os.path.exists(uploads_folder):
        shutil.rmtree(uploads_folder)
        print(f"Deleted folder: {uploads_folder}")

    if os.path.exists(db_folder):
        try:
            shutil.rmtree(db_folder)
            print(f"Deleted folder: {db_folder}")
        except PermissionError:
            print(f"Could not delete {db_folder}. File is likely in use by the reloading server.")
    
    os.makedirs(uploads_folder, exist_ok=True)
    print("--- Data cleared. Starting with a clean state. ---")

clear_data_on_startup()

# --- Main Flask Application ---
app = Flask(__name__)
UPLOAD_FOLDER = 'data/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

agents = {
    "IngestionAgent": IngestionAgent(),
    "RetrievalAgent": RetrievalAgent(),
    "LLMResponseAgent": LLMResponseAgent()
}
chat_history = []

def route_message(message):
    """Routes an MCP message to the appropriate agent."""
    receiver_name = message['receiver']
    if receiver_name in agents:
        return agents[receiver_name].process_message(message)
    elif receiver_name == "Coordinator":
        return message
    return None

@app.route('/')
def index():
    """Renders the main chat interface."""
    return render_template('index.html', chat_history=chat_history)

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handles file uploads and triggers the ingestion agent."""
    if 'files' not in request.files: return jsonify({"error": "No files part"}), 400
    files = request.files.getlist('files')
    if not files or files[0].filename == '': return jsonify({"error": "No selected files"}), 400
    
    uploaded_paths = []
    for file in files:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        uploaded_paths.append(filepath)

    ingest_request = create_mcp_message(
        sender="Coordinator", receiver="IngestionAgent",
        msg_type="INGEST_REQUEST", payload={"file_paths": uploaded_paths}
    )
    response_from_ingestion = route_message(ingest_request)
    if response_from_ingestion:
        final_ingest_response = route_message(response_from_ingestion)
        if final_ingest_response and final_ingest_response.get('type') == 'INGEST_COMPLETE':
            return jsonify({"message": f"Successfully ingested {len(uploaded_paths)} file(s)."}), 200
    return jsonify({"error": "Ingestion process failed."}), 500

@app.route('/chat', methods=['POST'])
def chat():
    """Handles user chat messages and orchestrates the RAG pipeline."""
    user_query = request.json.get('message')
    if not user_query: return jsonify({"error": "Empty message"}), 400
    chat_history.append({"sender": "user", "text": user_query})
    
    retrieval_request = create_mcp_message(
        sender="Coordinator", receiver="RetrievalAgent",
        msg_type="RETRIEVAL_REQUEST", payload={"query": user_query}
    )
    
    # This is now the response from the RetrievalAgent
    response_from_retrieval = route_message(retrieval_request)
    
    if not response_from_retrieval:
        return jsonify({"error": "Retrieval process failed."}), 500

    # --- UPDATED LOGIC ---
    # Check if the RetrievalAgent handled it (as a greeting)
    if response_from_retrieval.get('type') == 'FINAL_RESPONSE':
        payload = response_from_retrieval['payload']
        chat_history.append({"sender": "bot", "text": payload['answer'], "sources": payload['sources']})
        return jsonify({"answer": payload['answer'], "sources": payload['sources']})
    
    # If not, it's a CONTEXT_RESPONSE, so route it to the LLMResponseAgent
    if response_from_retrieval.get('type') == 'CONTEXT_RESPONSE':
        final_response_message = route_message(response_from_retrieval)
        
        if not final_response_message or final_response_message.get('type') != 'FINAL_RESPONSE':
            return jsonify({"error": "Response generation failed."}), 500
        
        payload = final_response_message['payload']
        chat_history.append({"sender": "bot", "text": payload['answer'], "sources": payload['sources']})
        return jsonify({"answer": payload['answer'], "sources": payload['sources']})

    return jsonify({"error": "Unknown error in chat processing."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)