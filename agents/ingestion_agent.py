from .base_agent import BaseAgent
from core.doc_parser import parse_document
from core.mcp_protocol import create_mcp_message
from langchain_text_splitters import RecursiveCharacterTextSplitter # <-- THIS LINE IS UPDATED

class IngestionAgent(BaseAgent):
    """Agent responsible for ingesting and preprocessing documents."""
    def __init__(self, name="IngestionAgent"):
        super().__init__(name)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )

    def process_message(self, message):
        if message['type'] == 'INGEST_REQUEST':
            file_paths = message['payload']['file_paths']
            all_chunks = []
            
            for file_path in file_paths:
                text_content = parse_document(file_path)
                if text_content.startswith("Error"):
                    continue

                chunks = self.text_splitter.split_text(text_content)
                for chunk in chunks:
                    all_chunks.append({"text": chunk, "source": file_path})

            return create_mcp_message(
                sender=self.name,
                receiver="RetrievalAgent",
                msg_type="EMBED_AND_STORE_REQUEST",
                payload={"chunks": all_chunks},
                trace_id=message['trace_id']
            )
        return None