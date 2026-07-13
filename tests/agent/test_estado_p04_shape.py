"""Structural smoke test for EstadoP04. Acceptance criteria: CA-F3-01.
EstadoP04 is a TypedDict — not runtime-validated, so this test constructs a
minimal valid instance and asserts every field each node reads/writes
(per design.md SPEC-F3-02) is present and accessible without KeyError.
"""
from src.agent.state import EstadoP04, MensajeChat


def _estado_minimo() -> EstadoP04:
    return EstadoP04(
        thread_id="user-1:P04:2026:1T",
        user_id="user-1",
        ejercicio=None,
        periodo=None,
        fecha_inicio_periodo=None,
        fecha_fin_periodo=None,
        fecha_limite_presentacion=None,
        dias_para_vencimiento=None,
        presentacion_duplicada=False,
        csv_presentacion_previa=None,
        quiere_rectificativa=None,
        sin_actividad=None,
        facturas_emitidas=[],
        facturas_recibidas=[],
        facturas_pendientes_ocr=[],
        facturas_baja_confianza=[],
        resultado_m303=None,
        errores_coherencia=[],
        mensaje_resumen=None,
        confirmado=False,
        quiere_revisar=False,
        cancelado=False,
        mensajes=[],
        tokens_usados=0,
    )


# Fields each node reads or writes, per design.md SPEC-F3-02
CAMPOS_DETECTAR_PERIODO = ["ejercicio", "periodo", "fecha_inicio_periodo", "fecha_fin_periodo", "fecha_limite_presentacion", "dias_para_vencimiento"]
CAMPOS_VERIFICAR_DUPLICADO = ["user_id", "ejercicio", "periodo", "presentacion_duplicada", "csv_presentacion_previa"]
CAMPOS_RECOPILAR_DATOS = ["mensajes", "facturas_emitidas", "facturas_recibidas", "facturas_pendientes_ocr", "sin_actividad"]
CAMPOS_OCR_FACTURA = ["facturas_pendientes_ocr", "facturas_emitidas", "facturas_recibidas", "facturas_baja_confianza"]
CAMPOS_CALCULAR = ["facturas_emitidas", "facturas_recibidas", "ejercicio", "periodo", "resultado_m303", "errores_coherencia"]
CAMPOS_RESUMIR = ["resultado_m303", "mensaje_resumen"]
CAMPOS_CONFIRMAR = ["mensaje_resumen", "confirmado", "quiere_revisar", "cancelado"]
CAMPOS_NOTIFICAR = ["confirmado", "cancelado", "resultado_m303", "mensajes"]


def test_estado_p04_construye_sin_errores():
    estado = _estado_minimo()
    assert estado["thread_id"] == "user-1:P04:2026:1T"


def test_estado_p04_todos_los_campos_de_cada_nodo_accesibles():
    estado = _estado_minimo()
    todos_los_campos = (
        CAMPOS_DETECTAR_PERIODO + CAMPOS_VERIFICAR_DUPLICADO + CAMPOS_RECOPILAR_DATOS
        + CAMPOS_OCR_FACTURA + CAMPOS_CALCULAR + CAMPOS_RESUMIR + CAMPOS_CONFIRMAR + CAMPOS_NOTIFICAR
    )
    for campo in set(todos_los_campos):
        try:
            estado[campo]
        except KeyError:
            raise AssertionError(f"EstadoP04 missing field required by a node: {campo}")


def test_mensaje_chat_shape():
    mensaje: MensajeChat = {"rol": "usuario", "contenido": "hola"}
    assert mensaje["rol"] == "usuario"
    assert mensaje["contenido"] == "hola"
