---
name: lit-miner
description: Autonomous multi-agent pipeline that mines PubMed literature for drug-repurposing insights using four coordinated agents.
---

# Multi-Agent Literature Miner for Drug Repurposing

An autonomous agentic system that discovers potential drug-repurposing candidates by mining biomedical literature, indexing findings into a vector store, reasoning over drug-gene interactions, and presenting structured analysis.

## Agent Architecture

The pipeline is orchestrated as a four-agent handoff chain:

```
Scraper ──► Indexer ──► Reasoner ──► Analyst
```

### Agent 1 — Scraper (The Miner)

| Property | Detail |
|----------|--------|
| **Script** | `scraper.py` |
| **Role** | Fetch PubMed abstracts via BioPython Entrez API |
| **Input** | Drug-gene interaction keywords (e.g. `"metformin AND AMPK"`) |
| **Output** | `data/abstracts.json` — list of `{pmid, title, abstract, authors, date}` |
| **Handoff** | Passes the JSON path to the **Indexer** |

**Planning notes:**
- Respect NCBI rate limits (≤ 3 req/s without API key, ≤ 10 with key).
- Log every API call with status code, latency, and result count.
- Support configurable `max_results` and `search_term` parameters.

---

### Agent 2 — Indexer

| Property | Detail |
|----------|--------|
| **Script** | `vector_store.py` |
| **Role** | Embed abstracts and build a FAISS vector index |
| **Input** | `data/abstracts.json` |
| **Output** | Persisted FAISS index at `data/faiss_index/` |
| **Handoff** | Notifies the **Reasoner** that the index is ready |

**Planning notes:**
- Use LangChain document loaders to ingest the JSON.
- Chunk long abstracts if they exceed the embedding model's token limit.
- Persist index to disk so it can be reloaded without re-embedding.

---

### Agent 3 — Reasoner

| Property | Detail |
|----------|--------|
| **Script** | `reasoner.py` *(future)* |
| **Role** | Query the vector store and apply LLM reasoning to identify drug-gene repurposing signals |
| **Input** | User query + FAISS index |
| **Output** | Ranked list of candidate drug-gene interactions with supporting evidence |
| **Handoff** | Passes candidates to the **Analyst** |

**Planning notes:**
- Use RAG (Retrieval-Augmented Generation) to ground LLM answers in retrieved abstracts.
- Score candidates by evidence strength (number of supporting papers, recency).
- Use `google-genai` for the generative component.

---

### Agent 4 — Analyst

| Property | Detail |
|----------|--------|
| **Script** | `analyst.py` *(future)* |
| **Role** | Synthesise results, build knowledge graphs, and present findings |
| **Input** | Ranked candidate list from Reasoner |
| **Output** | Interactive Gradio dashboard with network graph and evidence table |
| **Handoff** | Final output — presented to the user |

**Planning notes:**
- Use `networkx` to construct a drug-gene interaction graph.
- Use `pandas` for tabular summaries.
- Serve via `gradio` for an interactive web UI.

---

## Logging & Observability

All agents share a central logging module (`logger.py`) that writes to `logs/system.log`.

**Tracked events:**
- `[HANDOFF]` — agent-to-agent transitions with payload metadata
- `[API]` — external API calls with status, latency, and result count
- `[INDEX]` — vector store build/load operations
- `[QUERY]` — RAG queries and response summaries

## Dependencies

See `requirements.txt` for the full list: `langchain`, `faiss-cpu`, `google-genai`, `biopython`, `networkx`, `gradio`, `pandas`.
