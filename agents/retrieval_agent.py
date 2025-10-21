import os
import uuid
import chromadb
from .base_agent import BaseAgent
from core.mcp_protocol import create_mcp_message
from agents.llm_response_agent import model # Import the LLM for classification

class RetrievalAgent(BaseAgent):
    """
    Agent for storing and retrieving chunks from a ChromaDB vector store.
    This agent also acts as a router to classify intent.
    """
    def __init__(self, name="RetrievalAgent"):
        super().__init__(name)
        db_path = os.path.join('data', 'chroma_db')
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="document_collection")
        print(f"[{self.name}] ChromaDB collection '{self.collection.name}' loaded with {self.collection.count()} documents.")

    def _classify_intent(self, query):
        """Uses the LLM to classify the user's intent."""
        if model is None:
            return "rag_query" # Default if model isn't working

        prompt = f"""
        Classify the user's query into one of two categories:
        1. "greeting": For simple hellos, goodbyes, thank yous, or other conversational pleasantries.
        2. "rag_query": For any questions that require looking up specific information, facts, or details.

        User Query: "{query}"
        Classification:
        """
        try:
            response = model.generate_content(prompt)
            classification = response.text.strip().lower()
            if "greeting" in classification:
                return "greeting"
            return "rag_query"
        except Exception as e:
            print(f"Error during intent classification: {e}")
            return "rag_query" # Default to RAG query on error

    def _store_chunks(self, chunks_with_metadata):
        """Stores chunks in the ChromaDB collection."""
        if not chunks_with_metadata: return
        documents = [chunk['text'] for chunk in chunks_with_metadata]
        metadatas = [{'source': chunk['source']} for chunk in chunks_with_metadata]
        ids = [str(uuid.uuid4()) for _ in chunks_with_metadata]
        self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
        print(f"[{self.name}] Storage complete. Collection now has {self.collection.count()} documents.")

    def _retrieve_context(self, query, top_k=5):
        """Retrieves context from the ChromaDB collection."""
        if self.collection.count() == 0: return []
        results = self.collection.query(query_texts=[query], n_results=min(top_k, self.collection.count()))
        retrieved_chunks = []
        if results and results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                retrieved_chunks.append({"text": doc, "source": results['metadatas'][0][i]['source']})
        return retrieved_chunks

    def process_message(self, message):
        msg_type, payload = message['type'], message['payload']
        
        if msg_type == 'EMBED_AND_STORE_REQUEST':
            self._store_chunks(payload['chunks'])
            return create_mcp_message(
                sender=self.name, receiver="Coordinator", msg_type="INGEST_COMPLETE",
                payload={"status": "success", "chunks_added": len(payload['chunks'])}, trace_id=message['trace_id']
            )
        
        elif msg_type == 'RETRIEVAL_REQUEST':
            query = payload['query']
            
            # --- NEW ROUTING LOGIC ---
            intent = self._classify_intent(query)
            print(f"[{self.name}] Classified intent as: {intent}")

            if intent == "greeting":
                # Handle greeting directly and skip retrieval
                return create_mcp_message(
                    sender=self.name,
                    receiver="Coordinator",
                    msg_type="FINAL_RESPONSE",
                    payload={"answer": "Hello! How can I help you with your documents?", "sources": []},
                    trace_id=message['trace_id']
                )
            
            # --- ORIGINAL RAG LOGIC ---
            # If it's a "rag_query", proceed as normal
            retrieved_context = self._retrieve_context(query)
            return create_mcp_message(
                sender=self.name, receiver="LLMResponseAgent", msg_type="CONTEXT_RESPONSE",
                payload={"retrieved_context": retrieved_context, "query": query}, trace_id=message['trace_id']
            )
        
        return None