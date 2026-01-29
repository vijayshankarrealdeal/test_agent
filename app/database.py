import chromadb
from chromadb.utils import embedding_functions
from app.config import get_settings

settings = get_settings()

class ChromaKnowledgeBase:
    def __init__(self):
        # PersistentClient saves data to disk
        self.client = chromadb.PersistentClient(path=settings.chroma_db_dir)
        
        # Default sentence-transformers model
        self.ef = embedding_functions.DefaultEmbeddingFunction()
        
        self.collection = self.client.get_or_create_collection(
            name="anantya_docs", 
            embedding_function=self.ef
        )

    def upsert_documents(self, documents: list[str], metadatas: list[dict], ids: list[str]):
        """Add or update documents in the vector store."""
        self.collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def search(self, query: str, n_results: int = 3) -> str:
        """Search for relevant documents."""
        results = self.collection.query(
            query_texts=[query], 
            n_results=n_results
        )
        
        if not results['documents'] or not results['documents'][0]:
            return "No relevant information found in the knowledge base."
            
        # Combine the results into a single string context
        context_parts = []
        for i, doc in enumerate(results['documents'][0]):
            meta = results['metadatas'][0][i] if results['metadatas'] else {}
            source = meta.get('source', 'Unknown')
            context_parts.append(f"[Source: {source}]\n{doc}")
            
        return "\n\n".join(context_parts)
