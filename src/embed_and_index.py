import argparse
import json
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer


DEFAULT_INPUT = Path("data/chunks/documents.json")
DEFAULT_DB_DIR = "data/chroma_db"
COLLECTION_NAME = "yale_dining_guide"


def main():
    parser = argparse.ArgumentParser(description="Embed chunks and index them in ChromaDB.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db-dir", type=str, default=DEFAULT_DB_DIR)
    parser.add_argument("--collection", type=str, default=COLLECTION_NAME)
    args = parser.parse_args()

    # 1. Load the chunks
    print(f"Loading chunks from {args.input}...")
    with args.input.open("r", encoding="utf-8") as file:
        chunks = json.load(file)
    print(f"Loaded {len(chunks)} chunks.")

    # 2. Load the embedding model
    print("Initializing SentenceTransformer('all-MiniLM-L6-v2')...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # 3. Compute embeddings
    print("Computing embeddings for chunks (this runs locally)...")
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True)
    # Convert numpy array to list of lists for ChromaDB
    embeddings_list = embeddings.tolist()

    # 4. Set up persistent ChromaDB client
    print(f"Initializing ChromaDB client at {args.db_dir}...")
    client = chromadb.PersistentClient(path=args.db_dir)

    # 5. Create or recreate the collection
    try:
        print(f"Deleting existing collection '{args.collection}' if it exists...")
        client.delete_collection(name=args.collection)
    except Exception:
        # Collection might not exist yet
        pass

    print(f"Creating new collection '{args.collection}'...")
    collection = client.create_collection(name=args.collection)

    # 6. Prepare data for insertion
    ids = [c["id"] for c in chunks]
    metadatas = [
        {
            "document_id": c["document_id"],
            "title": c["title"],
            "url": c["url"],
            "chunk_index": c["chunk_index"],
        }
        for c in chunks
    ]

    # 7. Add to ChromaDB
    print(f"Adding {len(chunks)} documents to ChromaDB collection...")
    collection.add(
        ids=ids,
        embeddings=embeddings_list,
        metadatas=metadatas,
        documents=texts
    )

    print(f"\nSuccessfully indexed {len(chunks)} chunks in ChromaDB under collection '{args.collection}'.")


if __name__ == "__main__":
    main()
