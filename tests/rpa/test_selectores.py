"""SPEC-F4-01: selector map is external, never hardcoded in Python.
Acceptance criteria: CA-F4-10.
"""
import ast
import re
from pathlib import Path

from src.rpa.aeat.selectores import cargar_selectores

REPO_ROOT = Path(__file__).resolve().parents[2]
RPA_AEAT_DIR = REPO_ROOT / "src" / "rpa" / "aeat"

# Real CSS/aria selectors in aeat_m303.yml always contain one of these
# syntactic markers (#id, [attr=...], :has-text(...)). Plain snake_case
# identifiers (dict keys, variable names) never do, so this avoids false
# positives like the dict key "selector_ejercicio".
SELECTOR_LIKE = re.compile(r"[#\[]|:has-text\(")


def test_cargar_selectores_devuelve_dict_completo():
    selectores = cargar_selectores()

    for clave in (
        "clave_pin", "navegacion", "pagina_1_identificacion",
        "pagina_2_devengado", "pagina_3_deducible", "pagina_4_resultado",
        "acciones", "mensajes_error",
    ):
        assert clave in selectores, f"falta la clave '{clave}' en el selector map"
        assert isinstance(selectores[clave], dict)
        assert len(selectores[clave]) > 0


def test_cargar_selectores_casillas_devengado_incluye_01_a_09():
    selectores = cargar_selectores()
    devengado = selectores["pagina_2_devengado"]
    for casilla in ("casilla_01", "casilla_02", "casilla_03", "casilla_07", "casilla_08", "casilla_09"):
        assert casilla in devengado


def test_ningun_modulo_rpa_hardcodea_selectores():
    """Static check: no .py file under src/rpa/aeat/ (except selectores.py,
    which only loads the YAML) may contain a CSS/aria selector string
    literal. Selectors must be threaded in as parameters, sourced from
    cargar_selectores()."""
    excepciones = {"selectores.py"}

    for archivo in RPA_AEAT_DIR.glob("*.py"):
        if archivo.name in excepciones or archivo.name == "__init__.py":
            continue

        arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
                valor = nodo.value.strip()
                if SELECTOR_LIKE.match(valor):
                    raise AssertionError(
                        f"selector aparentemente hardcodeado en {archivo.name}: {valor!r}"
                    )
