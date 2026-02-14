"""
Agent 3 — The Strategist (Reasoner)
Uses Gemini 2.5 Flash with Chain-of-Thought reasoning to identify
drug repurposing opportunities from the vector store.
Supports dynamic input: python strategist.py "Metformin Leukemia"
"""

import json
import os
import sys

# Fix Windows console encoding for medical/Greek characters
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
import time

from dotenv import load_dotenv

load_dotenv()

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

import vector_store
from logger import get_logger

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_NAME = "gemini-2.5-flash"
THINKING_BUDGET = 8192

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hypotheses.json")

log = get_logger("Reasoner")


# ---------------------------------------------------------------------------
# Core Logic
# ---------------------------------------------------------------------------


def get_llm() -> ChatGoogleGenerativeAI:
    """
    Initialize Gemini 2.5 Flash with thinking config.
    Fetches API key securely from environment.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not found in environment.")

    log.info(f"Initialising LLM: {MODEL_NAME} (thinking_budget={THINKING_BUDGET})")

    return ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=api_key,
        temperature=0.7,
        model_kwargs={
            "generation_config": {
                "thinking_config": {
                    "include_thoughts": True,
                    "thinking_budget_token_count": THINKING_BUDGET,
                }
            }
        },
    )


def generate_hypothesis(
    drug: str, disease: str, context_chunks: list
) -> list[dict]:
    """
    Run Chain-of-Thought reasoning to propose a repurposing hypothesis.
    """
    context_text = "\n\n".join(
        [f"[source: {d.metadata.get('pmid')}] {d.page_content}" for d in context_chunks]
    )

    prompt = ChatPromptTemplate.from_template(
        """Context from PubMed literature:
{context}

---
Task: Analyze the provided literature to identify MULTIPLE high-confidence drug repurposing candidates for the target disease '{disease}'.
(Note: The input '{drug}' might be synonymous with the disease. Ignore it if so. You must find DIFFERENT drug candidates in the text).

STRICT INSTRUCTIONS:
1. You MUST output a JSON ARRAY (list) containing 3 to 5 distinct drug candidates.
2. Do NOT output a single JSON object. It must be a list: [ {{...}}, {{...}}, ... ]
3. The 'Shared Pathway' field MUST NEVER BE EMPTY. If a specific biological pathway isn't named, provide a short 2-3 word mechanistic description.
4. NEVER put the user's disease query into the Drug field.

Output your final answer as a JSON LIST of objects with the following keys and NO markdown formatting:
[
  {{
    "drug": "Name of the drug candidate (e.g. Metformin)",
    "target_disease": "{disease}",
    "shared_pathways": ["pathway1", "mechanistic description"],
    "mechanism_of_action": "Detailed explanation...",
    "confidence_score": 85,
    "reasoning_trace": "Summary of analysis..."
  }},
  {{
    "drug": "Another drug candidate",
    ...
  }}
]
"""
    )

    llm = get_llm()
    chain = prompt | llm

    log.info(f"Sending reasoning request for {drug} -> {disease} ...")
    start = time.time()


    try:
        response = chain.invoke(
            {"drug": drug, "disease": disease, "context": context_text}
        )
        content = response.content.strip()
        
        # Strip markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        # log.debug(f"[DEBUG] Raw LLM content: {content[:500]}...") # Optional debug

        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            # Fallback: try to find the list [...]
            start_idx = content.find('[')
            end_idx = content.rfind(']')
            if start_idx != -1 and end_idx != -1:
                result = json.loads(content[start_idx:end_idx+1])
            else:
                raise ValueError("Could not find JSON list in response")

        # Validate result is a list
        if isinstance(result, dict):
            log.warning("[REASONING] LLM returned single object despite instructions. Wrapping in list.")
            result = [result]
        elif not isinstance(result, list):
             log.error("[REASONING] LLM returned neither dict nor list.")
             return []
            
        elapsed = round(time.time() - start, 2)
        log.info(f"[REASONING] Generated {len(result)} hypotheses in {elapsed}s")
        return result

    except Exception as e:
        log.error(f"[REASONING] Failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Pipeline Entry Point
# ---------------------------------------------------------------------------


def run(drug: str = "Metformin", disease: str = "Leukemia") -> str:
    """
    Execute Agent 3 (The Strategist).

    1. Load FAISS index.
    2. Retrieve relevant chunks for "Drug + Disease".
    3. Generate hypothesis using Gemini 2.5.
    4. Save to hypotheses.json (fresh write, no append).
    """
    log.info("=" * 60)
    log.info("Strategist agent started")
    log.info(f"Hypothesis target: {drug} + {disease}")
    log.info("=" * 60)

    # 1. Load Index
    try:
        index = vector_store.load_index()
    except Exception as e:
        log.error(f"Failed to load vector store: {e}")
        return ""

    # 2. Retrieve
    query = f"{drug} {disease} repurposing mechanism"
    log.info(f"Retrieving context for query: '{query}'")
    
    retriever = index.as_retriever(search_kwargs={"k": 10}) 
    chunks = retriever.invoke(query)
    
    log.info(f"[RETRIEVAL] Found {len(chunks)} relevant chunks")

    # 3. Reason
    hypotheses = generate_hypothesis(drug, disease, chunks)
    if not hypotheses:
        return ""

    # 4. Save — fresh write (scraper already wiped old data)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(hypotheses, f, indent=2, ensure_ascii=False)

    log.info(f"Saved hypothesis to {OUTPUT_FILE}")
    log.info(f"[HANDOFF] Strategist → Validator | payload={OUTPUT_FILE}")
    log.info("Strategist agent finished")
    
    return OUTPUT_FILE


# ---------------------------------------------------------------------------
# CLI  —  python strategist.py "Metformin Leukemia"
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Accept dynamic query: first word = drug, rest = disease
    query = sys.argv[1] if len(sys.argv) > 1 else ""

    if query.strip():
        parts = query.strip().split()
        drug = parts[0]
        disease = " ".join(parts[1:]) if len(parts) >= 2 else "cancer"
    else:
        drug = "Metformin"
        disease = "Leukemia"

    output = run(drug, disease)
    if output:
        print(f"\n✅ Reasoning complete. Hypothesis saved to: {output}")
    else:
        print("\n❌ Reasoning failed.")

