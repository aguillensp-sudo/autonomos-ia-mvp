"""Tests for graph wiring. Acceptance criteria: CA-F3-01."""
from src.agent.graph import NODOS_ESPERADOS, construir_grafo


def test_grafo_instancia_sin_errores():
    grafo = construir_grafo()
    assert grafo is not None


def test_grafo_todos_los_nodos_conectados():
    grafo = construir_grafo()
    grafo_estructura = grafo.get_graph()
    nombres_nodos = set(grafo_estructura.nodes.keys())
    for nodo in NODOS_ESPERADOS:
        assert nodo in nombres_nodos, f"nodo esperado ausente del grafo compilado: {nodo}"


def test_grafo_sin_nodos_inalcanzables():
    grafo = construir_grafo()
    grafo_estructura = grafo.get_graph()

    adyacencia: dict[str, set[str]] = {}
    for edge in grafo_estructura.edges:
        adyacencia.setdefault(edge.source, set()).add(edge.target)

    visitados: set[str] = set()
    pendientes = ["__start__"]
    while pendientes:
        actual = pendientes.pop()
        if actual in visitados:
            continue
        visitados.add(actual)
        pendientes.extend(adyacencia.get(actual, set()) - visitados)

    for nodo in NODOS_ESPERADOS:
        assert nodo in visitados, f"nodo inalcanzable desde START: {nodo}"
