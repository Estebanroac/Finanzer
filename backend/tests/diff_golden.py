"""
Diferencias entre el comportamiento ACTUAL (desde fixtures) y los golden.

    cd finanzer_next/backend
    python3 tests/diff_golden.py                  # los 6 tickers, entorno local
    python3 tests/diff_golden.py --env prod       # juego de producción
    python3 tests/diff_golden.py NFLX SNOW        # algunos
    python3 tests/diff_golden.py --full           # sin recortar listas/diff de PDF
    python3 tests/diff_golden.py --regenerate     # reescribe golden (pide confirmación)
    python3 tests/diff_golden.py --regenerate --yes NFLX
    python3 tests/diff_golden.py --local-vs-prod  # local → prod, con la causa en inputs crudos

Por ticker muestra `campo: anterior → nuevo`, agrupado por bloque (score,
Piotroski, Altman, DCF, grid, alertas, métricas, otros) y el diff del texto
del PDF. Código de salida 1 si hay diferencias (útil en CI), 0 si no.

Los golden describen el comportamiento ACTUAL (con sus bugs), no el correcto.
Regenerarlos es una decisión explícita: nunca ocurre de forma automática.
"""
import argparse
import difflib
import json
import logging
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend as fb  # noqa: E402

BLOCKS = [
    ("score", ("score", "company_type", "is_growth", "financial_health")),
    ("piotroski", ("piotroski_f",)),
    ("altman", ("altman_z",)),
    ("dcf", ("dcf", "graham_number", "graham_margin")),
    ("grid", ("sensitivity",)),
    ("alertas", ("alerts",)),
    ("métricas", ("key_metrics", "ratios")),
]
_BLOCK_OF = {k: name for name, keys in BLOCKS for k in keys}
_MISSING = "∅"


def _flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        if not obj and prefix:
            out[prefix] = {}
        for k, v in obj.items():
            out.update(_flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        if not obj and prefix:
            out[prefix] = []
        for i, v in enumerate(obj):
            out.update(_flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def _fmt(v, full):
    s = _MISSING if v is _MISSING else json.dumps(v, ensure_ascii=False)
    return s if full or len(s) <= 90 else s[:87] + "..."


def diff_analysis(old, new):
    """{bloque: [(ruta, anterior, nuevo)]} sobre valores ya normalizados."""
    fo, fn = _flatten(old), _flatten(new)
    groups = {}
    for path in sorted(set(fo) | set(fn)):
        a, b = fo.get(path, _MISSING), fn.get(path, _MISSING)
        if a == b:
            continue
        top = path.split(".", 1)[0].split("[", 1)[0]
        groups.setdefault(_BLOCK_OF.get(top, "otros"), []).append((path, a, b))
    return groups


def diff_text(old, new, full, limit=60):
    lines = list(difflib.unified_diff(old.splitlines(), new.splitlines(),
                                      "golden", "actual", n=0, lineterm=""))
    if not full and len(lines) > limit:
        lines = lines[:limit] + [f"... ({len(lines) - limit} líneas más; usa --full)"]
    return lines


def load_golden(sym, golden_dir):
    jpath, tpath = fb.golden_paths(sym, golden_dir)
    if not os.path.isfile(jpath):
        return None, None
    with open(jpath, encoding="utf-8") as fh:
        gj = json.load(fh)
    with open(tpath, encoding="utf-8") as fh:
        gt = fh.read()
    return gj, gt


def write_golden(sym, analysis, text, golden_dir):
    os.makedirs(golden_dir, exist_ok=True)
    jpath, tpath = fb.golden_paths(sym, golden_dir)
    with open(jpath, "w", encoding="utf-8") as fh:
        fh.write(fb.stable_json(analysis))
    with open(tpath, "w", encoding="utf-8") as fh:
        fh.write(text)
    return jpath, tpath


def report(sym, gj, gt, analysis, text, full):
    """Imprime las diferencias de un ticker; devuelve True si hay alguna."""
    print(f"\n{'═' * 70}\n {sym}\n{'═' * 70}")
    if gj is None:
        print("  (sin golden: ejecuta con --regenerate para crearlo)")
        return True
    new = json.loads(fb.stable_json(analysis))
    groups = diff_analysis(gj, new)
    pdf_lines = diff_text(gt, text, full)
    if not groups and not pdf_lines:
        print("  sin cambios")
        return False
    order = [name for name, _ in BLOCKS] + ["otros"]
    for name in order:
        items = groups.get(name)
        if not items:
            continue
        print(f"\n  [{name}] {len(items)} cambio(s)")
        shown = items if full else items[:40]
        for path, a, b in shown:
            print(f"    {path}: {_fmt(a, full)} → {_fmt(b, full)}")
        if len(shown) < len(items):
            print(f"    ... ({len(items) - len(shown)} más; usa --full)")
    if pdf_lines:
        print(f"\n  [pdf] texto del informe")
        for line in pdf_lines:
            if not line.startswith(("---", "+++")):
                print(f"    {line}")
    return True


# ═══════════════════════ modo local-vs-prod (causas) ═══════════════════════
# Qué inputs del dict interno de yf_adapter (lo que consume el motor) explican
# cada campo de salida. Regla = (regex sobre la ruta de salida, [inputs]); un
# input terminado en ".*" abarca todas sus subclaves.
CAUSE_RULES = [
    (r"free_cash_flow|fcf_yield|pfcf|p_fcf|ev_fcf|fcf_to_net_income|^ratios\.fcf$",
     ["freeCashflow", "operatingCashflow", "capitalExpenditures", "marketCap"]),
    (r"operating_cash_flow", ["operatingCashflow"]),
    (r"^dcf\.|^sensitivity\.", ["freeCashflow", "revenueGrowth", "beta", "sharesOutstanding",
                                "totalDebt", "cash", "currentPrice"]),
    (r"revenue_growth|^is_growth|Crecimiento Ingresos|crecimiento|company_type",
     ["revenueGrowth"]),
    (r"earnings_growth|Crecimiento EPS|peg", ["earningsGrowth", "_yahoo_ratios.pegRatio", "trailingEps"]),
    (r"beta|wacc|discount_rates", ["beta"]),
    (r"(^|\.)pe$|(^|\.)eps$|earnings_yield|graham", ["trailingEps", "bookValue", "currentPrice"]),
    (r"forward_pe", ["forwardEps", "forwardPE", "_yahoo_ratios.forwardPE"]),
    (r"^piotroski_f|calidad|Piotroski", ["_prior_year.*", "_piotroski_current.*", "netIncome",
                                         "operatingCashflow"]),
    (r"^altman_z|solidez", ["totalAssets", "totalLiab", "retainedEarnings", "operatingIncome", "marketCap",
                            "totalCurrentAssets", "totalCurrentLiabilities", "totalRevenue"]),
    (r"roe|roa|margin|roic|rentabilidad", ["netIncome", "totalStockholderEquity", "totalAssets",
                                           "operatingIncome", "grossProfits", "totalRevenue", "_yahoo_ratios.*"]),
    (r"current_ratio|quick_ratio|cash_ratio", ["totalCurrentAssets", "totalCurrentLiabilities", "inventory",
                                               "cash", "_yahoo_ratios.currentRatio", "_yahoo_ratios.quickRatio"]),
    (r"debt|interest", ["totalDebt", "cash", "interestExpense", "totalStockholderEquity", "operatingIncome",
                        "_yahoo_ratios.debtToEquity", "_yahoo_ratios.interestCoverage"]),
    (r"ebitda|enterprise", ["ebitda", "totalDebt", "cash", "marketCap", "_yahoo_ratios.enterpriseValue",
                            "_yahoo_ratios.enterpriseToEbitda"]),
    (r"dividend|payout|shareholder|buyback", ["dividendRate", "dividendYield", "dividendsPaid", "payoutRatio",
                                              "_yahoo_ratios.dividendYield", "_yahoo_ratios.payoutRatio",
                                              "sharesOutstanding", "_prior_year.shares"]),
    (r"shares|market_cap|price", ["sharesOutstanding", "marketCap", "currentPrice",
                                  "fiftyTwoWeekHigh", "fiftyTwoWeekLow"]),
    (r"ffo", ["netIncome", "ebitda", "operatingIncome", "sharesOutstanding"]),
    (r"^profile\.|sector_info", ["sector", "industry", "longName", "exchange"]),
    (r"yearly_financials", ["_yearly_financials"]),
    (r"valoracion|Valoración", ["trailingEps", "forwardEps", "freeCashflow", "ebitda", "earningsGrowth",
                                "revenueGrowth", "_yahoo_ratios.pegRatio"]),
]
_RELEVANT_REL = 0.01   # cambio numérico relativo mínimo para considerarlo relevante
# Textos derivados de un valor ya listado: se omiten en este modo salvo --full.
_DERIVED_TEXT = re.compile(r"\.(reason|severity|detail|metric|interpretation|emoji|level_color)$|\.details\[\d+\]$"
                           r"|^sensitivity\.matrix\[")  # celdas del grid: se resumen en statistics.*


def _engine_inputs(sym, env, with_finnhub=True):
    """Dict interno de yf_adapter tras las defensas (lo que consume el motor)."""
    import copy as _copy
    import finnhub_fallback
    import yf_adapter
    with fb.replay(fb.fixtures_dir(env)) as st:
        st.load(sym)
        if st.meta[sym].get("finnhub", {}).get("participated"):
            os.environ["FINNHUB_API_KEY"] = "fixture-replay"
        orig = finnhub_fallback.enrich_info
        if not with_finnhub:
            finnhub_fallback.enrich_info = lambda info, *a, **k: info
        try:
            fb.reset_state()
            return _copy.deepcopy(yf_adapter.get_ticker_info(sym)), st.meta[sym]
        finally:
            finnhub_fallback.enrich_info = orig


def _source_summary(meta, n_finnhub):
    statuses = meta.get("yahoo", {}).get("http_statuses") or []
    ok = any(s == 200 for s in statuses) or (not statuses and meta.get("yahoo", {}).get("http_calls"))
    path = "quoteSummary 200 + estados yfinance" if ok and not meta["yahoo"].get("fallback_yfinance_used") \
        else f"quoteSummary {statuses or '?'} → fallback yfinance"
    fh = f"Finnhub rellenó {n_finnhub} campo(s)" if meta.get("finnhub", {}).get("participated") else "sin Finnhub"
    v = meta.get("versions", {})
    return f"{path} · {fh} · py{v.get('python')} yfinance {v.get('yfinance')} pandas {v.get('pandas')}"


def _human(v):
    if isinstance(v, bool) or v is None or not isinstance(v, (int, float)):
        return json.dumps(v, ensure_ascii=False)[:40] if not isinstance(v, str) else v[:40]
    a = abs(v)
    if a >= 1e9:
        return f"{v / 1e9:.2f}B"
    if a >= 1e6:
        return f"{v / 1e6:.1f}M"
    return f"{v:.4g}"


def _relevant(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        if a == b:
            return False
        base = max(abs(a), abs(b))
        return base == 0 or abs(a - b) / base >= _RELEVANT_REL
    return a != b


def _input_changes(keys, loc, prod, prov):
    out = []
    for k in keys:
        cands = [x for x in set(loc) | set(prod) if x.startswith(k[:-1])] if k.endswith(".*") else [k]
        for c in sorted(cands):
            a, b = loc.get(c, _MISSING), prod.get(c, _MISSING)
            if a is _MISSING and b is _MISSING:
                continue
            if a is _MISSING or b is _MISSING or _relevant(a, b):
                out.append(f"{c} {_human(a) if a is not _MISSING else _MISSING} → "
                           f"{_human(b) if b is not _MISSING else _MISSING} "
                           f"[prod: {prov.get(c, 'ausente en prod') if b is not _MISSING else 'ausente en prod'}]")
    return out


def compare_envs(syms, full):
    print("Comparación local → prod (comportamiento actual de la rama sobre cada juego de inputs)")
    loc_out = fb.compute_outputs(syms, fb.fixtures_dir("local"))
    prod_out = fb.compute_outputs(syms, fb.fixtures_dir("prod"))
    order = [name for name, _ in BLOCKS] + ["otros"]
    for sym in syms:
        loc_in, loc_meta = _engine_inputs(sym, "local")
        prod_in, prod_meta = _engine_inputs(sym, "prod")
        prod_nofh, _ = _engine_inputs(sym, "prod", with_finnhub=False)
        f_loc, f_prod, f_nofh = _flatten(loc_in), _flatten(prod_in), _flatten(prod_nofh)
        base_src = "yfinance fallback" if prod_meta["yahoo"].get("fallback_yfinance_used") else "yahoo v10"
        prov = {k: ("finnhub" if f_nofh.get(k, _MISSING) != v else base_src) for k, v in f_prod.items()}
        n_fh = sum(1 for p in prov.values() if p == "finnhub")

        print(f"\n{'═' * 78}\n {sym}\n{'═' * 78}")
        print(f"  local: {_source_summary(loc_meta, 0)}")
        print(f"  prod : {_source_summary(prod_meta, n_fh)}")
        a_loc = json.loads(fb.stable_json(loc_out[sym][0]))
        a_prod = json.loads(fb.stable_json(prod_out[sym][0]))
        groups = diff_analysis(a_loc, a_prod)
        for name in order:
            items = [(p, a, b) for p, a, b in groups.get(name, [])
                     if _relevant(a, b) and (full or not _DERIVED_TEXT.search(p))]
            if not items:
                continue
            print(f"\n  [{name}] {len(items)} diferencia(s) relevante(s)")
            for path, a, b in (items if full else items[:25]):
                print(f"    {path}: {_fmt(a, full)} → {_fmt(b, full)}")
                keys = []
                for rx, ks in CAUSE_RULES:
                    if re.search(rx, path, re.IGNORECASE):
                        keys += [k for k in ks if k not in keys]
                causes = _input_changes(keys, f_loc, f_prod, prov) if keys else []
                if causes:
                    print("        ← causa: " + "; ".join(causes[: (None if full else 4)]))
                elif name in ("alertas", "otros"):
                    print("        ← derivado de los cambios de inputs listados en los otros bloques")
                else:
                    print("        ← sin input crudo distinto asociado (efecto de umbral o derivado)")
            if not full and len(items) > 25:
                print(f"    ... ({len(items) - 25} más; usa --full)")
        lines = diff_text(fb.pdf_text(loc_out[sym][1]), fb.pdf_text(prod_out[sym][1]), full, limit=30)
        if lines:
            print(f"\n  [pdf] texto del informe (local → prod)")
            for line in lines:
                if not line.startswith(("---", "+++")):
                    print(f"    {line}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tickers", nargs="*")
    ap.add_argument("--full", action="store_true", help="no recortar listados")
    ap.add_argument("--regenerate", action="store_true", help="reescribir los golden (explícito)")
    ap.add_argument("--yes", action="store_true", help="confirmar --regenerate sin preguntar")
    ap.add_argument("--env", default=fb.DEFAULT_ENV, choices=fb.ENVS + (fb.PANEL_ENV,), help="juego de fixtures/golden")
    ap.add_argument("--local-vs-prod", action="store_true",
                    help="comparar los juegos local y prod con la causa en inputs crudos")
    args = ap.parse_args(argv)
    logging.disable(logging.CRITICAL)

    syms = [t.upper() for t in args.tickers] or fb.env_tickers(args.env)
    if args.local_vs_prod:
        return compare_envs(syms, args.full)
    gdir = fb.golden_dir(args.env)
    outputs = fb.compute_outputs(syms, fb.fixtures_dir(args.env))
    print(f"entorno: {args.env}")
    any_diff = False
    current = {}
    for sym in syms:
        analysis, pdf = outputs[sym]
        text = fb.pdf_text(pdf)
        current[sym] = (analysis, text)
        gj, gt = load_golden(sym, gdir)
        any_diff |= report(sym, gj, gt, analysis, text, args.full)

    if args.regenerate:
        if not args.yes:
            ans = input(f"\n¿Reescribir los golden [{args.env}] de {', '.join(syms)} con el comportamiento actual? "
                        "Escribe SI para confirmar: ")
            if ans.strip() != "SI":
                print("Cancelado: no se escribió nada.")
                return 2
        for sym in syms:
            jpath, tpath = write_golden(sym, *current[sym], gdir)
            print(f"golden escrito: {os.path.relpath(jpath)} , {os.path.relpath(tpath)}")
        return 0

    print("\nResultado:", "HAY diferencias" if any_diff else "sin diferencias")
    return 1 if any_diff else 0


if __name__ == "__main__":
    sys.exit(main())
