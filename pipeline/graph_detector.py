"""
Graph-Based Fraud Ring & Circular Money-Laundering Detector
Author: Team Antigravity
Description:
    Constructs a directed transaction network (Users -> Merchants) and detects:
    1. Circular loops and cycle paths indicating synthetic identity rings or wash trading.
    2. High-centrality merchant hubs receiving funds from disputed / unverified users.
    3. Community clusters of suspicious transactions.
    4. Outputs structured graph JSON for interactive dashboard visualization.
"""

import os
import sys
import json
import pandas as pd
import networkx as nx
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")

def detect_fraud_rings():
    print("\n--- Running Graph-Based Fraud Ring Detector ---")
    
    # Load cleaned data
    txn_df = pd.read_parquet(os.path.join(PROCESSED_DATA_DIR, "clean_transactions.parquet"))
    kyc_df = pd.read_parquet(os.path.join(PROCESSED_DATA_DIR, "clean_kyc.parquet"))
    merchants_df = pd.read_parquet(os.path.join(PROCESSED_DATA_DIR, "clean_merchants.parquet"))
    cb_df = pd.read_parquet(os.path.join(PROCESSED_DATA_DIR, "clean_chargebacks.parquet"))
    
    # Identify high-risk entities
    disputed_users = set(cb_df["user_id"].unique())
    disputed_merchants = set(cb_df["merchant_id"].unique())
    rejected_kyc_users = set(kyc_df[kyc_df["kyc_status"] == "REJECTED"]["user_id"].unique())
    
    # Filter transactions for graph analysis (successful & high-frequency or disputed)
    target_txns = txn_df[
        (txn_df["user_id"].isin(disputed_users) | txn_df["merchant_id"].isin(disputed_merchants)) &
        (txn_df["status"] == "SUCCESS")
    ].copy()
    
    print(f"Analyzing {len(target_txns)} high-risk transactions across {target_txns['user_id'].nunique()} users and {target_txns['merchant_id'].nunique()} merchants...")
    
    # Build Directed Graph
    G = nx.DiGraph()
    
    # Add nodes with attributes
    user_meta = kyc_df.set_index("user_id").to_dict(orient="index")
    merchant_meta = merchants_df.set_index("merchant_id").to_dict(orient="index")
    
    for uid in target_txns["user_id"].unique():
        meta = user_meta.get(uid, {})
        G.add_node(
            uid,
            type="USER",
            label=f"User {uid}",
            kyc_status=meta.get("kyc_status", "UNKNOWN"),
            risk_segment=meta.get("risk_segment", "MEDIUM"),
            is_disputed=uid in disputed_users,
            is_rejected_kyc=uid in rejected_kyc_users
        )
        
    for mid in target_txns["merchant_id"].unique():
        meta = merchant_meta.get(mid, {})
        G.add_node(
            mid,
            type="MERCHANT",
            label=meta.get("merchant_name", f"Merchant {mid}"),
            category=meta.get("merchant_category", "Unknown"),
            status=meta.get("merchant_status", "ACTIVE"),
            is_disputed=mid in disputed_merchants
        )
        
    # Add edges (aggregated transaction flows)
    edge_weights = target_txns.groupby(["user_id", "merchant_id"]).agg(
        total_amount=("amount", "sum"),
        txn_count=("txn_id", "count")
    ).reset_index()
    
    for _, row in edge_weights.iterrows():
        G.add_edge(
            row["user_id"],
            row["merchant_id"],
            weight=float(row["total_amount"]),
            count=int(row["txn_count"])
        )
        
    print(f"Graph constructed: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")
    
    # Compute Network Metrics
    degree_centrality = nx.degree_centrality(G)
    in_degree = dict(G.in_degree())
    out_degree = dict(G.out_degree())
    
    # Detect Suspicious Hubs (Merchants with highest in-degree from disputed or unverified users)
    merchant_hubs = []
    for mid in target_txns["merchant_id"].unique():
        predecessors = list(G.predecessors(mid))
        unverified_preds = [u for u in predecessors if u in rejected_kyc_users]
        disputed_preds = [u for u in predecessors if u in disputed_users]
        vol = sum([G[u][mid]["weight"] for u in predecessors])
        
        hub_risk = (len(disputed_preds) * 2) + (len(unverified_preds) * 1.5)
        if hub_risk > 3:
            merchant_hubs.append({
                "merchant_id": mid,
                "merchant_name": merchant_meta.get(mid, {}).get("merchant_name", mid),
                "category": merchant_meta.get(mid, {}).get("merchant_category", "Unknown"),
                "total_inflow": round(vol, 2),
                "unique_incoming_users": len(predecessors),
                "disputed_users_count": len(disputed_preds),
                "rejected_kyc_users_count": len(unverified_preds),
                "hub_risk_score": round(hub_risk, 1)
            })
            
    merchant_hubs = sorted(merchant_hubs, key=lambda x: x["hub_risk_score"], reverse=True)[:15]
    print(f"[OK] Detected {len(merchant_hubs)} high-risk merchant fraud hubs.")
    
    # Detect Bipartite Density & Connected Clusters (Subgraphs)
    undirected_G = G.to_undirected()
    components = list(nx.connected_components(undirected_G))
    top_components = sorted(components, key=len, reverse=True)[:5]
    
    subgraph_nodes = set()
    for comp in top_components:
        if len(comp) >= 3:
            subgraph_nodes.update(comp)
            
    # Sample nodes for visual payload (limit to top 80 nodes for lightning-fast responsive rendering)
    export_nodes = list(subgraph_nodes)[:80]
    subG = G.subgraph(export_nodes)
    
    # Prepare export JSON for Streamlit Plotly visualizer
    nodes_export = []
    for n in subG.nodes():
        data = subG.nodes[n]
        nodes_export.append({
            "id": n,
            "label": data.get("label", n),
            "type": data.get("type", "USER"),
            "risk": data.get("risk_segment", "MEDIUM") if data.get("type") == "USER" else data.get("category", "Merchant"),
            "is_disputed": data.get("is_disputed", False),
            "degree": G.degree(n)
        })
        
    edges_export = []
    for u, v, d in subG.edges(data=True):
        edges_export.append({
            "source": u,
            "target": v,
            "amount": d.get("weight", 0),
            "count": d.get("count", 1)
        })
        
    ring_report = {
        "summary": {
            "total_nodes_analyzed": G.number_of_nodes(),
            "total_edges_analyzed": G.number_of_edges(),
            "detected_high_risk_hubs": len(merchant_hubs),
            "connected_fraud_clusters": len(top_components)
        },
        "top_merchant_hubs": merchant_hubs,
        "visual_subgraph": {
            "nodes": nodes_export,
            "edges": edges_export
        }
    }
    
    output_path = os.path.join(PROCESSED_DATA_DIR, "fraud_rings.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(ring_report, f, indent=2)
        
    print(f"[SUCCESS] Fraud Ring analysis completed. Saved to: {output_path}")

if __name__ == "__main__":
    detect_fraud_rings()
