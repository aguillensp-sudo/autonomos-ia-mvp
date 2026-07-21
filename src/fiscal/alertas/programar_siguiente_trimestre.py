"""SPEC-F5-03 — next-quarter alert scheduling (CA-F5-07). Pure date
arithmetic + one `alerta` insert, called by the ARQ worker immediately after
a successful presentation. Deadlines per docs/domain-context.md's filing
deadlines table; weekend shift reuses detectar_periodo's own rule (Phase 3)
so both places agree on what "next business day" means.
"""
from datetime import date, timedelta
from typing import Any

from src.agent.nodes.detectar_periodo import _siguiente_dia_habil

_SIGUIENTE_PERIODO = {
    "1T": ("2T", 0, (7, 20)),
    "2T": ("3T", 0, (10, 20)),
    "3T": ("4T", 1, (1, 30)),
    "4T": ("1T", 1, (4, 20)),
}


def programar_alerta_siguiente_trimestre(client: Any, user_id: str, ejercicio: int, periodo: str) -> None:
    siguiente_periodo, offset_ejercicio_limite, (mes_limite, dia_limite) = _SIGUIENTE_PERIODO[periodo]
    ejercicio_siguiente = ejercicio + (1 if periodo == "4T" else 0)

    fecha_limite = _siguiente_dia_habil(date(ejercicio + offset_ejercicio_limite, mes_limite, dia_limite))
    fecha_alerta = fecha_limite - timedelta(days=15)

    client.table("alerta").insert({
        "user_id": user_id,
        "tipo": "vencimiento_m303",
        "proceso": "P04",
        "ejercicio": ejercicio_siguiente,
        "periodo": siguiente_periodo,
        "fecha_alerta": fecha_alerta.isoformat(),
        "fecha_limite": fecha_limite.isoformat(),
        "mensaje": f"Tu IVA de {siguiente_periodo} {ejercicio_siguiente} vence el {fecha_limite.strftime('%d/%m/%Y')}.",
    }).execute()
