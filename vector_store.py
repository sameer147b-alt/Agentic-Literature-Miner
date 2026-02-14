"""
Agent 2 — The Architect (Indexer)
RAG Infrastructure: cleans abstracts, chunks text, generates embeddings
with GoogleGenerativeAIEmbeddings, and builds a FAISS vector store.
"""

import json
import os
import re
import time

from dotenv import load_dotenv

load_dotenv()

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
# from langchain_google_genai import GoogleGenerativeAIEmbeddings  <-- REMOVED due to quota limits
from langchain_huggingface import HuggingFaceEmbeddings

from logger import get_logger

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RAW_DATA_FILE = os.path.join(DATA_DIR, "raw_data.json")
VECTOR_DB_DIR = os.path.join(os.path.dirname(__file__), "vector_db")

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Local embeddings — free, fast, no rate limits
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

log = get_logger("Indexer")


# ---------------------------------------------------------------------------
# Data Cleaning
# ---------------------------------------------------------------------------

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def clean_text(text: str) -> str:
    """Strip HTML tags, collapse whitespace, and trim."""
    text = _HTML_TAG_RE.sub(" ", text)           # remove HTML tags
    text = re.sub(r"\s+", " ", text)             # collapse whitespace
    return text.strip()


def load_and_clean(path: str = RAW_DATA_FILE) -> list[Document]:
    """
    Load raw_data.json, drop entries with empty abstracts,
    clean the remaining text, and return LangChain Documents.
    """
    if not os.path.exists(path):
        log.error(f"Raw data file not found: {path}")
        return []

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    log.info(f"Loaded {len(raw)} entries from {path}")

    documents: list[Document] = []
    skipped = 0
    for entry in raw:
        abstract = entry.get("abstract", "").strip()
        if not abstract:
            skipped += 1
            continue

        cleaned = clean_text(abstract)
        metadata = {
            "pmid": entry.get("pmid", ""),
            "title": clean_text(entry.get("title", "")),
            "authors": ", ".join(entry.get("authors", [])),
            "date": entry.get("date", ""),
        }
        documents.append(Document(page_content=cleaned, metadata=metadata))

    log.info(
        f"Cleaning complete: {len(documents)} valid abstracts, {skipped} empty/skipped"
    )
    return documents


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def chunk_documents(documents: list[Document]) -> list[Document]:
    """
    Split documents using RecursiveCharacterTextSplitter.
    500-char chunks with 50-char overlap to preserve biological context.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    log.info(
        f"Chunking complete: {len(documents)} docs → {len(chunks)} chunks "
        f"(size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})"
    )
    return chunks


# ---------------------------------------------------------------------------
# Embeddings & Index
# ---------------------------------------------------------------------------


def get_embeddings() -> HuggingFaceEmbeddings:
    """Initialise local HuggingFace embeddings (no API key needed)."""
    log.info(f"Initialising local embedding model: {EMBEDDING_MODEL_NAME}")
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)


def build_index(chunks: list[Document], embeddings=None) -> FAISS:
    """Create a FAISS index from chunked documents."""
    if embeddings is None:
        embeddings = get_embeddings()

    log.info(f"Building FAISS index from {len(chunks)} chunks …")
    start = time.time()

    index = FAISS.from_documents(chunks, embeddings)

    elapsed = round(time.time() - start, 2)
    log.info(f"[INDEX] FAISS index built in {elapsed}s")
    return index


def save_index(index: FAISS, path: str = VECTOR_DB_DIR) -> None:
    """Persist the FAISS index to disk."""
    os.makedirs(path, exist_ok=True)
    index.save_local(path)
    log.info(f"[INDEX] Saved FAISS index → {path}")


def load_index(path: str = VECTOR_DB_DIR) -> FAISS:
    """Reload a previously saved FAISS index."""
    embeddings = get_embeddings()
    index = FAISS.load_local(path, embeddings, allow_dangerous_deserialization=True)
    log.info(f"[INDEX] Loaded FAISS index ← {path}")
    return index


def query_index(index: FAISS, query: str, k: int = 5) -> list[Document]:
    """Return the top-k most similar documents for the given query."""
    log.info(f"[QUERY] '{query}' (k={k})")
    results = index.similarity_search(query, k=k)
    log.info(f"[QUERY] Returned {len(results)} results")
    return results


# ---------------------------------------------------------------------------
# Pipeline Entry Point
# ---------------------------------------------------------------------------


def run(raw_data_path: str = RAW_DATA_FILE) -> str:
    """
    Execute the Indexer agent pipeline (Agent 2).

    1. Load & clean raw_data.json.
    2. Chunk abstracts (500 chars / 50 overlap).
    3. Generate embeddings with GoogleGenerativeAIEmbeddings.
    4. Build FAISS index → vector_db/.
    5. Log success with total chunk count.
    6. Return the index directory (handoff payload for the Reasoner).
    """
    log.info("=" * 60)
    log.info("Indexer agent (The Architect) started")
    log.info("=" * 60)

    # Step 1 — Load & clean
    documents = load_and_clean(raw_data_path)
    if not documents:
        log.warning("No documents to index. Aborting.")
        return ""

    # Step 2 — Chunk
    chunks = chunk_documents(documents)

    # Step 3 & 4 — Embed & build index
    embeddings = get_embeddings()
    index = build_index(chunks, embeddings)

    # Step 5 — Save & verify
    save_index(index)
    log.info(
        f"✅ Indexer verification: {len(chunks)} chunks successfully indexed "
        f"into {VECTOR_DB_DIR}"
    )

    log.info(f"[HANDOFF] Indexer → Reasoner | payload={VECTOR_DB_DIR}")
    log.info("Indexer agent finished")
    return VECTOR_DB_DIR


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    result = run()
    if result:
        print(f"\n✅ Done. FAISS index saved to: {result}")
    else:
        print("\n⚠️  No data found. Run scraper.py first.")
