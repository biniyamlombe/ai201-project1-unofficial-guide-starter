import os
import argparse
import sys
from pathlib import Path
# Add workspace root to system path to enable 'src.' imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

import chromadb
from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer

from src.retrieve import retrieve


# Load environment variables
dotenv_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
DEFAULT_DB_DIR = "data/chroma_db"
COLLECTION_NAME = "yale_dining_guide"
DEFAULT_MODEL = "llama-3.3-70b-versatile"


def generate_answer(query_str, collection, embed_model, groq_client, model_name=DEFAULT_MODEL, k=4, retrieval_method="semantic"):
    # 1. Retrieve relevant chunks based on chosen method
    if retrieval_method == "semantic":
        results = retrieve(query_str, collection, embed_model, k=k)
    elif retrieval_method == "keyword":
        from src.hybrid_retrieve import get_bm25_searcher
        bm25_searcher = get_bm25_searcher()
        bm25_results = bm25_searcher.search(query_str, top_n=k)
        results = []
        for score, chunk in bm25_results:
            results.append({
                "id": chunk["id"],
                "distance": 1.0,
                "metadata": {
                    "document_id": chunk["document_id"],
                    "title": chunk["title"],
                    "url": chunk["url"],
                    "chunk_index": chunk["chunk_index"],
                },
                "document": chunk["text"],
                "bm25_score": score
            })
    elif retrieval_method == "hybrid":
        from src.hybrid_retrieve import hybrid_retrieve
        results = hybrid_retrieve(query_str, collection, embed_model, k=k)
    else:
        raise ValueError(f"Unknown retrieval method: {retrieval_method}")
    
    # 2. Format context
    context_parts = []
    for res in results:
        meta = res["metadata"]
        context_parts.append(
            f"Source Title: {meta['title']}\n"
            f"Source URL: {meta['url']}\n"
            f"Chunk ID: {res['id']}\n"
            f"Content:\n{res['document']}\n"
        )
    context_text = "\n---\n".join(context_parts)

    # 3. Construct system prompt for strict grounding
    system_prompt = """You are a helpful and precise Yale campus dining assistant. Your goal is to answer the user's question using ONLY the provided text context.

Strict grounding guidelines:
1. Your answer must be directly supported by and derived ONLY from the provided text context.
2. Do NOT use any outside knowledge, assumptions, or extrapolations. Do not make up facts or details.
3. If the provided context does not contain the answer, you must state exactly: "I do not have enough information in my source documents to answer this question."
4. Format your answer clearly and cite your sources. Surround inline citations with square brackets, referencing the exact "Source Title" from the context (e.g., [Berkeley Dining] or [Explore Meal Plans]).
5. If the source information is from the Bon Appétit article, cite it as [Bon Appétit article].
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Context:\n{context_text}\n\nQuestion: {query_str}"
        }
    ]

    # 4. Call Groq API (with temperature 0.0 for deterministic grounding)
    try:
        completion = groq_client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.0
        )
        answer = completion.choices[0].message.content
    except Exception as e:
        answer = f"Error calling Groq API: {e}"

    return answer, results


def run_evaluations(collection, embed_model, groq_client, retrieval_method="semantic"):
    queries = [
        "How many residential dining halls does Yale describe as part of its dining system?",
        "What does the Full meal plan include for undergraduate students?",
        "Which meal plan is designed for off-campus undergraduate students, and what does it include?",
        "What makes Berkeley dining distinctive according to Yale Hospitality?",
        "What does the project corpus say about wait times at Yale dining halls?"
    ]

    print("=" * 80)
    print(f"RUNNING END-TO-END EVALUATION ({retrieval_method.upper()} SEARCH)")
    print("=" * 80)

    for i, query in enumerate(queries, 1):
        print(f"\nQUESTION #{i}: '{query}'")
        print("-" * 60)
        answer, sources = generate_answer(query, collection, embed_model, groq_client, retrieval_method=retrieval_method)
        print(f"ANSWER:\n{answer}")
        print("-" * 60)
        print("SOURCES RETRIEVED:")
        for rank, res in enumerate(sources, 1):
            meta = res["metadata"]
            if "rrf_score" in res:
                print(f"  {rank}. {meta['title']} (RRF: {res['rrf_score']:.6f} | Dist: {res['distance']:.4f})")
            elif "bm25_score" in res:
                print(f"  {rank}. {meta['title']} (BM25: {res['bm25_score']:.4f})")
            else:
                print(f"  {rank}. {meta['title']} (Distance: {res['distance']:.4f})")
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Query the Yale Dining RAG pipeline and generate grounded answers.")
    parser.add_argument("query", nargs="?", type=str, help="Optional query string to answer a single question.")
    parser.add_argument("--db-dir", type=str, default=DEFAULT_DB_DIR)
    parser.add_argument("--collection", type=str, default=COLLECTION_NAME)
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--method", type=str, default="semantic", choices=["semantic", "keyword", "hybrid"], help="Retrieval method to use")
    args = parser.parse_args()

    if not GROQ_API_KEY:
        print("Error: GROQ_API_KEY environment variable not found in .env. Please check your config.")
        return

    # 1. Initialize client and load collection
    db_client = chromadb.PersistentClient(path=args.db_dir)
    try:
        collection = db_client.get_collection(name=args.collection)
    except Exception:
        print(f"Error: Collection '{args.collection}' not found. Did you run embed_and_index.py first?")
        return

    # 2. Load embed model and Groq client
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    groq_client = Groq(api_key=GROQ_API_KEY)

    # 3. Execute
    if args.query:
        print(f"Query: '{args.query}' (Method: {args.method})\n")
        answer, sources = generate_answer(args.query, collection, embed_model, groq_client, model_name=args.model, retrieval_method=args.method)
        print(f"Answer:\n{answer}\n")
        print("Sources:")
        for res in sources:
            meta = res["metadata"]
            if "rrf_score" in res:
                print(f"- {meta['title']} ({meta['url']}) [RRF: {res['rrf_score']:.6f} | Dist: {res['distance']:.4f}]")
            elif "bm25_score" in res:
                print(f"- {meta['title']} ({meta['url']}) [BM25: {res['bm25_score']:.4f}]")
            else:
                print(f"- {meta['title']} ({meta['url']}) [Distance: {res['distance']:.4f}]")
    else:
        run_evaluations(collection, embed_model, groq_client, retrieval_method=args.method)


if __name__ == "__main__":
    main()
