"""
Fase 2a (T2): diagnóstico de EDGAR para los tickers del panel.

Para cada ticker: CIK (o "sin CIK" → caso D7), formularios, taxonomía, moneda de los estados y, para cada campo de
la tabla de conceptos (tests/edgar.py), el concepto XBRL elegido, su unidad, los periodos disponibles (anual,
trimestral, acumulados) y las reexpresiones de los ejercicios. Registra también la latencia y el tamaño de la descarga.

    cd finanzer_next/backend
    python3 tests/edgar_diag.py                       # panel + HSBC SHEL UL TM; caché en tests/fixtures/edgar/raw
    python3 tests/edgar_diag.py --tickers BCS UL      # solo esos
    python3 tests/edgar_diag.py --markdown            # además, las tablas para F2_EDGAR_DIAGNOSTICO.md

Escribe tests/fixtures/edgar/diag.json y, por ticker, tests/fixtures/edgar/<T>.json con solo los conceptos de la
tabla desde 2020, de 10-K/10-Q/20-F/40-F/6-K, más los filings con XBRL que companyfacts no trae (el extracto que
usa la verificación de T3 sin red). Ningún secreto en la salida.
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import edgar as E  # noqa: E402

EXTRA = ["HSBC", "SHEL", "UL", "TM"]           # T1: panel ampliado a emisores extranjeros
SINCE = "2020-01-01"
FORMS = E.ANNUAL_FORMS | E.QUARTERLY_FORMS | {"6-K", "6-K/A"}
KEEP = ("start", "end", "val", "form", "filed", "accn")


def panel_tickers():
    import fixture_backend as fb
    return [t for t in fb.PANEL_TICKERS] + [t for t in EXTRA if t not in fb.PANEL_TICKERS]


def extract(facts, tax):
    """Extracto del companyfacts: solo los conceptos de la tabla (y dei), hechos con fin desde SINCE."""
    keep = {"dei": {c for s in E.CONCEPTS.values() for c in s.get("dei", [])}, tax: set()}
    for s in E.CONCEPTS.values():
        keep[tax].update(s.get("us" if tax == "us-gaap" else "ifrs", []))
    keep[tax].update(E.EXTRACT_EXTRA["us" if tax == "us-gaap" else "ifrs"])
    out = {"cik": facts.get("cik"), "entityName": facts.get("entityName"), "taxonomy": tax, "facts": {}}
    for tx, concepts in keep.items():
        for c in sorted(concepts):
            node = facts.get("facts", {}).get(tx, {}).get(c)
            if not node:
                continue
            units = {u: [{k: f[k] for k in KEEP if k in f} for f in fs
                         if f["end"] >= SINCE and (tx == "dei" or f.get("form") in FORMS)]
                     for u, fs in node.get("units", {}).items()}
            units = {u: fs for u, fs in units.items() if fs}
            if units:
                out["facts"].setdefault(tx, {})[c] = {"label": node.get("label"), "units": units}
    return out


def diag_one(t, ciks, refresh=False):
    row = {"ticker": t}
    m = ciks.get(t) or ciks.get(t.replace("-", "."))
    if not m:
        row["cik"] = None
        row["d7"] = "sin CIK"
        return row, None
    cik = m["cik_str"]
    row.update(cik=cik, entity=m["title"])
    sub, smeta = E.submissions(cik, refresh)
    if sub:
        rec = sub.get("filings", {}).get("recent", {})
        forms = rec.get("form", [])
        annual = [(d, f) for f, d in zip(forms, rec.get("reportDate", [])) if f in E.ANNUAL_FORMS and d]
        row["last_annual_report"] = max(annual)[0] if annual else None
        row["filer"] = {"category": sub.get("category"), "fiscal_year_end": sub.get("fiscalYearEnd"),
                        "sic": sub.get("sic"), "sic_desc": sub.get("sicDescription"),
                        "forms_recent": {f: forms.count(f) for f in sorted(set(forms)) if f in
                                         ("10-K", "10-Q", "20-F", "40-F", "6-K", "8-K", "F-6", "F-6EF", "F-6 POS")}}
    facts, fmeta = E.company_facts(cik, refresh)
    row["download"] = {k: fmeta.get(k) for k in ("status", "seconds", "bytes", "fetched_at")}
    for pc in E.PREDECESSORS.get(t, []):
        older, ometa = E.company_facts(pc, refresh)
        if older:
            row["predecessor"] = {"cik": pc, "entity": older.get("entityName"),
                                  "download": {k: ometa.get(k) for k in ("status", "seconds", "bytes")}}
            facts = E.merge_facts(facts, older) if facts else older
    if not facts:
        row["taxonomy"] = None
        row["d7"] = f"CIK sin companyfacts (HTTP {fmeta.get('status')})"
        return row, None
    tax = E.taxonomy(facts)
    unit = E.reporting_unit(facts, tax)
    row.update(taxonomy=tax, currency=unit)
    assets = E.concept_facts(facts, tax, "Assets", unit)
    row["xbrl_last_fy"] = max((x["end"] for x in assets if x.get("form") in E.ANNUAL_FORMS), default=None)
    row["xbrl_last_q"] = max((x["end"] for x in assets if x.get("form") in E.QUARTERLY_FORMS), default=None)
    # el último 10-K/20-F presentado no está (aún) en companyfacts
    row["xbrl_lag"] = bool(row.get("last_annual_report") and row["xbrl_last_fy"]
                           and row["last_annual_report"] > row["xbrl_last_fy"])
    row["fields"] = {f: E.resolve(facts, f, tax, unit) for f in E.CONCEPTS}
    # El diagnóstico describe companyfacts tal cual; el extracto para T3 añade los filings con XBRL que la API no
    # trae (F2_EDGAR_DIAGNOSTICO §6.2), leídos de su instancia.
    full, added = E.supplement(cik, facts, refresh)
    row["supplemented"] = [{k: a.get(k) for k in ("form", "filed", "report", "accn", "file", "bytes", "seconds")}
                           for a in added]
    return row, extract(full, tax)


def ticker_table(rows):
    lines = ["| Ticker | CIK | Formularios | Tax. | Moneda | Cierre FY | Último FY en XBRL | Último trimestre | "
             "Campos (vigentes / con concepto) | FY reexpresados | JSON | Descarga |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    n = len(E.CONCEPTS)
    for r in rows:
        if not r.get("fields"):
            lines.append(f"| {r['ticker']} | {r.get('cik') or 'sin CIK'} | — | — | — | — | — | — | — | — | "
                         f"— | {r.get('d7')} |")
            continue
        fr = (r.get("filer") or {}).get("forms_recent", {})
        forms = " ".join(f"{k}×{v}" for k, v in fr.items() if k in ("10-K", "10-Q", "20-F", "40-F", "6-K"))
        fl = r["fields"].values()
        live = sum(1 for x in fl if x.get("concept") and not x.get("stale"))
        has = sum(1 for x in fl if x.get("concept"))
        rest = sum(1 for x in fl if x.get("restated_fy"))
        d = r["download"]
        lag = " ⚠ falta el último" if r.get("xbrl_lag") else ""
        pred = f" (+ CIK {r['predecessor']['cik']})" if r.get("predecessor") else ""
        lines.append(
            f"| {r['ticker']} | {r['cik']}{pred} | {forms} | {r['taxonomy']} | {r['currency']} | "
            f"{(r.get('filer') or {}).get('fiscal_year_end') or '—'} | {r['xbrl_last_fy']}{lag} | "
            f"{r.get('xbrl_last_q') or '— (sin 10-Q)'} | {live}/{has} de {n} | {rest} | "
            f"{d['bytes'] / 1e6:.1f} MB | {d['seconds']:.2f} s |")
    return "\n".join(lines)


def field_table(rows):
    ok = [r for r in rows if r.get("fields")]
    lines = ["| Campo | Con concepto vigente | Sin concepto | Concepto que deja de llegar al último FY |",
             "|---|---|---|---|"]
    for f in E.CONCEPTS:
        live = [r["ticker"] for r in ok if r["fields"][f].get("concept") and not r["fields"][f].get("stale")]
        none = [r["ticker"] for r in ok if not r["fields"][f].get("concept")]
        stale = [f"{r['ticker']} ({r['fields'][f]['last_end'][:7]})" for r in ok
                 if r["fields"][f].get("concept") and r["fields"][f].get("stale")]
        lines.append(f"| {f} | {len(live)}/{len(ok)} | {' '.join(none) or '—'} | {' '.join(stale) or '—'} |")
    return "\n".join(lines)


def concept_usage(rows):
    """Por campo: qué concepto se eligió y en cuántos tickers."""
    out = {}
    for r in rows:
        for f, x in (r.get("fields") or {}).items():
            if x.get("concept") and not x.get("stale"):
                out.setdefault(f, {}).setdefault(x["concept"], []).append(r["ticker"])
    return out


def restatements(rows, min_change=0.01):
    out = []
    for r in rows:
        for f, x in (r.get("fields") or {}).items():
            for end, ch in x.get("restated_fy") or []:
                if ch >= min_change and end >= "2021":
                    out.append((r["ticker"], f, end, ch))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="*")
    ap.add_argument("--refresh", action="store_true", help="vuelve a descargar aunque esté en caché")
    ap.add_argument("--markdown", action="store_true")
    a = ap.parse_args()
    tickers = a.tickers or panel_tickers()
    ciks = E.cik_map(a.refresh)
    rows = []
    E.EDGAR_DIR.mkdir(parents=True, exist_ok=True)
    for t in tickers:
        row, ex = diag_one(t, ciks, a.refresh)
        rows.append(row)
        if ex:
            (E.EDGAR_DIR / f"{t}.json").write_text(json.dumps(ex, sort_keys=True, separators=(",", ":")))
        n = sum(1 for x in (row.get("fields") or {}).values() if x.get("concept"))
        d = row.get("download") or {}
        print(f"{t:6} CIK={row.get('cik')!s:>8} {row.get('taxonomy')!s:9} {row.get('currency')!s:4} "
              f"campos={n}/{len(E.CONCEPTS)} {d.get('bytes', 0) / 1e6:6.2f} MB {d.get('seconds')}s"
              + (f"  D7: {row['d7']}" if row.get("d7") else ""), flush=True)
    (E.EDGAR_DIR / "diag.json").write_text(json.dumps(rows, indent=1, sort_keys=True, ensure_ascii=False))
    secs = [r["download"]["seconds"] for r in rows if (r.get("download") or {}).get("bytes")]
    mbs = [r["download"]["bytes"] / 1e6 for r in rows if (r.get("download") or {}).get("bytes")]
    if secs:
        print(f"\ndescarga companyfacts: mediana {statistics.median(secs):.2f}s (máx {max(secs):.2f}s), "
              f"tamaño mediana {statistics.median(mbs):.1f} MB (máx {max(mbs):.1f} MB)")
    if a.markdown:
        print("\n" + ticker_table(rows) + "\n\n" + field_table(rows))
        for f, use in concept_usage(rows).items():
            print(f"\n{f}: " + "; ".join(f"{c} ({len(ts)}: {' '.join(ts)})" for c, ts in use.items()))
        print("\nReexpresiones ≥ 1% (ejercicios desde 2021):")
        for t, f, end, ch in restatements(rows):
            print(f"  {t:6} {f:24} {end} {ch:.1%}")


if __name__ == "__main__":
    main()
