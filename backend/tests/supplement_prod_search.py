"""
Complementa los fixtures de PROD con la respuesta de la búsqueda de Yahoo
(/v1/finance/search), que el plan B empezó a consultar en la etapa 3 para
obtener sector e industria (bug a). Las capturas de prod son anteriores a esa
llamada, así que no la contienen.

La búsqueda NO exige crumb y responde igual desde cualquier IP (verificado: el
/api/search de prod devuelve resultados de Yahoo desde Render). Por eso se
captura desde aquí y se marca de forma explícita en metadata.supplements: no
es un dato capturado en Render.

    cd finanzer_next/backend
    ../.venv313/bin/python tests/supplement_prod_search.py [TICKERS] [--force]
"""
import argparse
import datetime as _dt
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend as fb  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tickers", nargs="*", default=fb.TICKERS)
    ap.add_argument("--force", action="store_true", help="reemplazar un complemento existente")
    args = ap.parse_args()
    logging.disable(logging.WARNING)
    import yf_adapter

    for sym in [t.upper() for t in args.tickers]:
        d = os.path.join(fb.fixtures_dir("prod"), sym)
        with open(os.path.join(d, "metadata.json"), encoding="utf-8") as fh:
            meta = json.load(fh)
        with open(os.path.join(d, "yahoo_http.json"), encoding="utf-8") as fh:
            http = json.load(fh)
        has = any("/finance/search" in e["url"] for e in http)
        if has and not args.force:
            print(f"[{sym}] ya tiene la búsqueda; usa --force para reemplazarla")
            continue
        http = [e for e in http if "/finance/search" not in e["url"]]
        with fb.record(fb.fixtures_dir("prod")) as store:
            prof = yf_adapter._search_profile(sym)
        entries = [e for e in store.http.get(sym, []) if "/finance/search" in e["url"]]
        if not entries:
            print(f"[{sym}] ERROR: no se grabó la búsqueda")
            continue
        http.extend(entries)
        sup = [s for s in meta.get("supplements", []) if s.get("endpoint") != "yahoo_search"]
        sup.append({
            "endpoint": "yahoo_search",
            "url": entries[0]["url"],
            "captured_at_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "captured_from": "local (IP residencial)",
            "reason": "llamada añadida al plan B en la etapa 3 (sector/industria); posterior a la captura de prod",
            "ip_agnostic_evidence": "endpoint sin crumb; /api/search de prod devuelve resultados de Yahoo desde Render",
            "result": prof,
        })
        meta["supplements"] = sup
        for name, payload in (("yahoo_http.json", http), ("metadata.json", meta)):
            with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=1, sort_keys=True, ensure_ascii=False)
                fh.write("\n")
        print(f"[{sym}] OK búsqueda añadida: {prof}")


if __name__ == "__main__":
    main()
