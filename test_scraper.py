"""Broader test run for the Scraper agent — multiple search terms to reach ~20 abstracts."""
import os
import scraper

OUTPUT_PATH = os.path.join(scraper.DATA_DIR, "raw_data.json")

BROAD_TERMS = [
    "metformin AND leukemia",
    "metformin cancer repurposing",
    "metformin drug repurposing AND hematologic",
]

scraper.log.info("=" * 60)
scraper.log.info("Broad test run: 3 queries, max 20 each")
scraper.log.info("=" * 60)

all_pmids = []
for term in BROAD_TERMS:
    pmids = scraper.search_pubmed(term, max_results=20)
    all_pmids.extend(pmids)
    import time; time.sleep(0.34)

# Deduplicate
seen, unique = set(), []
for pid in all_pmids:
    if pid not in seen:
        seen.add(pid)
        unique.append(pid)

scraper.log.info(f"Total unique PMIDs after dedup: {len(unique)}")

# Cap at 20
unique = unique[:20]
scraper.log.info(f"Fetching top {len(unique)} abstracts")

abstracts = scraper.fetch_abstracts(unique)
result = scraper.save_results(abstracts, path=OUTPUT_PATH)

scraper.log.info(f"[HANDOFF] Scraper → Indexer | payload={result}")
print(f"\n✅ Done. {len(abstracts)} abstracts saved to: {result}")
