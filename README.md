# 🧬 Agentic Literature Miner: The Autonomous Drug Repurposing Swarm
🌍 The Problem (Why This Matters)
Finding a new use for an existing drug (Drug Repurposing) is one of the fastest ways to cure complex diseases. However, standard LLMs hallucinate when asked to find cures because they do not cross-reference real-world biological databases.

The Solution: I engineered an Autonomous Multi-Agent Swarm that scrapes live PubMed abstracts, uses Chain-of-Thought reasoning to find hidden drug-disease pathways, and cryptographically validates every single hypothesis against the global UniProt Knowledgebase.

📊 Proof of Work & Performance Metrics
Unlike standard AI wrappers, this system relies on verifiable data processing. >
Latest Production Run (Alzheimer's Disease):

Data Digested: 146 dense medical abstracts scraped via NCBI E-utilities.

Knowledge Graph: Constructed a FAISS vector database using local HuggingFaceMiniLM (bypassing cloud API quotas).

Agentic Reasoning: Generated 4 distinct pharmacological hypotheses (including PDE5Is and Metabolic Modulators).

Validation: Highest validated mechanism achieved a 0.91 Evidence Score against the UniProt database.

The Dashboard in Action
1. The Network Visualization (Agentic Reasoning)
Dynamically maps the LLM's extracted pathways (Drug -> Mechanism -> Target).

2. The Validation Matrix (Grounding & Truth)
Shows the rigorous UniProt verification process to eliminate LLM hallucinations.

A full raw JSON output from the Strategist Agent is available in sample_alzheimers_report.json.

🧠 The Agentic Architecture (LangChain v0.3)
The Miner (Scraper Agent): Dynamically interfaces with the NCBI E-utilities API.

The Architect (RAG Builder): Bypasses external API rate limits using a local all-MiniLM-L6-v2 embedding engine for high-speed semantic chunking.

The Strategist (CoT Reasoner): Leverages Gemini 2.5 Flash using strict Chain-of-Thought JSON parsing to extract interconnected entities.

The Validator (Grounding Agent): Cross-references proposed biological mechanisms against the UniProt KB, implementing "Graceful Degradation" (flagging partial matches for review rather than crashing).

💻 Local Installation & Setup
Want to run the swarm on your local machine? Follow these steps:

1. Clone the repo and install dependencies:
```bash
git clone https://github.com/your-username/Agentic-Literature-Miner.git
cd Agentic-Literature-Miner
pip install -r requirements.txt
```

2. Set up your environment variables:
Create a .env file in the root directory and add your API key:
```text
GOOGLE_API_KEY=your_gemini_api_key_here
```

3. Launch the Gradio Dashboard:
```bash
python app.py
```
Navigate to http://127.0.0.1:7860 in your browser. Type in a disease (e.g., "Glioblastoma"), set your Evidence Threshold, and click Initialize Swarm.

(Note: You will need to change your-username in the GitHub repo size badge and the clone link to your actual GitHub username once it's up!)
