"""calcular — thin wrapper: deserializes state dicts to Pydantic models,
calls calcular_m303() (Phase 2), serializes the result back into EstadoP04's
JSON-safe shape. The only fiscal computation this graph performs, and it
performs none itself — per docs/backend-standards.md: "LLM never calculates
taxes." No LLM call in this node either.
"""
from datetime import date

from src.agent.supabase_client import crear_cliente_usuario
from src.fiscal.iva.calcular_m303 import calcular_m303
from src.fiscal.models import FacturaEmitida, FacturaRecibida, PerfilFiscal


def calcular(estado: dict) -> dict:
    client = crear_cliente_usuario(estado["user_jwt"])

    perfil_row = (
        client.table("perfil_fiscal").select("*").eq("user_id", estado["user_id"]).execute()
    )
    if not perfil_row.data:
        raise ValueError(f"No perfil_fiscal found for user_id={estado['user_id']}")
    perfil_fiscal = PerfilFiscal(**perfil_row.data[0])

    facturas_emitidas = [FacturaEmitida(**f) for f in estado.get("facturas_emitidas", [])]
    facturas_recibidas = [FacturaRecibida(**f) for f in estado.get("facturas_recibidas", [])]

    resultado, errores = calcular_m303(
        client=client,
        user_id=estado["user_id"],
        ejercicio=estado["ejercicio"],
        periodo=estado["periodo"],
        perfil_fiscal=perfil_fiscal,
        facturas_emitidas=facturas_emitidas,
        facturas_recibidas=facturas_recibidas,
        fecha_inicio_periodo=date.fromisoformat(estado["fecha_inicio_periodo"]),
        fecha_fin_periodo=date.fromisoformat(estado["fecha_fin_periodo"]),
        solicita_devolucion=estado.get("quiere_devolucion", False),
    )

    return {
        "resultado_m303": resultado.model_dump(mode="json"),
        "errores_coherencia": errores,
    }
