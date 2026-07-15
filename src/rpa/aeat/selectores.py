"""Loads the external AEAT selector map (SPEC-F4-01). This is the only
module allowed to reference the YAML file's path — every other RPA module
receives selectors as a parameter, never imports the path itself.
"""
from functools import lru_cache
from pathlib import Path

import yaml

SELECTOR_MAP_PATH = Path(__file__).resolve().parents[1] / "selectors" / "aeat_m303.yml"


@lru_cache(maxsize=1)
def cargar_selectores() -> dict:
    with open(SELECTOR_MAP_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)
