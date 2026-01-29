import json
import os
from app.database import ChromaKnowledgeBase

# Ensure data directory exists
DATA_FILE = "data/source_data.jsonl"

def load_data():
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found. Please create it.")
        return

    print("Initializing Database...")
    db = ChromaKnowledgeBase()
    
    docs = []
    metadatas = []
    ids = []
    
    print(f"Reading {DATA_FILE}...")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                item = json.loads(line)
                
                # Extract fields based on your JSONL structure
                doc_id = item.get("id")
                text = item.get("text")
                meta = item.get("metadata", {})
                
                if doc_id and text:
                    ids.append(doc_id)
                    docs.append(text)
                    # Chroma requires metadata values to be str, int, float, or bool
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
    # Create dummy data if file doesn't exist for testing
    if not os.path.exists("data"):
        os.makedirs("data")
        
    # Run ingestion
    load_data()
