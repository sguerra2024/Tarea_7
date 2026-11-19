"""Abre la edición de escritorio de Agente TRIZ incluida en Tarea_7."""

import runpy
from pathlib import Path

from dotenv import load_dotenv


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parent
    load_dotenv(raiz / ".env", override=False)
    runpy.run_path(str(raiz / "escritorio" / "launch.py"), run_name="__main__")
