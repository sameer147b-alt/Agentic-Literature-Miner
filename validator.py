"""
Agent 4 — The Validator
Performs biological cross-verification of hypotheses using UniProt API.
Graceful degradation: if UniProt returns 0 hits the hypothesis is kept
with status 'Review Required' and scored on literature alone.
"""

import json
import os
import time

# Fix Windows console encoding for medical/Greek characters
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import requests

from logger import get_logger

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, "hypotheses.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "validated_results.json")

UNIPROT_API_URL = "https://rest.uniprot.org/uniprotkb/search"

WEIGHT_LITERATURE = 0.6
WEIGHT_DATABASE = 0.4

log = get_logger("Validator")


# ---------------------------------------------------------------------------
# Core Logic
# ---------------------------------------------------------------------------


def query_uniprot(drug: str, pathways: list[str]) -> bool:
    """
    Query UniProt KB for protein entries matching the drug + pathway.
    Returns True if at least one entry is found.
    """
    if not pathways:
        return False

    pathway_query = " OR ".join([f'"{p}"' for p in pathways])
    query = f'({drug}) AND ({pathway_query}) AND (organism_id:9606)'
    
    params = {
        "query": query,
        "format": "json",
        "size": 1,
    }

    log.info(f"Querying UniProt: {query}")
    start = time.time()

    try:
        response = requests.get(UNIPROT_API_URL, params=params, timeout=10)
        elapsed = round(time.time() - start, 2)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            hit_count = len(results)
            log.info(f"[API] UniProt | 200 | {elapsed}s | {hit_count} hits")
            return hit_count > 0
        else:
            log.error(f"[API] UniProt | {response.status_code} | {elapsed}s | FAILED")
            return False

    except Exception as e:
        log.error(f"[API] UniProt | ERROR | {e}")
        return False


def calculate_score(confidence: int, db_match: bool) -> float:
    """
    Final Evidence Score (0.0 - 1.0).
    
    If db_match is True:
        score = confidence*0.6 + 1.0*0.4
    If db_match is False (graceful degradation):
        score = confidence*1.0  (literature-only baseline)
    """
    norm_confidence = min(max(confidence, 0), 100) / 100.0

    if db_match:
        return round((norm_confidence * WEIGHT_LITERATURE) + (1.0 * WEIGHT_DATABASE), 2)
    else:
        # Graceful degradation: score purely on literature evidence
        return round(norm_confidence * WEIGHT_LITERATURE, 2)


# ---------------------------------------------------------------------------
# Pipeline Entry Point
# ---------------------------------------------------------------------------


def run() -> str:
    """
    Execute Agent 4 (The Validator).

    1. Load hypotheses.json.
    2. For each hypothesis, query UniProt.
    3. Calculate final score (graceful degradation if no hits).
    4. Save validated_results.json — NEVER blank if hypotheses exist.
    """
    log.info("=" * 60)
    log.info("Validator agent started")
    log.info("=" * 60)

    if not os.path.exists(INPUT_FILE):
        log.error(f"Input file not found: {INPUT_FILE}")
        return ""

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        hypotheses = json.load(f)

    validated_results = []
    
    for item in hypotheses:
        drug = item.get("drug", "")
        disease = item.get("target_disease", "")
        pathways = item.get("shared_pathways", [])
        confidence = item.get("confidence_score", 0)

        log.info(f"Verifying: {drug} → {disease}")

        # Cross-check
        db_confirmed = query_uniprot(drug, pathways)
        
        if db_confirmed:
            validation_status = "✅ Confirmed"
        else:
            validation_status = "⚠️ Review Required"
            log.warning(
                f"[GRACEFUL] No UniProt match for {drug} — "
                f"marking as 'Review Required', scoring on literature only"
            )

        # Score
        final_score = calculate_score(confidence, db_confirmed)

        # Build result record — hypothesis is ALWAYS preserved
        result = item.copy()
        result["uniprot_validation"] = {
            "confirmed": db_confirmed,
            "status": validation_status,
            "evidence_link": f"https://www.uniprot.org/uniprotkb?query={drug} AND {' OR '.join(pathways)}",
        }
        result["final_evidence_score"] = final_score

        validated_results.append(result)

    # Save — table is NEVER blank if hypotheses were generated
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(validated_results, f, indent=2, ensure_ascii=False)

    log.info(f"Saved {len(validated_results)} validated results to {OUTPUT_FILE}")
    log.info(f"[HANDOFF] Validator → Interface | payload={OUTPUT_FILE}")
    log.info("Validator agent finished")
    
    return OUTPUT_FILE


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    output = run()
    if output:
        print(f"\n✅ Validation complete. Results saved to: {output}")
    else:
        print("\n❌ Validation failed.")
