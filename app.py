"""
Agent 5 — The Interface (Enterprise Dashboard)
Orchestrates the full pipeline via subprocess and displays results.
"""

import io
import json
import os
import subprocess
import sys
import time
import base64

import gradio as gr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_FILE = os.path.join(BASE_DIR, "validated_results.json")
RAW_DATA_FILE = os.path.join(BASE_DIR, "data", "raw_data.json")
LOG_FILE = os.path.join(BASE_DIR, "logs", "system.log")
PYTHON = sys.executable  # Use the same Python interpreter


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


def load_results():
    if not os.path.exists(RESULTS_FILE):
        return []
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def count_abstracts():
    if not os.path.exists(RAW_DATA_FILE):
        return 0
    with open(RAW_DATA_FILE, "r", encoding="utf-8") as f:
        return len(json.load(f))


def build_dataframe(results, threshold=0.0):
    rows = []
    for item in results:
        score = item.get("final_evidence_score", 0)
        if score < threshold:
            continue
        rows.append({
            "Drug": item.get("drug", ""),
            "Target Disease": item.get("target_disease", ""),
            "Shared Pathway": ", ".join(item.get("shared_pathways", [])),
            "UniProt Validation": item.get("uniprot_validation", {}).get("status", "N/A"),
            "Evidence Score": f"{score:.2f}",
        })
    if not rows:
        return pd.DataFrame(columns=[
            "Drug", "Target Disease", "Shared Pathway",
            "UniProt Validation", "Evidence Score",
        ])
    return pd.DataFrame(rows)


def read_logs(n=15):
    if not os.path.exists(LOG_FILE):
        return "No log file found."
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return "".join(lines[-n:])


# ---------------------------------------------------------------------------
# Network graph
# ---------------------------------------------------------------------------


def render_network_graph(results):
    if not results:
        return "<p style='text-align:center; color:#888;'>No data to visualize.</p>"

    G = nx.DiGraph()

    for item in results:
        drug = item.get("drug", "Unknown")
        disease = item.get("target_disease", "Unknown")
        pathways = item.get("shared_pathways", [])

        G.add_node(drug, ntype="drug")
        G.add_node(disease, ntype="disease")

        for p in pathways:
            short = (p[:25] + "…") if len(p) > 25 else p
            G.add_node(short, ntype="pathway")
            G.add_edge(drug, short)
            G.add_edge(short, disease)

    color_map = {"drug": "#6366f1", "pathway": "#22c55e", "disease": "#ef4444"}
    node_colors = [color_map.get(G.nodes[n].get("ntype", ""), "#94a3b8") for n in G.nodes]

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor("#1e1e2e")
    ax.set_facecolor("#1e1e2e")

    pos = nx.spring_layout(G, seed=42, k=2.5)

    nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#475569", arrows=True,
                           arrowsize=20, width=1.5, connectionstyle="arc3,rad=0.1")
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, node_size=2200,
                           edgecolors="#334155", linewidths=1.5)
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=9, font_color="white",
                            font_weight="bold")

    legend_handles = [
        mpatches.Patch(color="#6366f1", label="Drug"),
        mpatches.Patch(color="#22c55e", label="Pathway"),
        mpatches.Patch(color="#ef4444", label="Disease"),
    ]
    ax.legend(handles=legend_handles, loc="upper left", fontsize=9,
              facecolor="#1e1e2e", edgecolor="#475569", labelcolor="white")
    ax.set_title("Drug → Pathway → Disease Mechanism Map", color="white", fontsize=13, pad=12)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")

    return (
        f'<div style="text-align:center">'
        f'<img src="data:image/png;base64,{b64}" '
        f'style="max-width:100%; border-radius:12px; '
        f'box-shadow: 0 4px 24px rgba(0,0,0,0.3);" />'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Pipeline orchestration via subprocess
# ---------------------------------------------------------------------------


def run_pipeline(query: str) -> tuple[bool, str]:
    """
    Execute the full 4-agent pipeline sequentially via subprocess.
    Returns (success: bool, log_trace: str).
    The log_trace accumulates stdout/stderr from every step so the user
    can always see exactly what happened.
    """
    steps = [
        ("🔍 Agent 1 — Miner",     [PYTHON, os.path.join(BASE_DIR, "scraper.py"), query]),
        ("🏗️ Agent 2 — Architect",  [PYTHON, os.path.join(BASE_DIR, "vector_store.py")]),
        ("🧠 Agent 3 — Strategist", [PYTHON, os.path.join(BASE_DIR, "strategist.py"), query]),
        ("🛡️ Agent 4 — Validator",  [PYTHON, os.path.join(BASE_DIR, "validator.py")]),
    ]

    trace_lines = []

    for label, cmd in steps:
        trace_lines.append(f"\n{'='*50}")
        trace_lines.append(f"▶ Running: {label}")
        trace_lines.append(f"  Command: {' '.join(cmd)}")
        trace_lines.append(f"{'='*50}")

        try:
            result = subprocess.run(
                cmd,
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            trace_lines.append(f"❌ TIMEOUT: {label} exceeded 300s limit")
            return False, "\n".join(trace_lines)
        except Exception as exc:
            trace_lines.append(f"❌ EXCEPTION launching {label}: {exc}")
            return False, "\n".join(trace_lines)

        # Capture stdout
        if result.stdout and result.stdout.strip():
            trace_lines.append(f"[stdout]\n{result.stdout.strip()}")

        # Check for failure — surface stderr immediately
        if result.returncode != 0:
            trace_lines.append(f"❌ {label} FAILED (exit code {result.returncode})")
            if result.stderr:
                trace_lines.append(f"[stderr]\n{result.stderr.strip()}")
            else:
                trace_lines.append("[stderr] (empty — likely a silent crash)")
            return False, "\n".join(trace_lines)

        trace_lines.append(f"✅ {label} completed (exit code 0)")

    trace_lines.append(f"\n{'='*50}")
    trace_lines.append("✅ Full pipeline completed successfully.")
    trace_lines.append(f"{'='*50}")
    return True, "\n".join(trace_lines)


# ---------------------------------------------------------------------------
# Swarm callback (blocks UI while running)
# ---------------------------------------------------------------------------


def initialize_swarm(query, threshold):
    """
    Main callback: runs the pipeline, then refreshes all UI components.
    Gradio shows a loading spinner while this function executes.
    If any step fails, the exact crash log is displayed in the UI.
    """
    if not query or not query.strip():
        gr.Warning("Please enter a search query in the sidebar.")
        return (
            "⚠️ Please enter a search query.",
            "<p style='text-align:center; color:#f59e0b;'>Enter a query to start.</p>",
            build_dataframe([], threshold),
            "Waiting for input...",
        )

    # Execute the 4-step pipeline (UI blocks here)
    success, trace = run_pipeline(query.strip())

    if not success:
        # Surface error — display crash log in BOTH status AND logs tab
        gr.Warning("Pipeline failed! Check the 'Agentic Trace & Logs' tab for details.")
        return (
            f"❌ Pipeline failed. See trace below.\n{trace[-200:]}",
            "<p style='text-align:center; color:#ef4444;'>Pipeline failed. Check logs.</p>",
            build_dataframe([], threshold),
            trace,  # Full crash log in the logs textbox
        )

    # Read fresh results AFTER pipeline completes
    results = load_results()
    abstracts_mined = count_abstracts()
    verified = sum(1 for r in results if r.get("uniprot_validation", {}).get("confirmed"))

    stats = (
        f"✅ Pipeline completed successfully.\n"
        f"📚 Total Abstracts Mined: {abstracts_mined}   |   "
        f"🎯 Verified Targets: {verified}   |   "
        f"📋 Hypotheses: {len(results)}"
    )

    graph_html = render_network_graph(results)
    df = build_dataframe(results, threshold)
    logs = trace  # Show full pipeline trace in logs tab

    return stats, graph_html, df, logs


# ---------------------------------------------------------------------------
# UI Layout
# ---------------------------------------------------------------------------

theme = gr.themes.Soft(primary_hue="indigo")

with gr.Blocks(theme=theme, title="Agentic Literature Miner") as demo:

    # Header
    gr.Markdown(
        """
        # 🧬 Agentic Literature Miner: Drug Repurposing Pipeline

        A **multi-agent AI system** that autonomously mines PubMed literature, builds a
        vector-indexed knowledge base, reasons over biological pathways with
        **Gemini 2.5 Flash (Chain-of-Thought)**, and cross-validates hypotheses against
        **UniProt KB** — orchestrated through five specialised agents:

        **Miner** → **Architect** → **Strategist** → **Validator** → **Interface**
        """
    )

    # Sidebar
    with gr.Sidebar():
        gr.Markdown("### ⚙️ Pipeline Controls")
        query_input = gr.Textbox(
            label="Target Disease / Drug Candidate",
            placeholder="e.g. Metformin Leukemia",
        )
        threshold_slider = gr.Slider(
            minimum=0.0, maximum=1.0, value=0.0, step=0.05,
            label="Minimum Evidence Threshold",
        )
        run_btn = gr.Button("🚀 Initialize Swarm", variant="primary", size="lg")

        gr.Markdown("---")
        gr.Markdown(
            """
            **Agent Legend**
            - 🔍 **Miner** — PubMed Scraper
            - 🏗️ **Architect** — RAG Builder
            - 🧠 **Strategist** — CoT Reasoner
            - 🛡️ **Validator** — UniProt Check
            - 📊 **Interface** — This Dashboard
            """
        )

    # Main Panel — 3 Tabs
    with gr.Tabs():

        with gr.TabItem("🔬 Network Visualization"):
            stats_display = gr.Textbox(
                label="Pipeline Status",
                interactive=False,
                value="Click 'Initialize Swarm' to start the pipeline.",
            )
            network_html = gr.HTML(
                value="<p style='text-align:center; color:#888; padding:40px;'>"
                      "Enter a query and click <b>Initialize Swarm</b>.</p>",
                label="Drug-Gene-Pathway Network",
            )

        with gr.TabItem("📋 Validation Matrix"):
            validation_table = gr.Dataframe(
                value=build_dataframe(load_results()),
                label="Validated Repurposing Candidates",
                interactive=False,
            )

        with gr.TabItem("🖥️ Agentic Trace & Logs"):
            gr.Markdown("**Real-time agent activity log** — proves autonomous multi-agent orchestration.")
            log_output = gr.Textbox(
                value=read_logs(15),
                label="System Log (logs/system.log)",
                lines=15,
                interactive=False,
            )

    # Wiring
    run_btn.click(
        fn=initialize_swarm,
        inputs=[query_input, threshold_slider],
        outputs=[stats_display, network_html, validation_table, log_output],
    )


# ---------------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    demo.launch(share=True)
