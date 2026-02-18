"""FastAPI server for the Membria Analytics Dashboard."""

from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
from pathlib import Path

from membria.graph import GraphClient
from membria.config import ConfigManager

app = FastAPI(title="Membria Analytics Dashboard")

# Dependency for graph client
def get_graph():
    config = ConfigManager()
    client = GraphClient(config.falkordb)
    client.connect()
    try:
        yield client
    finally:
        client.disconnect()

@app.get("/api/graph")
def get_graph_data(client: GraphClient = Depends(get_graph)):
    """Fetch all nodes and edges for D3.js visualization."""
    # Simplified query for MVP
    query = """
    MATCH (n)
    OPTIONAL MATCH (n)-[r]->(m)
    RETURN n, r, m
    """
    results = client.query(query)
    
    nodes = {}
    links = []
    
    if results:
        for row in results:
            n = row[0]
            r = row[1]
            m = row[2]
            
            # Process node n
            n_id = n.id
            if n_id not in nodes:
                nodes[n_id] = {
                    "id": n_id,
                    "label": list(n.labels)[0] if n.labels else "Unknown",
                    "properties": n.properties
                }
                
            # Process edge and target m
            if r and m:
                m_id = m.id
                if m_id not in nodes:
                    nodes[m_id] = {
                        "id": m_id,
                        "label": list(m.labels)[0] if m.labels else "Unknown",
                        "properties": m.properties
                    }
                links.append({
                    "source": n_id,
                    "target": m_id,
                    "type": r.relation
                })
                
    return {"nodes": list(nodes.values()), "links": links}

@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    dashboard_html = Path(__file__).parent / "index.html"
    return dashboard_html.read_text()

def start_dashboard(host: str = "127.0.0.1", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)
