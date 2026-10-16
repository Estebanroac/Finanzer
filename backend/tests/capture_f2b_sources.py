"""
Fase 2b: captura (con red) de las fuentes que el análisis consulta desde la 2b y que los fixtures del panel (14 y
15-oct) y del juego local (11 y 12-oct) no traen, para el replay:

  · SEC EDGAR: la lista de emisores (solo los tickers capturados) y la lista de filings de cada CIK (lib/sec_edgar.py);
  · Finnhub: el calendario de resultados (aviso de resultados publicados de los emisores sin 8-K);
  · con --facts (T4), SOLO los hechos XBRL: companyfacts reducido de cada CIK (y de sus predecesores) y la instancia
    de cada filing que companyfacts aún no trae (lib/sec_edgar.py); no toca las listas ni el calendario.

Uso EXPLÍCITO, nunca automático. Las claves llegan por el entorno de esta orden y no se escriben:

    cd finanzer_next/backend
    SEC_EDGAR_USER_AGENT="$(security find-generic-password -s finanzer-sec-ua -w)" \\
    FINNHUB_API_KEY="$(security find-generic-password -s finanzer-finnhub -w)" \\
    ../.venv313/bin/python tests/capture_f2b_sources.py

El replay (fixture_backend) corta cada lista en la fecha de captura del ticker analizado: un filing o una publicación
posteriores no existían ese día.
"""
import argparse
import datetime as _dt
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f2b_fixtures as ff  # noqa: E402  (añade backend/ y lib/ al path)
import capture_history  # noqa: E402
import sec_edgar as edgar  # noqa: E402
import finnhub_fallback  # noqa: E402

CAL_FROM = "2025-01-01"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("symbols", nargs="*")
    ap.add_argument("--dir", default=ff.F2B_DIR)
    ap.add_argument("--facts", action="store_true", help="solo companyfacts e instancias pendientes (T4)")
    args = ap.parse_args(argv)
    if not edgar.user_agent():
        ap.error("falta SEC_EDGAR_USER_AGENT en el entorno (ver el uso)")
    if args.facts:
        return capture_facts([s.upper() for s in args.symbols], args.dir)
    if not finnhub_fallback.is_enabled():
        ap.error("falta FINNHUB_API_KEY en el entorno (ver el uso)")
    syms = [s.upper() for s in args.symbols] or [s for s in capture_history.default_symbols() if not s.startswith("^")]
    syms = sorted(set(syms))
    today = _dt.date.today().isoformat()
    tickers, report = {}, {}
    for s in syms:
        b = edgar.Budget(60.0)
        ent = edgar.cik_for(s, b)
        if ent is None:
            report[s] = {"cik": None}
            print(f"[{s}] sin CIK")
        else:
            tickers[s] = ent
            raw = edgar._get_json(edgar.SUBMISSIONS_URL.format(cik=ent["cik"]), b)
            ff.save_submissions(ent["cik"], raw, args.dir)
            n = len((raw.get("filings") or {}).get("recent", {}).get("form") or [])
            report[s] = {"cik": ent["cik"], "recent_filings": n}
            print(f"[{s}] CIK {ent['cik']}: {n} filings recientes")
        cal = finnhub_fallback.earnings_calendar(s, CAL_FROM, today)
        ff.save_calendar(s, cal, args.dir)
        report[s]["calendar_entries"] = None if cal is None else len(cal)
        time.sleep(1.1)        # Finnhub: ≤ 55 peticiones por minuto
    ff.save_tickers(tickers, args.dir)
    meta = {"captured_at_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "sources": {"edgar": "company_tickers.json (solo los tickers capturados) y submissions por CIK "
                                 f"(filings desde {ff.SINCE})",
                        "finnhub": f"/calendar/earnings desde {CAL_FROM}"},
            "replay": "cada lista se corta en la fecha de captura del ticker analizado (fixture_backend)",
            "symbols": report}
    with open(os.path.join(args.dir, "metadata.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    print(f"\n{len(tickers)}/{len(syms)} con CIK → {args.dir}")
    return 0


def capture_facts(symbols, base):
    """companyfacts reducido + instancias pendientes de los tickers del juego (o de `symbols`). Las descargas de la
    captura no tienen el límite de tiempo del análisis (un companyfacts llega a 8 MB)."""
    edgar.FETCHER = lambda url, _t: edgar.urllib_fetcher(url, 60.0)
    table = json.load(open(os.path.join(base, "edgar", "company_tickers.json"), encoding="utf-8"))
    syms = symbols or sorted(table)
    report = {}
    for s in syms:
        ent = table.get(s)
        if ent is None:
            print(f"[{s}] sin CIK en el juego: nada que capturar")
            continue
        b = edgar.Budget(600.0)
        fl = edgar.filings(ent["cik"], b)
        ciks = list(edgar._predecessors(s)) + [ent["cik"]]
        for c in ciks:
            try:
                ff.save_facts(c, edgar.company_facts(c, b), base)
            except edgar.NotFound:
                ff.save_facts_not_found(c, base)
                print(f"[{s}] CIK {c}: companyfacts 404")
        try:
            facts, log = edgar.facts_with_pending(ent["cik"], fl, b, edgar._predecessors(s))
        except edgar.NotFound:
            report[s] = {"ciks": ciks, "companyfacts": 404}
            continue
        for rec in log:
            if rec["read"]:
                acc = rec["accn"].replace("-", "")
                inst = edgar._cache.get(f"inst:{acc}")
                ff.save_instance(rec["accn"], inst[1], base)
        report[s] = {"ciks": ciks, "pending": [{k: r[k] for k in ("form", "date", "accn", "read", "reason")}
                                               for r in log]}
        print(f"[{s}] CIK {ent['cik']}: {len(log)} pendientes "
              + ", ".join(f"{r['form']} {r['date']}{'' if r['read'] else ' (sin leer: ' + str(r['reason']) + ')'}"
                          for r in log))
    meta_p = os.path.join(base, "metadata.json")
    meta = json.load(open(meta_p, encoding="utf-8"))
    meta["facts"] = {"captured_at_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
                     "source": "companyfacts reducido a sec_edgar.CONCEPTS e instancias XBRL de los filings que "
                               "companyfacts aún no traía (mínimas, mismos conceptos)",
                     "replay": "los hechos se cortan en `filed` ≤ fecha de captura del ticker analizado",
                     "symbols": report}
    with open(meta_p, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
