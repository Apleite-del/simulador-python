from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()
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
 allow_headers=["*"],
)




class ElecNode(BaseModel):
    id: str
    label: str
    type: str
    state: str
    locked: bool
    x: float
    y: float
currentDraw: Optional[float] = 0.0  # 👈 ¡AÑADE ESTA LÍNEA AQUÍ!
class ElecEdge(BaseModel):
    id: str
    from_node: str  
    to: str

class SimulationRequest(BaseModel):
    nodes: List[ElecNode]
    edges: List[ElecEdge]

@app.post("/api/simulate")
def simulate_electrical_network(data: SimulationRequest):
    # 1. Creamos un diccionario de nodos para buscar sus propiedades rápidamente por ID
    nodes_dict = {n.id: n for n in data.nodes}
    
    # 2. Construimos la lista de adyacencia (el grafo eléctrico es bidireccional)
    # Cada nodo sabrá con qué vecino se conecta y a través de qué cable (edge)
    adj = {n.id: [] for n in data.nodes}
    for edge in data.edges:
        if edge.from_node in adj and edge.to in adj:
            adj[edge.from_node].append((edge.to, edge.id))
            adj[edge.to].append((edge.from_node, edge.id))

    # 3. Estados que vamos a calcular
    queue = []
    energized_nodes = set()
    energized_edges = set()
    has_fault = False
    ground_verified = False
    total_amps = 0.0

    # 4. Inyectamos energía: Buscamos todas las fuentes activas para iniciar el recorrido
    for n in data.nodes:
        if n.type == 'source':
            queue.append(n.id)
            energized_nodes.add(n.id)

    # 5. Algoritmo BFS: La energía se propaga por el grafo
    while queue:
        curr_id = queue.pop(0)
        curr_node = nodes_dict[curr_id]

        # ⚡ DETECCIÓN DE ENERGÍA EN TIERRA (CORTOCIRCUITO)
        # Si la energía llega a una puesta a tierra que está CERRADA, ¡tenemos una falta grave!
        if curr_node.type == 'ground' and curr_node.state == 'closed':
            has_fault = True

        # 🛑 REGLA DE BLOQUEO ELECTROMECÁNICO
        # Si el equipo actual es un interruptor, seccionador o fusible y está ABIERTO,
        # la energía llega hasta él (se energiza), pero NO se propaga a sus vecinos.
        if curr_node.type in ['breaker', 'disconnector', 'fuse'] and curr_node.state == 'open':
            continue

        # 🧮 CÁLCULO DE CONSUMO
        # Si el nodo es una carga energizada, sumamos su demanda de corriente
        if curr_node.type == 'load' and curr_node.currentDraw:
            total_amps += curr_node.currentDraw

        # Pasamos la energía a los vecinos conectados
        for neighbor_id, edge_id in adj[curr_id]:
            # El cable que nos une al vecino se energiza
            energized_edges.add(edge_id)
            
            if neighbor_id not in energized_nodes:
                energized_nodes.add(neighbor_id)
                queue.append(neighbor_id)

    # 🛡️ VERIFICACIÓN LOTO (Bloqueo y Etiquetado)
    # La tierra es segura si hay al menos una tierra cerrada y NINGUNA zona está bajo tensión peligrosa
    closed_grounds = any(n.type == 'ground' and n.state == 'closed' for n in data.nodes)
    if closed_grounds and not has_fault and len(energized_nodes) <= 1:
        ground_verified = True

    # Si hay un cortocircuito, la corriente se dispara al infinito de forma segura para el simulador
    if has_fault:
        total_amps = 999.9

    # 6. Devolvemos las listas transformadas a formato JSON estándar
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