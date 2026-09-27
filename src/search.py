import sys
from vectorstore import get_vectorstore

def search(query: str, k: int = 3):
    print(f"Searching for: '{query}'")
    print("-" * 60)

    vectorstore = get_vectorstore()

    try:
        results = vectorstore.similarity_search_with_score(query, k=k)

        if not results:
            print("No results found.")
            return

        for i, (doc, score) in enumerate(results, 1):
            metadata = doc.metadata
            source = metadata.get("source", "unknown")
            chunk_index = metadata.get("chunk_index", "unknown")

            print(f"\n[Result {i}]")
            print(f"Source: {source} (chunk {chunk_index})")
            print(f"Similarity Score: {score:.4f}")
            print(f"Content:\n{doc.page_content[:300]}...")
            print("-" * 60)

    except Exception as e:
        print(f"Error during search: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python search.py '<query>' [k]")
        print("Example: python search.py 'insurance claim' 5")
        sys.exit(1)

    query = sys.argv[1]
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    search(query, k=k)
