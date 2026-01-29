import time
import google.generativeai as genai
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.config import get_settings

settings = get_settings()

genai.configure(api_key=settings.gemini_api_key)

class KnowledgeBase:
    def __init__(self):
        # Initialize Qdrant
        self.client = QdrantClient(path=settings.chroma_db_dir)
        self.collection_name = "anantya_docs"
        
        # --- DYNAMIC SETUP START ---
        # 1. Check what dimension the API is actually returning
        # We use 'models/text-embedding-004' which is the latest stable version
        self.embedding_model = "models/text-embedding-004"
        
        try:
            print("Verifying embedding dimension...")
            test_embed = genai.embed_content(
                model=self.embedding_model,
                content="test",
                task_type="retrieval_document"
            )['embedding']
            actual_dim = len(test_embed)
            print(f"API is returning vectors of dimension: {actual_dim}")
        except Exception as e:
            print(f"Warning: Could not verify dimension. Defaulting to 768. Error: {e}")
            actual_dim = 768

        # 2. Check if collection exists
        collections = self.client.get_collections()
        collection_names = [c.name for c in collections.collections]

        if self.collection_name in collection_names:
            # 3. SAFETY CHECK: If existing collection has wrong size, DELETE IT
            info = self.client.get_collection(self.collection_name)
            if info.config.params.vectors.size != actual_dim:
                print(f"Mismatch! Collection has size {info.config.params.vectors.size}, but API has {actual_dim}.")
                print("Deleting old collection to recreate with correct size...")
                self.client.delete_collection(self.collection_name)
                collection_names.remove(self.collection_name)

        # 4. Create Collection if it doesn't exist
        if self.collection_name not in collection_names:
            print(f"Creating collection '{self.collection_name}' with size {actual_dim}...")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=actual_dim, distance=Distance.COSINE),
            )
        # --- DYNAMIC SETUP END ---

    def get_embeddings_batch(self, texts: list[str], retries=3) -> list[list[float]]:
        """
        Generate embeddings for a list of texts (Batch Mode).
        Includes retry logic for 429 errors.
        """
        for attempt in range(retries):
            try:
                result = genai.embed_content(
                    model=self.embedding_model,
                    content=texts,
                    task_type="retrieval_document",
                    title="Anantya Doc"
                )
                # Google API returns a dictionary. 'embedding' key contains the list of vectors.
                return result['embedding']
            
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower() or "resource" in str(e).lower():
                    wait_time = (attempt + 1) * 10  # Increase wait time: 10s, 20s, 30s
                    print(f"   Rate limit hit. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    print(f"   Error generating embeddings: {e}")
                    raise e
        
        raise Exception("Failed to get embeddings after retries")

    def upsert_documents(self, documents: list[str], metadatas: list[dict], ids: list[str]):
        """Upload data to Qdrant in Batches"""
        
        BATCH_SIZE = 10 
        total_docs = len(documents)
        
        print(f"Starting ingestion of {total_docs} documents in batches of {BATCH_SIZE}...")

        for i in range(0, total_docs, BATCH_SIZE):
            batch_docs = documents[i : i + BATCH_SIZE]
            batch_metas = metadatas[i : i + BATCH_SIZE]
            batch_ids = ids[i : i + BATCH_SIZE]
            
            print(f" - Processing batch {i//BATCH_SIZE + 1} (Docs {i} to {i+len(batch_docs)})...")

            try:
                batch_vectors = self.get_embeddings_batch(batch_docs)
                
                points = []
                for doc, meta, doc_id, vector in zip(batch_docs, batch_metas, batch_ids, batch_vectors):
                    points.append(PointStruct(
                        id=doc_id,
                        vector=vector,
                        payload={"text": doc, **meta}
                    ))
                
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                
                # Sleep slightly to stay safe
                time.sleep(1)

            except Exception as e:
                print(f"Error processing batch starting at index {i}: {e}")

    def search(self, query: str, n_results: int = 3) -> str:
        """Search Qdrant"""
        try:
            # Embed query
            query_vector = genai.embed_content(
                model=self.embedding_model,
                content=query,
                task_type="retrieval_query"
            )['embedding']

            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=n_results
            )

            if not search_result:
                return "No relevant information found in the knowledge base."

            context_parts = []
            for hit in search_result:
                source = hit.payload.get('source', 'Unknown')
                text = hit.payload.get('text', '')
                context_parts.append(f"[Source: {source}]\n{text}")

            return "\n\n".join(context_parts)
            
        except Exception as e:
            print(f"Search Error: {e}")
            return "Error searching knowledge base."