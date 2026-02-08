import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt

st.title("Supply Chain Agent Network")

G = nx.Graph()
G.add_node("Procurement", role="buyer")
G.add_node("Supplier", role="supplier")
G.add_node("Logistics", role="logistics")
G.add_edge("Procurement", "Supplier", flow="wheels", cost=100)
G.add_edge("Supplier", "Logistics", flow="transport", cost=30)

# Draw
fig, ax = plt.subplots(figsize=(8, 6))
pos = nx.spring_layout(G)
nx.draw(G, pos, ax=ax, with_labels=True, node_color='lightblue',
        node_size=2000, font_size=12, font_weight='bold')
nx.draw_networkx_edge_labels(G, pos, edge_labels=nx.get_edge_attributes(G, 'flow'))
st.pyplot(fig)

# Analytics
st.subheader("Network Analytics")
degrees = dict(G.degree())
st.write("Node degrees:", degrees)

bottlenecks = {n: d for n, d in degrees.items() if d > 2}
if bottlenecks:
    st.warning(f"Potential bottlenecks: {bottlenecks}")
else:
    st.success("No major bottlenecks detected")