"""
Fase 7 (PLAN §4, punto 2): revisión mensual de los parámetros de mercado (config/review.toml). Sin red.

    cd finanzer_next/backend
    ../.venv313/bin/python tests/revision_parametros.py [--hoy AAAA-MM-DD] [--out informe.md]

Por parámetro: valor de hoy, fuente, fecha del dato, fecha de consulta y estado:
  · "vigente": aún no ha llegado la próxima publicación esperada (fecha del dato + cadencia; si la consulta fue
    posterior a esa fecha, no había otra más nueva y cuenta desde la consulta);
  · "revisar": ya debería haber una más reciente en la fuente;
  · "sin fuente": PROVISIONAL, fijado a mano (no hay fecha que vigilar; hay que sustituirlo).
Código de salida 1 si algo está por revisar o sin fuente (para encadenarlo con la vigilancia semanal).
"""
import argparse
import datetime as _dt
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from settings import cfg  # noqa: E402


def estado(item, hoy: _dt.date):
    """(estado, próxima fecha esperada o None)."""
    if not item["consulted"]:
        return "sin fuente", None
    cad = _dt.timedelta(days=item["cadence_days"])
    consulted = _dt.date.fromisoformat(item["consulted"])
    base = _dt.date.fromisoformat(item["published"]) if item["published"] else consulted
    # Si se consultó después de la publicación esperada, se miró y no había otra más nueva: cuenta desde la consulta.
    if consulted >= base + cad:
        base = consulted
    due = base + cad
    return ("revisar" if hoy >= due else "vigente"), due


def _valor(key):
    v = cfg(key)
    if isinstance(v, float):
        return f"{v:.4f}"
    if isinstance(v, (int, str)):
        return str(v)
    return f"tabla ({len(v)} entradas)"


def informe(hoy: _dt.date):
    rows, malos = [], 0
    for name, it in cfg("review.parameters").items():
        st, due = estado(it, hoy)
        malos += st != "vigente"
        rows.append(f"| {name} | `{it['key']}` | {_valor(it['key'])} | {st} | {it['published'] or '—'} | "
                    f"{it['consulted'] or '—'} | {due or '—'} | {it['source']} |")
    head = (f"# Revisión de parámetros · {hoy}\n\n{malos} por revisar o sin fuente.\n\n"
            "| Parámetro | Clave | Valor | Estado | Dato de | Consultado | Próxima publicación | Fuente |\n"
            "|---|---|---|---|---|---|---|---|")
    return head + "\n" + "\n".join(rows) + "\n", malos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hoy", default=_dt.date.today().isoformat())
    ap.add_argument("--out")
    a = ap.parse_args()
    txt, malos = informe(_dt.date.fromisoformat(a.hoy))
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(txt)
    print(txt)
    return 1 if malos else 0


if __name__ == "__main__":
    sys.exit(main())
