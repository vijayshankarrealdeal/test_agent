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

        # 1. Setup Embedding Model
        self.embedding_model = "gemini-embedding-001"

        # 2. Determine Dimension
        try:
            print("Verifying embedding dimension...")
            # Generate a dummy embedding to check size
            test_embed = genai.embed_content(
                model=self.embedding_model,
                content="test",
                task_type="retrieval_document",
            )["embedding"]
            actual_dim = len(test_embed)
        except Exception as e:
            print(f"Warning: Could not verify dimension. Defaulting to 768. Error: {e}")
            actual_dim = 768

        # 3. Ensure Collection Exists & Verify Size
        collections = self.client.get_collections()
        collection_names = [c.name for c in collections.collections]

        if self.collection_name in collection_names:
            info = self.client.get_collection(self.collection_name)
            if info.config.params.vectors.size != actual_dim:
                print(
                    f"Mismatch! Collection size {info.config.params.vectors.size} != API {actual_dim}. Resetting..."
                )
                self.client.delete_collection(self.collection_name)
                collection_names.remove(self.collection_name)

        if self.collection_name not in collection_names:
            print(
                f"Creating collection '{self.collection_name}' with size {actual_dim}..."
            )
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=actual_dim, distance=Distance.COSINE),
            )

    def get_embeddings_batch(self, texts: list[str], retries=3) -> list[list[float]]:
        """Generate embeddings with retry logic"""
        for attempt in range(retries):
            try:
                result = genai.embed_content(
                    model=self.embedding_model,
                    content=texts,
                    task_type="retrieval_document",
                    title="Anantya Doc",
                )
                return result["embedding"]
            except Exception as e:
                if (
                    "429" in str(e)
                    or "quota" in str(e).lower()
                    or "resource" in str(e).lower()
                ):
                    wait_time = (attempt + 1) * 10
                    print(f"   Rate limit hit. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise e
        raise Exception("Failed to get embeddings after retries")

    def upsert_documents(
        self, documents: list[str], metadatas: list[dict], ids: list[str]
    ):
        """Upload to Qdrant"""
        BATCH_SIZE = 10
        total = len(documents)
        print(f"Ingesting {total} documents...")

        for i in range(0, total, BATCH_SIZE):
            batch_docs = documents[i : i + BATCH_SIZE]
            batch_metas = metadatas[i : i + BATCH_SIZE]
            batch_ids = ids[i : i + BATCH_SIZE]

            print(f" - Batch {i // BATCH_SIZE + 1}")
            try:
                vectors = self.get_embeddings_batch(batch_docs)
                points = [
                    PointStruct(id=uid, vector=v, payload={"text": doc, **meta})
                    for uid, v, doc, meta in zip(
                        batch_ids, vectors, batch_docs, batch_metas
                    )
                ]
                self.client.upsert(collection_name=self.collection_name, points=points)
                time.sleep(1)  # Safety pause
            except Exception as e:
                print(f"Error in batch {i}: {e}")

    def search(self, query: str, n_results: int = 3) -> str:
        """Search using the Core API (query_points) to bypass attribute errors"""
        try:
            # 1. Embed Query
            query_vector = genai.embed_content(
                model=self.embedding_model, content=query, task_type="retrieval_query"
            )["embedding"]

            # 2. Execute Search (Using query_points instead of search)
            # 'query_points' is the underlying method that works even if 'search' mixin fails
            search_response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=n_results,
            )

            # 3. Process Results
            # query_points returns a QueryResponse object containing .points
            results = search_response.points

            if not results:
                return "No relevant information found in the knowledge base."

            context_parts = []
            for hit in results:
                # hit is a ScoredPoint
                source = hit.payload.get("source", "Unknown")
                text = hit.payload.get("text", "")
                context_parts.append(f"[Source: {source}]\n{text}")

            return "\n\n".join(context_parts)

        except AttributeError:
            # Fallback if query_points also has issues (very unlikely)
            return "Error: Database client configuration issue."
        except Exception as e:
            print(f"Search Error Details: {e}")
            return f"Error searching knowledge base: {str(e)}"
