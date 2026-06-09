import argparse
import chromadb
from sentence_transformers import SentenceTransformer


DEFAULT_DB_DIR = "data/chroma_db"
COLLECTION_NAME = "yale_dining_guide"


def retrieve(query_str, collection, model, k=4):
    # Embed the query
    query_vector = model.encode(query_str).tolist()
    
    # Query the ChromaDB collection
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=k
    )
    
    # Format the results
    formatted_results = []
    
    # Chroma collection query results are nested lists
    ids = results["ids"][0]
    distances = results["distances"][0]
    metadatas = results["metadatas"][0]
    documents = results["documents"][0]
    
    for idx in range(len(ids)):
        formatted_results.append({
            "id": ids[idx],
            "distance": distances[idx],
            "metadata": metadatas[idx],
            "document": documents[idx]
        })
        
    return formatted_results


def run_evaluations(collection, model):
    queries = [
        "How many residential dining halls does Yale describe as part of its dining system?",
        "What does the Full meal plan include for undergraduate students?",
        "Which meal plan is designed for off-campus undergraduate students, and what does it include?",
        "What makes Berkeley dining distinctive according to Yale Hospitality?",
        "What does the project corpus say about wait times at Yale dining halls?"
    ]
    
    print("=" * 80)
    print("RUNNING RETRIEVAL EVALUATION")
    print("=" * 80)
    
    for i, query in enumerate(queries, 1):
        print(f"\nQUERY #{i}: '{query}'")
        print("-" * 60)
        
        results = retrieve(query, collection, model, k=4)
        
        for rank, res in enumerate(results, 1):
            meta = res["metadata"]
            print(f"Rank {rank} | Chunk: {res['id']} | Distance: {res['distance']:.4f}")
            print(f"Source: {meta['title']} ({meta['url']})")
            print("Content Snippet:")
            # Print first few lines of the text, indented
            preview = "\n".join("  " + line for line in res["document"].splitlines()[:6])
            print(preview)
            if len(res["document"].splitlines()) > 6:
                print("  ...")
            print("-" * 40)
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Query the Yale Dining retrieval index.")
    parser.add_argument("query", nargs="?", type=str, help="Optional query string to run a single query.")
    parser.add_argument("--db-dir", type=str, default=DEFAULT_DB_DIR)
    parser.add_argument("--collection", type=str, default=COLLECTION_NAME)
    parser.add_argument("-k", type=int, default=4, help="Number of results to retrieve")
    args = parser.parse_args()

    # 1. Initialize client and load collection
    client = chromadb.PersistentClient(path=args.db_dir)
    try:
        collection = client.get_collection(name=args.collection)
    except Exception as e:
        print(f"Error: Collection '{args.collection}' not found. Did you run embed_and_index.py first?")
        return

    # 2. Load model
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # 3. Execute
    if args.query:
        print(f"Retrieving top-{args.k} matches for: '{args.query}'\n")
        results = retrieve(args.query, collection, model, k=args.k)
        for rank, res in enumerate(results, 1):
            meta = res["metadata"]
            print(f"Rank {rank} | Chunk: {res['id']} | Distance: {res['distance']:.4f}")
            print(f"Source: {meta['title']} ({meta['url']})")
            print(f"Text:\n{res['document']}\n")
            print("-" * 60)
    else:
        run_evaluations(collection, model)


if __name__ == "__main__":
    main()
