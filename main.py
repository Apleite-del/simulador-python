from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# 🛡️ EL PASAPORTE: Esto permite que StackBlitz pueda hablar con Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite peticiones desde cualquier web
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ElecNode(BaseModel):
    id: str
    label: Optional[str] = ""
    type: str
    state: str
    locked: Optional[bool] = False
    x: Optional[float] = 0.0
    y: Optional[float] = 0.0
    currentDraw: Optional[float] = 0.0  # 👈 ¡Indentado correctamente dentro de la clase!

class ElecEdge(BaseModel):
    id: str
    from_node: str  
    to: str

class SimulationRequest(BaseModel):
    nodes: List[ElecNode]
    edges: List[ElecEdge]

@app.post("/api/simulate")
def simulate_electrical_network(data: SimulationRequest):
    # 1. Creamos un diccionario de nodos
    nodes_dict = {n.id: n for n in data.nodes}
    
    # 2. Construimos la lista de adyacencia
    adj = {n.id: [] for n in data.nodes}
    for edge in data.edges:
        if edge.from_node in adj and edge.to in adj:
            adj[edge.from_node].append((edge.to, edge.id))
            adj[edge.to].append((edge.from_node, edge.id))

    # 3. Estados
    queue = []
    energized_nodes = set()
    energized_edges = set()
    has_fault = False
    ground_verified = False
    total_amps = 0.0

    # 4. Inyectamos energía
    for n in data.nodes:
        if n.type == 'source':
            queue.append(n.id)
            energized_nodes.add(n.id)

    # 5. Algoritmo BFS
    while queue:
        curr_id = queue.pop(0)
        curr_node = nodes_dict[curr_id]

        # Cortocircuito letal
        if curr_node.type == 'ground' and curr_node.state == 'closed':
            has_fault = True

        # 🛑 AQUÍ SUCEDE LA MAGIA DEL CORTE
        if curr_node.type in ['breaker', 'disconnector', 'fuse'] and curr_node.state == 'open':
            continue

        # Carga
        if curr_node.type == 'load' and curr_node.currentDraw:
            total_amps += curr_node.currentDraw

        for neighbor_id, edge_id in adj[curr_id]:
            energized_edges.add(edge_id)
            if neighbor_id not in energized_nodes:
                energized_nodes.add(neighbor_id)
                queue.append(neighbor_id)
ground_queue = []
    grounded_nodes = set()
    grounded_edges = set()

    # Buscamos todas las tierras conectadas
    for n in data.nodes:
        if n.type == 'ground' and n.state == 'closed':
            ground_queue.append(n.id)
            grounded_nodes.add(n.id)

    while ground_queue:
        curr_id = ground_queue.pop(0)
        curr_node = nodes_dict[curr_id]

        # La tierra SÍ pasa por los interruptores cerrados, pero se detiene si están abiertos
        if curr_node.type in ['breaker', 'disconnector', 'fuse'] and curr_node.state == 'open':
            continue

        for neighbor_id, edge_id in adj[curr_id]:
            grounded_edges.add(edge_id)
            if neighbor_id not in grounded_nodes:
                grounded_nodes.add(neighbor_id)
                ground_queue.append(neighbor_id)
    # 🛡️ VERIFICACIÓN LOTO
    closed_grounds = any(n.type == 'ground' and n.state == 'closed' for n in data.nodes)
    if closed_grounds and not has_fault and len(energized_nodes) <= 1:
        ground_verified = True

    if has_fault:
        total_amps = 999.9

    return {
        "energizedNodes": list(energized_nodes),
        "energizedEdges": list(energized_edges),
        "hasFault": has_fault,
        "groundVerified": ground_verified,
        "totalAmps": round(total_amps, 2)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
