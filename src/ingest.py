import os
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from ocr import extract_text_from_directory
from vectorstore import get_vectorstore, COLLECTION_NAME

IMAGES_DIR = "images"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

def ingest_images():
    print("Starting OCR ingestion pipeline...")

    extracted_docs = extract_text_from_directory(IMAGES_DIR)

    if not extracted_docs:
        print("No images found. Exiting.")
        return

    print(f"\nExtracted text from {len(extracted_docs)} image(s)")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )

    all_documents = []
    for filename, text in extracted_docs.items():
        if not text.strip():
            print(f"Skipping {filename} - no text extracted")
            continue

        chunks = splitter.split_text(text)
        print(f"{filename}: {len(chunks)} chunks")

        for i, chunk in enumerate(chunks):
            all_documents.append({
                "text": chunk,
                "metadata": {
                    "source": filename,
                    "chunk_index": i,
                }
            })

    if not all_documents:
        print("No chunks to ingest. Exiting.")
        return

    print(f"\nTotal chunks: {len(all_documents)}")
    print("Connecting to Milvus and ingesting documents...")

    vectorstore = get_vectorstore()

    texts = [doc["text"] for doc in all_documents]
    metadatas = [doc["metadata"] for doc in all_documents]

    ids = vectorstore.add_texts(texts=texts, metadatas=metadatas)

    print(f"\nIngestion complete! Stored {len(ids)} chunks in Milvus.")
    print(f"Collection: {COLLECTION_NAME}")

if __name__ == "__main__":
    ingest_images()
