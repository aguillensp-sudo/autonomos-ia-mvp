"""resumir — human-language summary of resultado_m303. Acceptance criteria:
CA-F3-05. Required fields are filled deterministically in Python (not left
to the LLM to paraphrase, which could drop a required value) — the LLM call
adds a short friendly intro sentence in front of the fixed template, per
specs/agente-conversacional/design.md SPEC-F3-04.
"""
from src.agent.llm_client import crear_cliente_anthropic
from src.agent.prompts.p04_system_prompt import _RESUMEN_TEMPLATE

_MODEL = "claude-sonnet-5"

_TIPO_RESULTADO_HUMANO = {
    "a_ingresar": "A INGRESAR",
    "a_compensar": "A COMPENSAR",
    "a_devolver": "A DEVOLVER",
    "sin_actividad": "SIN ACTIVIDAD",
}


def _renderizar_plantilla(estado: dict) -> str:
    resultado = estado["resultado_m303"]
    return _RESUMEN_TEMPLATE.format(
        periodo=resultado["periodo"],
        ejercicio=resultado["ejercicio"],
        total_devengado=resultado["total_devengado"],
        total_deducible=resultado["total_deducible"],
        resultado=resultado["resultado"],
        tipo_resultado_humano=_TIPO_RESULTADO_HUMANO.get(resultado["tipo_resultado"], resultado["tipo_resultado"]),
        num_emitidas=len(estado.get("facturas_emitidas", [])),
        num_recibidas=len(estado.get("facturas_recibidas", [])),
        fecha_limite_presentacion=estado.get("fecha_limite_presentacion"),
        dias_para_vencimiento=estado.get("dias_para_vencimiento"),
    )


def resumir(estado: dict) -> dict:
    plantilla_rellena = _renderizar_plantilla(estado)

    client = crear_cliente_anthropic()
    respuesta = client.messages.create(
        model=_MODEL,
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": (
                "Escribe UNA frase breve y amigable en español, a modo de "
                "introducción, para presentar el siguiente resumen fiscal. "
                "Responde solo con esa frase, sin repetir el resumen:\n\n"
                f"{plantilla_rellena}"
            ),
        }],
    )

    intro = "".join(b.text for b in respuesta.content if b.type == "text").strip()
    mensaje_resumen = f"{intro}\n\n{plantilla_rellena}" if intro else plantilla_rellena

    return {
        "mensaje_resumen": mensaje_resumen,
        "tokens_usados": estado.get("tokens_usados", 0) + respuesta.usage.input_tokens + respuesta.usage.output_tokens,
    }
