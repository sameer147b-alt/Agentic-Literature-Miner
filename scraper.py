import json
import os
import shutil
import sys
import time
from datetime import datetime

# Fix Windows console encoding for medical/Greek characters
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from Bio import Entrez, Medline

from logger import get_logger

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

Entrez.email = "sameer.147b@gmail.com"

MAX_RESULTS = 50
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "raw_data.json")

log = get_logger("Scraper")


# ---------------------------------------------------------------------------
# Clean Data Wipe
# ---------------------------------------------------------------------------


def clean_previous_run():
    """
    Autonomously delete stale artefacts so old disease data never bleeds
    into new searches.
    """
    targets = [
        os.path.join(DATA_DIR, "raw_data.json"),
        os.path.join(BASE_DIR, "hypotheses.json"),
        os.path.join(BASE_DIR, "validated_results.json"),
    ]
    dir_targets = [
        os.path.join(BASE_DIR, "vector_db"),
    ]

    for path in targets:
        if os.path.exists(path):
            os.remove(path)
            log.info(f"[CLEAN] Deleted {os.path.basename(path)}")

    for d in dir_targets:
        if os.path.exists(d):
            shutil.rmtree(d)
            log.info(f"[CLEAN] Deleted directory {os.path.basename(d)}/")


# ---------------------------------------------------------------------------
# Core Functions
# ---------------------------------------------------------------------------


def search_pubmed(query: str, max_results: int = MAX_RESULTS) -> list[str]:
    """Search PubMed and return a list of PMIDs for the given query."""
    log.info(f"Searching PubMed: '{query}' (max_results={max_results})")
    start = time.time()

    try:
        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
        record = Entrez.read(handle)
        handle.close()

        pmids = record.get("IdList", [])
        elapsed = round(time.time() - start, 3)
        log.info(f"[API] PubMed esearch | 200 | {elapsed}s | {len(pmids)} PMIDs")
        return pmids

    except Exception as exc:
        elapsed = round(time.time() - start, 3)
        log.error(f"[API] PubMed esearch | FAILED | {elapsed}s | {exc}")
        return []


def fetch_abstracts(pmids: list[str]) -> list[dict]:
    """Fetch full abstract records for a list of PMIDs."""
    if not pmids:
        return []

    log.info(f"Fetching abstracts for {len(pmids)} PMIDs …")
    start = time.time()

    try:
        handle = Entrez.efetch(
            db="pubmed", id=",".join(pmids), rettype="medline", retmode="text"
        )
        records = list(Medline.parse(handle))
        handle.close()

        results = []
        for rec in records:
            results.append(
                {
                    "pmid": rec.get("PMID", ""),
                    "title": rec.get("TI", ""),
                    "abstract": rec.get("AB", ""),
                    "authors": rec.get("AU", []),
                    "date": rec.get("DP", ""),
                }
            )

        elapsed = round(time.time() - start, 3)
        log.info(
            f"[API] PubMed efetch  | 200 | {elapsed}s | {len(results)} abstracts"
        )
        return results

    except Exception as exc:
        elapsed = round(time.time() - start, 3)
        log.error(f"[API] PubMed efetch  | FAILED | {elapsed}s | {exc}")
        return []


def save_results(abstracts: list[dict], path: str = OUTPUT_FILE) -> str:
    """Persist fetched abstracts to a JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(abstracts, f, indent=2, ensure_ascii=False)
    log.info(f"Saved {len(abstracts)} abstracts → {path}")
    return path


# ---------------------------------------------------------------------------
# Pipeline Entry Point
# ---------------------------------------------------------------------------


def run(
    search_terms: list[str] | None = None,
    max_results: int = MAX_RESULTS,
) -> str:
    """
    Execute the Scraper agent pipeline.

    1. Clean previous run data.
    2. Search PubMed for each term.
    3. Fetch abstracts for all discovered PMIDs.
    4. Save to data/raw_data.json.
    5. Return the output file path (handoff payload for the Indexer).
    """
    log.info("=" * 60)
    log.info("Scraper agent started")
    log.info("=" * 60)

    # Step 0 — Clean slate
    clean_previous_run()

    terms = search_terms or [
        "drug repurposing AND gene interaction",
        "metformin AND AMPK",
        "aspirin AND COX2 AND cancer",
    ]

    log.info(f"Search terms: {terms}")

    all_pmids: list[str] = []
    for term in terms:
        pmids = search_pubmed(term, max_results)
        all_pmids.extend(pmids)
        time.sleep(0.34)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_pmids: list[str] = []
    for pid in all_pmids:
        if pid not in seen:
            seen.add(pid)
            unique_pmids.append(pid)

    log.info(f"Total unique PMIDs collected: {len(unique_pmids)}")

    abstracts = fetch_abstracts(unique_pmids)
    output_path = save_results(abstracts)

    log.info(f"[HANDOFF] Scraper → Indexer | payload={output_path}")
    log.info("Scraper agent finished")

    return output_path


# ---------------------------------------------------------------------------
# CLI  —  python scraper.py "metformin leukemia"
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Accept dynamic query from command line; fallback to defaults
    query = sys.argv[1] if len(sys.argv) > 1 else ""

    if query.strip():
        parts = query.strip().split()
        terms = [
            query,  # exact phrase
            f"{parts[0]} AND {' AND '.join(parts[1:])} AND repurposing"
            if len(parts) > 1
            else f"{parts[0]} repurposing",
            f"{parts[0]} AND cancer" if len(parts) >= 1 else query,
        ]
    else:
        terms = None  # uses defaults inside run()

    result_path = run(search_terms=terms)
    print(f"\n✅ Done. Abstracts saved to: {result_path}")

