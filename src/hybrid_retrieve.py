import sys
import re
import json
from pathlib import Path
from rank_bm25 import BM25Okapi

# Add workspace root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.retrieve import retrieve

DEFAULT_CHUNKS_PATH = Path("data/chunks/documents.json")


def clean_tokenize(text):
    """
    Tokenizes text by lowercasing and extracting alphanumeric words.
    This creates clean keywords for BM25 matching.
    """
    text = text.lower()
    return re.findall(r"\b\w+\b", text)


class BM25Searcher:
    def __init__(self, chunks_path=DEFAULT_CHUNKS_PATH):
        with chunks_path.open("r", encoding="utf-8") as file:
            self.chunks = json.load(file)
            
        # Tokenize the documents
        tokenized_corpus = [clean_tokenize(c["text"]) for c in self.chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)

    def search(self, query_str, top_n=10):
        tokenized_query = clean_tokenize(query_str)
        scores = self.bm25.get_scores(tokenized_query)
        
        # Pair scores with chunks and sort descending
        ranked_chunks = []
        for idx, score in enumerate(scores):
            ranked_chunks.append((score, self.chunks[idx]))
            
        ranked_chunks.sort(key=lambda x: x[0], reverse=True)
        return ranked_chunks[:top_n]


# Instantiate a singleton searcher in-memory
_bm25_searcher = None


def get_bm25_searcher():
    global _bm25_searcher
    if _bm25_searcher is None:
        _bm25_searcher = BM25Searcher()
    return _bm25_searcher


def hybrid_retrieve(query_str, collection, embed_model, k=4, rrf_k=60):
    """
    Retrieves chunks using Reciprocal Rank Fusion (RRF) on Semantic & BM25 results.
    """
    # 1. Fetch top 10 semantic results
    semantic_results = retrieve(query_str, collection, embed_model, k=10)
    
    # 2. Fetch top 10 keyword (BM25) results
    bm25_searcher = get_bm25_searcher()
    bm25_results = bm25_searcher.search(query_str, top_n=10)
    
    # 3. Apply Reciprocal Rank Fusion
    rrf_scores = {}
    chunk_map = {}
    
    # Process semantic ranks
    for rank, res in enumerate(semantic_results, 1):
        chunk_id = res["id"]
        chunk_map[chunk_id] = res
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
        
    # Process BM25 ranks
    for rank, (score, chunk) in enumerate(bm25_results, 1):
        chunk_id = chunk["id"]
        
        # If chunk is not in our map yet, construct its search entry
        if chunk_id not in chunk_map:
            chunk_map[chunk_id] = {
                "id": chunk["id"],
                "distance": 1.0,  # Max distance (unmatched semantically)
                "metadata": {
                    "document_id": chunk["document_id"],
                    "title": chunk["title"],
                    "url": chunk["url"],
                    "chunk_index": chunk["chunk_index"],
                },
                "document": chunk["text"]
            }
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
        
    # 4. Sort all items by combined RRF score
    sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
    
    # 5. Extract top k results
    top_k_results = []
    for cid in sorted_ids[:k]:
        item = chunk_map[cid]
        # Append combined RRF score metadata
        item["rrf_score"] = rrf_scores[cid]
        top_k_results.append(item)
        
    return top_k_results


if __name__ == "__main__":
    # Small test CLI for checking hybrid retrieval output
    import argparse
    from sentence_transformers import SentenceTransformer
    import chromadb
    
    parser = argparse.ArgumentParser(description="Test hybrid search CLI")
    parser.add_argument("query", type=str, help="Query string")
    args = parser.parse_args()
    
    client = chromadb.PersistentClient(path="data/chroma_db")
    collection = client.get_collection(name="yale_dining_guide")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    print(f"Testing Hybrid Search for: '{args.query}'\n")
    results = hybrid_retrieve(args.query, collection, model, k=4)
    for rank, res in enumerate(results, 1):
        print(f"Rank {rank} | Chunk: {res['id']} | RRF Score: {res['rrf_score']:.6f} | Distance: {res['distance']:.4f}")
        print(f"Source: {res['metadata']['title']}")
        print(f"Snippet: {res['document'][:150]}...")
        print("-" * 50)
