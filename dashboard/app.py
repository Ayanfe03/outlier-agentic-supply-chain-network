import streamlit as st
import requests
import json
import networkx as nx
import matplotlib.pyplot as plt
from datetime import datetime, timezone
from pathlib import Path

st.set_page_config(page_title="One Click AI – Supply Chain Agents", layout="wide")

st.title("One Click AI – NANDA-Native Internet of Agents Simulation")

# Sidebar controls
st.sidebar.header("Controls")
intent = st.sidebar.text_input("Declare your procurement intent", "Buy 100 wheels for Ferrari assembly")
quantity = st.sidebar.number_input("Quantity", min_value=1, value=50)
region = st.sidebar.selectbox("Preferred Region", ["NG", "EU", "Any"], index=0)
origin = st.sidebar.text_input("Origin", "Lagos")
destination = st.sidebar.text_input("Destination", "Ota")

if st.sidebar.button("Execute One Click"):
    with st.spinner("Orchestrating decentralized agents..."):
        payload = {
            "intent": intent,
            "quantity": quantity,
            "region": region if region != "Any" else None,
            "origin": origin,
            "destination": destination,
        }
        try:
            #resp = requests.post("http://buyer:8002/intent", json=payload, timeout=30)
            resp = requests.post("http://localhost:8002/intent", json=payload, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            st.success("Cascade executed successfully!")
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
        st.metric("Status", report["final_plan"].get("status", "N/A"))
        col1, col2, col3 = st.columns(3)
        col1.metric("Estimated Cost", f"₦{report['final_plan'].get('total_cost_estimate', 'N/A'):,}")
        col2.metric("Lead Time", f"{report['final_plan'].get('lead_time_days', 'N/A')} days")
        col3.metric("Route", report["final_plan"].get("route", "N/A"))

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

    # Add nodes from discovered agents
    for path in report.get("discovery_paths", []):
        if isinstance(path, dict):
            agent_id = path.get("agent_id", "Unknown")
            role = path.get("role", "Agent")
            G.add_node(agent_id, label=f"{role}\n{agent_id}")

    # Add edges from message exchanges
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
