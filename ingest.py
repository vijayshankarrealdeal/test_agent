import json
import os
import uuid
from app.database import KnowledgeBase

# Ensure data directory exists
DATA_FILE = "data/anantya_embeddings_data.jsonl"

def load_data():
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found. Please create it.")
        return

    print("Initializing Database (Qdrant)...")
    db = KnowledgeBase()
    
    docs = []
    metadatas = []
    ids = []
    
    print(f"Reading {DATA_FILE}...")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                item = json.loads(line)
                
                doc_id = item.get("id")
                # Qdrant prefers UUIDs. If your ID is a string, let's hash it or use a valid UUID.
                # If your JSON has valid UUID strings, this is fine. 
                # If not, we generate one to be safe.
                if not doc_id:
                    doc_id = str(uuid.uuid4())
                
                text = item.get("text")
                meta = item.get("metadata", {})
                
                if text:
                    ids.append(doc_id)
                    docs.append(text)
                    metadatas.append(meta)
            except json.JSONDecodeError:
                print("Skipping invalid JSON line")

    if docs:
        print(f"Embedding and storing {len(docs)} documents...")
        db.upsert_documents(documents=docs, metadatas=metadatas, ids=ids)
        print("Success! Data ingested.")
    else:
        print("No valid data found to ingest.")

if __name__ == "__main__":
    if not os.path.exists("data"):
        os.makedirs("data")
    load_data()