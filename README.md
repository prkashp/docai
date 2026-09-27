# OCR Learning Pipeline: Tesseract + LangChain + Milvus

A containerized pipeline for learning OCR (Optical Character Recognition) workflows using open-source tools. Extract text from scanned documents, chunk and embed them, store in a vector database, and perform semantic search.

## What You'll Learn

- **OCR with Tesseract**: Extract raw text from scanned images using the popular Tesseract engine
- **Text Chunking**: Split long documents into semantic chunks using LangChain's recursive splitter
- **Embeddings**: Convert text to dense vectors using sentence transformers (local, no API keys needed)
- **Vector Databases**: Store and query embeddings in Milvus, a scalable vector DB
- **Semantic Search**: Find similar documents/chunks based on meaning, not keywords
- **Docker containerization**: Everything runs in containers, no local setup friction

## Architecture

```
Scanned Image → Tesseract OCR → Raw Text → Chunking → Embeddings → Milvus Vector DB
                                                                         ↓
                                                         Query → Similarity Search → Results
```

**Stack:**
- **OCR**: Tesseract (via pytesseract)
- **Chunking & Embeddings**: LangChain + sentence-transformers (all-MiniLM-L6-v2)
- **Vector DB**: Milvus (with etcd + MinIO dependencies)
- **Container Orchestration**: Docker Compose

## Quick Start

### 1. Prepare Images

Place scanned image files (`.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff`) in the `images/` directory:

```bash
cp /path/to/your/scans/* ./images/
```

For testing, you can generate synthetic images with text:

```bash
python3 << 'EOF'
from PIL import Image, ImageDraw, ImageFont

img = Image.new('RGB', (800, 600), color='white')
draw = ImageDraw.Draw(img)
draw.text((50, 50), "Sample claim document.\nPolicy #12345\nAmount: $500", fill='black')
img.save('images/test_document.png')
EOF
```

### 2. Start the Pipeline

```bash
# Build and start Milvus + app container
docker compose up -d --build

# Verify Milvus is healthy (wait 10-15 seconds)
docker compose exec app curl http://milvus:9091/healthz
```

### 3. Ingest Images

```bash
# OCR all images, chunk, embed, and store in Milvus
docker compose exec app python src/ingest.py
```

You should see output like:
```
Processing test_document.png...
test_document.png: 1 chunks
Total chunks: 1
Ingestion complete! Stored 1 chunks in Milvus.
```

### 4. Search

```bash
# Semantic search for related content
docker compose exec app python src/search.py "insurance claim"

# Search with custom result count
docker compose exec app python src/search.py "policy number" 5
```

Output shows source file, similarity score (0-1, higher = more similar), and matched text snippets.

## Project Structure

```
./
├── requirements.txt          # Python dependencies
├── Dockerfile                # Python 3.9 + Tesseract
├── docker-compose.yml        # Milvus + app services
├── .env.example              # Environment variable template
├── images/                   # Place scanned documents here
│   └── .gitkeep
├── src/
│   ├── ocr.py               # Tesseract extraction
│   ├── vectorstore.py        # Milvus connection & setup
│   ├── ingest.py            # OCR + embedding + ingestion pipeline
│   └── search.py            # CLI semantic search
└── README.md                 # This file
```

## Configuration

Create a `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
```

**Variables:**
- `MILVUS_HOST`: Host to connect to Milvus (default: `milvus` for Docker Compose)
- `MILVUS_PORT`: gRPC port (default: `19530`)
- `COLLECTION_NAME`: Milvus collection name (default: `ocr_documents`)

## Troubleshooting

### Milvus fails to start

Check logs:
```bash
docker compose logs milvus
```

Milvus needs etcd and MinIO to be healthy first. Wait 15-20 seconds and retry `docker compose ps`.

### "No module named pytesseract"

The container hasn't built yet. Run:
```bash
docker compose up -d --build
```

### "No such file or directory: images/"

Create the folder:
```bash
mkdir -p images
touch images/.gitkeep
```

### Empty text from OCR

- **Check image quality**: Tesseract struggles with low-contrast or rotated scans
- **Next steps to learn**: Preprocess images (binarization, deskew, upscaling) in `src/ocr.py` before OCR
- **Example**: Use OpenCV to threshold and rotate images for better recognition

## Next Steps to Extend

1. **Image Preprocessing**
   - Binarization (black text on white background)
   - Deskewing (rotation correction)
   - Upscaling (low-res images)
   - Remove artifacts (shadows, coffee stains)
   - See: OpenCV, scikit-image

2. **Better Embeddings**
   - Swap `sentence-transformers` for domain-specific models (e.g., SciBERT for papers, LayoutLM for forms)
   - Use OpenAI or Anthropic embeddings (add API key to `.env`)

3. **Structured Extraction**
   - Use an LLM (Claude, GPT) via LangChain to extract fields (claim #, amount, date)
   - Store structured metadata in Milvus alongside vectors

4. **Metadata & Filtering**
   - Add `date_scanned`, `document_type`, `status` to metadata
   - Perform hybrid search: semantic similarity + metadata filters

5. **Web Interface**
   - Build a FastAPI/Flask app wrapping `search.py`
   - Add file upload for on-the-fly OCR and search

6. **Scaling**
   - Replace Milvus Lite with a production Milvus cluster
   - Add authentication, monitoring, backups
   - Integrate with Kafka for streaming OCR jobs

## Key Files to Understand

- **`src/ocr.py`**: Where Tesseract is called; modify here to add preprocessing
- **`src/vectorstore.py`**: Milvus connection setup; swap embedding models here
- **`src/ingest.py`**: The orchestration logic; adjust chunking strategy here
- **`src/search.py`**: Query interface; modify output formatting here

## Learning References

- [Tesseract OCR](https://github.com/UB-Mannheim/pytesseract)
- [LangChain Text Splitters](https://python.langchain.com/docs/modules/data_connection/document_loaders/how_to/split_code)
- [Sentence Transformers](https://www.sbert.net/)
- [Milvus Documentation](https://milvus.io/docs)
- [LangChain Milvus Integration](https://python.langchain.com/docs/integrations/vectorstores/milvus)

## Cleanup

Stop all containers and remove volumes:

```bash
docker compose down -v
```

Remove just containers (keep data):

```bash
docker compose down
```
## License

Learning project. Use freely.
