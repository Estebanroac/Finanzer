"""
Corre un script de Python con el modo «fecha de corte» instalado (tests/hacia_atras/corte.py).

    python tests/hacia_atras/corte_run.py [--solo-reloj] <script.py> [args…]

--solo-reloj: solo congela el reloj en el corte (el replay sin red de los datos ya cortados: el motor juzga fechas con
«hoy» = 5-nov-2025). No importa nada de este árbol: sirve para correr el script de OTRA versión del motor (B, A14)
sin mezclar sus módulos con los de este. Sin él, además filtra las fuentes en vivo (captura).
time_machine vive fuera del venv del proyecto: HACIA_ATRAS_PYLIB (carpeta con pip install --target).
"""
import datetime as dt
import os
import runpy
import sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
if os.environ.get("HACIA_ATRAS_PYLIB"):
    sys.path.append(os.environ["HACIA_ATRAS_PYLIB"])
_C = dt.date.fromisoformat(os.environ.get("HACIA_ATRAS_CORTE") or "2025-11-05")
CLOCK = dt.datetime(_C.year, _C.month, _C.day, 18, 0, tzinfo=ZoneInfo("America/New_York"))   # = corte.CLOCK


def main():
    argv = sys.argv[1:]
    only_clock = argv and argv[0] == "--solo-reloj"
    if only_clock:
        argv = argv[1:]
    script = os.path.abspath(argv[0])
    if only_clock:
        import time_machine
        time_machine.travel(CLOCK, tick=True).start()
    else:
        sys.path.insert(0, HERE)
        import corte
        assert corte.CLOCK == CLOCK
        corte.install(clock=True, sources=True)
    sys.path.insert(0, os.path.dirname(script))
    sys.argv = [script] + argv[1:]
    runpy.run_path(script, run_name="__main__")


if __name__ == "__main__":
    main()
