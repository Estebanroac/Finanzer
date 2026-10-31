"""
F10 · N2 (revisión del informe de NVIDIA): genera config/peer_metrics.tsv, los múltiplos y márgenes de cada empresa del
universo (config/universe.tsv: S&P 500 + ADR principales), para el respaldo de la referencia de la industria.

    cd finanzer_next/backend
    ../.venv313/bin/python tools/build_peer_metrics.py [--out config/peer_metrics.tsv]

El respaldo (lib/industry_bench.peer_median) es la mediana de los pares del universo de la misma industria de
Damodaran, sin la propia empresa. Se usa cuando la referencia de Damodaran sin la empresa no se puede calcular (sin sus
cifras a la fecha del conjunto) o lo que queda no es representativo (pesa ≥ `max_weight` o quedan menos de `min_firms`
empresas).

Fuente: Yahoo Finance (yfinance `Ticker.info`), una instantánea con su fecha en la cabecera:
  · pe = trailingPE; ev_ebitda = enterpriseToEbitda; pb = priceToBook (un múltiplo ≤ 0 no es una referencia: sin dato);
  · roe = returnOnEquity; gross_margin, operating_margin, net_margin = grossMargins, operatingMargins, profitMargins (un
    margen de 0 o 1 es un artefacto de definición, como en tools/damodaran_import.py: sin dato);
  · de = debtToEquity / 100 (Yahoo lo da en porcentaje).
Sin ROIC ni cobertura de intereses: Yahoo no los da; en el respaldo esas filas quedan sin referencia.

Herramienta local con red (no corre en Render). Si menos del 90 % de las empresas da algún dato, termina con error y NO
sobrescribe el archivo.
"""
import argparse
import datetime as dt
import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import universe  # noqa: E402

FIELDS = (("pe", "trailingPE", 1.0), ("ev_ebitda", "enterpriseToEbitda", 1.0), ("pb", "priceToBook", 1.0),
          ("roe", "returnOnEquity", 1.0), ("gross_margin", "grossMargins", 1.0),
          ("operating_margin", "operatingMargins", 1.0), ("net_margin", "profitMargins", 1.0),
          ("de", "debtToEquity", 0.01))
MULTIPLES = ("pe", "ev_ebitda", "pb")
MARGINS = ("gross_margin", "operating_margin", "net_margin")
MIN_COVERAGE = 0.9


def metrics(info):
    out = {}
    for key, src, scale in FIELDS:
        try:
            v = float(info.get(src)) * scale
        except (TypeError, ValueError):
            v = math.nan
        if not math.isfinite(v) or (key in MULTIPLES and v <= 0) or \
                (key in MARGINS and (abs(v) < 0.002 or abs(v - 1) < 0.002)):
            v = math.nan
        out[key] = v
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config",
                                                  "peer_metrics.tsv"))
    ap.add_argument("--pause", type=float, default=0.4)
    a = ap.parse_args()
    import yfinance as yf
    rows, failed = [], []
    for r in universe.load():
        s = r["symbol"]
        info = {}
        for attempt in range(2):
            try:
                info = yf.Ticker(s).info or {}
                break
            except Exception as e:                     # noqa: BLE001 — se reintenta una vez y se registra
                if attempt:
                    failed.append(f"{s}: {type(e).__name__}")
                time.sleep(2.0)
        m = metrics(info)
        if not any(math.isfinite(v) for v in m.values()):
            failed.append(s)
        rows.append((s, r.get("damodaran_industry") or "", r.get("damodaran_region") or "", m))
        time.sleep(a.pause)
    ok = sum(1 for *_x, m in rows if any(math.isfinite(v) for v in m.values()))
    print(f"{ok} de {len(rows)} empresas con algún dato; sin dato: {failed}")
    if ok < MIN_COVERAGE * len(rows):
        raise SystemExit("cobertura insuficiente: no se escribe el archivo")
    today = dt.date.today().isoformat()
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(f"# GENERADO por tools/build_peer_metrics.py el {today} desde Yahoo Finance (yfinance Ticker.info)\n")
        fh.write("# Universo: config/universe.tsv. Definiciones: la cabecera de la herramienta. nan = sin dato.\n")
        fh.write("\t".join(["symbol", "damodaran_industry", "damodaran_region"] + [k for k, *_x in FIELDS]) + "\n")
        for s, ind, reg, m in rows:
            fh.write("\t".join([s, ind, reg] + ["nan" if not math.isfinite(m[k]) else repr(round(m[k], 4))
                                                for k, *_x in FIELDS]) + "\n")
    print(f"escrito {a.out}")


if __name__ == "__main__":
    main()
