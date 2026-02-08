import streamlit as st
import requests
import json
import networkx as nx
import matplotlib.pyplot as plt
from datetime import datetime, timezone
from pathlib import Path
import os

st.set_page_config(page_title="Outlier Agentic Protocol", layout="wide")

st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; }
    .kpi-card {
      background: #f7f7fb;
      border: 1px solid #e4e6ef;
      border-radius: 12px;
      padding: 12px 14px;
    }
    .kpi-label { color: #5b6270; font-size: 0.85rem; }
    .kpi-value { font-size: 1.3rem; font-weight: 600; color: #111827; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Outlier Agentic Protocol")
st.caption("Programmable supply-chain coordination via autonomous agent networks")

# Sidebar controls
st.sidebar.header("Control Panel")
intent = st.sidebar.text_input("Declare your procurement intent", "Buy 100 wheels for Ferrari assembly")
region = st.sidebar.selectbox("Preferred Region", ["NG", "EU", "Any"], index=0)

if st.sidebar.button("Run Protocol"):
    with st.spinner("Orchestrating decentralized agents..."):
        payload = {
            "intent": intent,
            "region": region if region != "Any" else None,
        }
        try:
            #resp = requests.post("http://buyer:8002/intent", json=payload, timeout=30)
            buyer_url = os.getenv("BUYER_URL", "http://localhost:8002")
            resp = requests.post(
                f"{buyer_url}/intent",
                json=payload,
                timeout=90,
                proxies={"http": None, "https": None},
            )
            resp.raise_for_status()
            result = resp.json()
            st.success("Cascade executed successfully.")
            st.session_state.last_result = result
        except Exception as e:
            st.error(f"Orchestration failed: {str(e)}")

# Load latest report (shared volume or local)
BASE_DIR = Path(__file__).resolve().parents[1]
REPORT_PATH = BASE_DIR / "reports" / "coord_report.json"
try:
    with open(REPORT_PATH, "r") as f:
        report = json.load(f)
    st.session_state.last_report = report
except:
    report = st.session_state.get("last_report", {})
    if not report:
        st.info(f"No report generated yet. Run an intent above. (Looking for: {REPORT_PATH})")

# ── Dashboard Sections ───────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs(["Overview", "Coordination Report", "Supply Network Graph"])

with tab1:
    st.subheader("Execution Summary")
    if report.get("final_plan"):
        st.write(f"Status: {report['final_plan'].get('status', 'N/A')}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                f"""<div class='kpi-card'>
                <div class='kpi-label'>Estimated Cost</div>
                <div class='kpi-value'>₦{report['final_plan'].get('total_cost_estimate', 'N/A')}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f"""<div class='kpi-card'>
                <div class='kpi-label'>Lead Time</div>
                <div class='kpi-value'>{report['final_plan'].get('lead_time_days', 'N/A')} days</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with col3:
            st.markdown(
                f"""<div class='kpi-card'>
                <div class='kpi-label'>Route</div>
                <div class='kpi-value'>{report['final_plan'].get('route', 'N/A')}</div>
                </div>""",
                unsafe_allow_html=True,
            )

    if "disruption" in json.dumps(report):
        st.warning("⚠️ Disruption occurred – resilience features activated (rediscovery & retry)")

with tab2:
    st.subheader("Full Network Coordination Report")
    if report:
        st.json(report)
    else:
        st.info("Run an intent to generate a report.")

    if report.get("discovery_paths"):
        st.subheader("Discovery Paths")
        for path in report["discovery_paths"]:
            if isinstance(path, dict):
                st.write(f"- {path.get('role')} ({path.get('agent_id')}) – score: {path.get('match_score')}")

with tab3:
    st.subheader("Dynamic Supply Network Graph")

    G = nx.DiGraph()

    # Add facility/hub nodes from final plan if available
    origin = report.get("origin") or report.get("final_plan", {}).get("origin")
    destination = report.get("destination") or report.get("final_plan", {}).get("destination")
    if origin:
        G.add_node(origin, label=f"Facility\\n{origin}")
    if destination:
        G.add_node(destination, label=f"Facility\\n{destination}")
    if origin and destination:
        G.add_edge(origin, destination, label="route")

    # Add nodes from discovered agents
    for path in report.get("discovery_paths", []):
        if isinstance(path, dict):
            agent_id = path.get("agent_id", "Unknown")
            role = path.get("role", "Agent")
            G.add_node(agent_id, label=f"{role}\n{agent_id}")

    # Material flow edges (supplier -> logistics -> destination)
    part = report.get("part") or "goods"
    qty = report.get("quantity") or ""
    qty_label = f"{qty} " if qty else ""
    supplier_id = None
    logistics_id = None
    for path in report.get("discovery_paths", []):
        if isinstance(path, dict):
            if path.get("role") == "Supplier" and not supplier_id:
                supplier_id = path.get("agent_id")
            if path.get("role") == "LogisticsProvider" and not logistics_id:
                logistics_id = path.get("agent_id")
    buyer_id = "buyer-1"
    if supplier_id:
        G.add_edge(buyer_id, supplier_id, label=f"order:{qty_label}{part}")
    if supplier_id and logistics_id:
        G.add_edge(supplier_id, logistics_id, label=f"material:{qty_label}{part}")
    if logistics_id and destination:
        G.add_edge(logistics_id, destination, label=f"delivery:{qty_label}{part}")

    # Add edges from message exchanges (information flow)
    for msg in report.get("message_exchanges", []):
        if isinstance(msg, dict) and "from" in msg and "to" in msg:  # if structured
            G.add_edge(msg["from"], msg["to"], label=msg.get("intent", "flow"))
        elif "disruption" in msg:
            G.add_node("Disruption", label="Disruption Event", color="red")

    if G.number_of_nodes() > 0:
        fig, ax = plt.subplots(figsize=(10, 7))
        pos = nx.spring_layout(G, seed=42)
        nx.draw(G, pos, with_labels=True, node_color="lightblue", 
                node_size=2000, font_size=10, font_weight="bold", ax=ax)
        
        # Edge labels
        edge_labels = nx.get_edge_attributes(G, 'label')
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax)
        
        st.pyplot(fig)

        # Basic analytics
        degrees = dict(G.degree())
        bottlenecks = [n for n, d in degrees.items() if d >= 3]
        if bottlenecks:
            st.warning(f"Potential bottlenecks detected: {', '.join(bottlenecks)}")
    else:
        st.info("Graph will populate after successful execution.")

st.caption(f"Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
