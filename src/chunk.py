import argparse
import json
from pathlib import Path


DEFAULT_INPUT = Path("data/processed/documents.json")
DEFAULT_OUTPUT = Path("data/chunks/documents.json")


def chunk_document(doc, target_word_min=350, target_word_max=500, overlap_word_target=75):
    paragraphs = [p.strip() for p in doc["clean_text"].split("\n") if p.strip()]
    
    if not paragraphs:
        return []

    chunks = []
    curr_paras = []
    curr_word_count = 0
    chunk_index = 0

    for p in paragraphs:
        p_words = p.split()
        p_word_count = len(p_words)
        
        # If adding this paragraph exceeds the maximum word limit,
        # we save the current chunk and start a new one with overlap.
        if curr_word_count + p_word_count > target_word_max and curr_paras:
            # Save current chunk
            chunk_text = "\n".join(curr_paras)
            chunks.append({
                "id": f"{doc['id']}_chunk{chunk_index:02d}",
                "document_id": doc["id"],
                "title": doc["title"],
                "url": doc["url"],
                "chunk_index": chunk_index,
                "text": chunk_text,
                "word_count": curr_word_count
            })
            chunk_index += 1
            
            # Build the overlap from the end of the current chunk
            overlap_paras = []
            overlap_word_count = 0
            for prev_p in reversed(curr_paras):
                prev_p_word_count = len(prev_p.split())
                if overlap_word_count + prev_p_word_count > overlap_word_target and overlap_paras:
                    break
                overlap_paras.insert(0, prev_p)
                overlap_word_count += prev_p_word_count
            
            # Start new chunk with overlap paragraphs and current paragraph
            curr_paras = overlap_paras + [p]
            curr_word_count = overlap_word_count + p_word_count
        else:
            curr_paras.append(p)
            curr_word_count += p_word_count

    # Save any remaining paragraphs as the final chunk
    if curr_paras:
        chunk_text = "\n".join(curr_paras)
        chunks.append({
            "id": f"{doc['id']}_chunk{chunk_index:02d}",
            "document_id": doc["id"],
            "title": doc["title"],
            "url": doc["url"],
            "chunk_index": chunk_index,
            "text": chunk_text,
            "word_count": curr_word_count
        })

    return chunks


def main():
    parser = argparse.ArgumentParser(description="Chunk cleaned documents using paragraph boundaries.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    with args.input.open("r", encoding="utf-8") as file:
        documents = json.load(file)

    all_chunks = []
    for doc in documents:
        chunks = chunk_document(doc)
        all_chunks.extend(chunks)
        print(f"Document {doc['id']} ('{doc['title']}') split into {len(chunks)} chunks.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as file:
        json.dump(all_chunks, file, indent=2, ensure_ascii=False)
        file.write("\n")

    print(f"\nSuccessfully generated {len(all_chunks)} chunks saved to {args.output}")


if __name__ == "__main__":
    main()
