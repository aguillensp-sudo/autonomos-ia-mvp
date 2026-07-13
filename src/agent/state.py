"""EstadoP04 — LangGraph state for the P04 conversational agent.

All fields are JSON-serializable (str/int/float/bool/list/dict only — no
Pydantic model instances, no `date` objects), per
specs/agente-conversacional/design.md SPEC-F3-01, because LangGraph's
PostgresSaver checkpoints the state by serializing it. Nodes convert to/from
src/fiscal/models.py Pydantic models at their own boundary, never store them
in state directly.
"""
from typing import TypedDict


class MensajeChat(TypedDict):
    rol: str  # 'usuario' | 'agente'
    contenido: str


class EstadoP04(TypedDict):
    # Identity / thread
    thread_id: str
    user_id: str
    user_jwt: str  # the authenticated user's own Supabase JWT — RLS-scoped
                    # client construction (src/agent/supabase_client.py) uses
                    # this, never the service role key. Post-adversarial-review
                    # Blocker 2.

    # Period (set by detectar_periodo)
    ejercicio: int | None
    periodo: str | None  # '1T' | '2T' | '3T' | '4T'
    fecha_inicio_periodo: str | None  # ISO date
    fecha_fin_periodo: str | None
    fecha_limite_presentacion: str | None
    dias_para_vencimiento: int | None

    # Duplicate detection (set by verificar_duplicado)
    presentacion_duplicada: bool
    csv_presentacion_previa: str | None
    quiere_rectificativa: bool | None  # None = not yet asked

    # Sin actividad (casuistica C01)
    sin_actividad: bool | None  # None = not yet determined

    # Invoice collection (set by recopilar_datos / ocr_factura)
    facturas_emitidas: list[dict]
    facturas_recibidas: list[dict]
    facturas_pendientes_ocr: list[str]
    facturas_baja_confianza: list[dict]

    # Calculation (set by calcular — calls calcular_m303(), never computes itself)
    resultado_m303: dict | None
    errores_coherencia: list[str]

    # Summary / confirmation (set by resumir / confirmar)
    mensaje_resumen: str | None
    confirmado: bool
    quiere_revisar: bool
    cancelado: bool

    # Conversation
    mensajes: list[MensajeChat]

    # Observability (CA-F3-10)
    tokens_usados: int
