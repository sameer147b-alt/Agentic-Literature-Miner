# 🧬 Agentic Literature Miner: The Autonomous Drug Repurposing Swarm

## 🌍 The Problem (Why This Matters)
Finding a new use for an existing drug (Drug Repurposing) is one of the fastest ways to cure diseases like Alzheimer's or Glioblastoma. The problem? There are over 36 million medical papers on PubMed. A human scientist could spend a lifetime reading and still miss the hidden connection between a specific drug, a biological pathway, and a disease.

Standard AI chatbots (like ChatGPT) can't solve this either. If you ask a chatbot to find a cure, it "hallucinates" (makes things up) because it doesn't cross-check its answers against real-world biological databases.

## 🚀 The Solution (What We Achieved)
I engineered an Autonomous Multi-Agent Swarm—a team of specialized AI programs that work together like a digital research lab. Instead of just "chatting" with an AI, the user simply types in a disease (e.g., "Alzheimer's disease").

From there, my engineering takes over entirely:

1. It autonomously searches the internet and downloads hundreds of cutting-edge medical papers.
2. It reads and memorizes them in seconds.
3. It uses advanced logical reasoning to spot hidden relationships between existing drugs and the disease.
4. **Crucially:** It fact-checks its own ideas against a global database of human proteins to ensure the science is actually real.

## 🧠 The Novelty (Why This is Groundbreaking)
This project moves beyond the era of simple "AI Wrappers" (apps that just send text to OpenAI/Google and print the response).

The novelty lies in **Automated Scientific Grounding**. The AI is not allowed to just guess. By integrating a "Validator" agent that talks directly to the UniProt Knowledgebase (the world's master encyclopedia of proteins), the system catches its own mistakes. If the AI suggests a drug but the biological pathway doesn't exist in the human body, the system flags it. It forces the AI to be scientifically accountable.

## 📊 Dashboard Walkthrough (What You Are Seeing)
The project features a custom No-Code interface designed for medical researchers, featuring two main components:

### The Network Visualization (The Mind Map)
This is a dynamic, visual web showing exactly how the AI connects the dots.
- **Blue Nodes:** The proposed Drugs (e.g., PDE5 Inhibitors).
- **Green Nodes:** The Biological Pathway (the actual mechanism in the body, like "Oxidative stress reduction").
- **Red Nodes:** The Target Disease (e.g., Alzheimer's).

### The Validation Matrix (The Truth Table)
This is where the AI's ideas face reality. It grades every hypothesis with an **Evidence Score**. If the AI found a massive amount of proof in the literature and verified it with the global protein database, it gets a high score (like 0.91) and a "Confirmed" stamp. If the data is incomplete, it gets flagged as "Review Required" so human scientists can investigate further.

## 🛠️ My Role: Gen AI & Agentic AI Engineer
Building an autonomous swarm is incredibly difficult because AI agents are prone to crashing, forgetting instructions, and breaking system limits. As the engineer, my core architectural contributions included:

### Multi-Agent Orchestration
I programmed four distinct AI "personas" (The Scraper, The Architect, The Strategist, The Validator) and built the pipeline that allows them to hand off massive amounts of data to each other without human intervention.

### Hybrid Compute Engineering
Cloud AI APIs (like Google Gemini) have strict data limits. To prevent the system from crashing when reading hundreds of heavy medical papers, I engineered a hybrid system. I integrated a local open-source AI model (HuggingFace MiniLM) to process the heavy data directly on the user's computer, saving the Cloud AI purely for high-level reasoning.

### Prompt Engineering & Constraint Formatting
LLMs naturally want to write paragraphs of text. I engineered strict "Chain-of-Thought" prompts that forced the AI to output highly structured data arrays, allowing the Python backend to read the AI's mind and draw the Network Graph.

### Graceful Degradation
I built error-handling safety nets. If the AI finds a new experimental drug that isn't fully documented in the global database yet, my system doesn't crash or delete the data. It elegantly flags it for human review, mimicking a real scientific workflow.
