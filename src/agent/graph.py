"""P04 LangGraph StateGraph. Acceptance criteria: CA-F3-01.
Wires all nodes and conditional edges per
specs/agente-conversacional/design.md SPEC-F3-03.
"""
from langgraph.graph import END, START, StateGraph

from src.agent.nodes.calcular import calcular
from src.agent.nodes.confirmar import confirmar
from src.agent.nodes.detectar_periodo import detectar_periodo
from src.agent.nodes.notificar import notificar
from src.agent.nodes.ocr_factura import ocr_factura
from src.agent.nodes.recopilar_datos import recopilar_datos
from src.agent.nodes.resumir import resumir
from src.agent.nodes.verificar_duplicado import verificar_duplicado
from src.agent.state import EstadoP04

NODOS_ESPERADOS = [
    "detectar_periodo",
    "verificar_duplicado",
    "recopilar_datos",
    "ocr_factura",
    "calcular",
    "resumir",
    "confirmar",
    "notificar",
]


def _ruta_tras_recopilar_datos(estado: EstadoP04) -> str:
    # facturas_baja_confianza is NOT checked here — recopilar_datos resolves
    # it internally via a real interrupt() loop before ever returning control
    # to this routing function (see design.md SPEC-F3-02 amendment). There is
    # deliberately no recopilar_datos -> recopilar_datos self-edge: a bare
    # conditional edge is not a LangGraph pause point and previously caused
    # a GraphRecursionError after 10,000+ redundant Claude Sonnet 5 calls.
    if estado.get("sin_actividad") is True:
        return "calcular"
    if estado.get("facturas_pendientes_ocr"):
        return "ocr_factura"
    return "calcular"


def _ruta_tras_confirmar(estado: EstadoP04) -> str:
    if estado.get("confirmado"):
        return "notificar"
    if estado.get("quiere_revisar"):
        return "recopilar_datos"
    return "notificar"  # cancelado


def construir_grafo(checkpointer=None):
    """Builds and compiles the P04 StateGraph. `checkpointer` is optional so
    the graph can be instantiated (CA-F3-01) without a live Postgres
    connection for structural tests; real invocation always passes one
    (per design.md SPEC-F3-06)."""
    g = StateGraph(EstadoP04)

    g.add_node("detectar_periodo", detectar_periodo)
    g.add_node("verificar_duplicado", verificar_duplicado)
    g.add_node("recopilar_datos", recopilar_datos)
    g.add_node("ocr_factura", ocr_factura)
    g.add_node("calcular", calcular)
    g.add_node("resumir", resumir)
    g.add_node("confirmar", confirmar)
    g.add_node("notificar", notificar)

    g.add_edge(START, "detectar_periodo")
    g.add_edge("detectar_periodo", "verificar_duplicado")
    g.add_edge("verificar_duplicado", "recopilar_datos")
    g.add_conditional_edges(
        "recopilar_datos", _ruta_tras_recopilar_datos,
        {"calcular": "calcular", "ocr_factura": "ocr_factura"},
    )
    g.add_edge("ocr_factura", "recopilar_datos")
    g.add_edge("calcular", "resumir")
    g.add_edge("resumir", "confirmar")
    g.add_conditional_edges(
        "confirmar", _ruta_tras_confirmar,
        {"notificar": "notificar", "recopilar_datos": "recopilar_datos"},
    )
    g.add_edge("notificar", END)

    return g.compile(checkpointer=checkpointer)
