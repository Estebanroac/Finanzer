"""
F10 · margen operativo con una sola verdad: efecto en vivo, antes (be9a0ea3) y después, sobre las mismas empresas.

    python tools/f10_margen_op_medida.py CACHE_ANTES CACHE_DESPUES [--g46 SIMBOLOS] [--out FICHERO.md]

Cachés de `tools/universe_scan.py` (<SIMBOLO>.analysis.json.gz). Dice:
  · los cambios de nivel de calidad y de precio (verdict), y la puntuación de Rentabilidad y del margen operativo;
  · qué queda de las de la puerta (`--g46`): el margen que puntúa frente al de la fila trimestral de Yahoo (> 3 pp), con
    los cargos operativos fuera (causa 1, resuelta por la regla 2) o sin cargos que lo expliquen (causa 2, pendiente de
    las reglas del constructor de EDGAR).
"""
import argparse
import glob
import gzip
import json
import os
import sys

TOL = 0.03


def _load(cache):
    out = {}
    for f in glob.glob(os.path.join(cache, "*.analysis.json.gz")):
        with gzip.open(f) as fh:
            a = json.load(fh).get("analysis") or {}
        if a.get("symbol"):
            out[a["symbol"]] = a
    return out


def _om_row(a):
    for x in ((a.get("score") or {}).get("breakdown") or {}).get("Rentabilidad", {}).get("adjustments") or []:
        if str(x.get("metric") or "").startswith("Margen operativo"):
            return x
    return None


def _rent(a):
    return (((a.get("score") or {}).get("breakdown") or {}).get("Rentabilidad") or {}).get("score")


def _pct(v):
    return "—" if v is None else f"{v * 100:.1f} %"


def _pieces(op):
    src = str(op.get("pieces_source") or "")
    return ("—" if not src else "Yahoo (respaldo declarado)" if src.startswith("respaldo") else
            "ejercicio" if src.startswith("último ejercicio") else "EDGAR" if "EDGAR" in src else "Yahoo (el corte)")


def _yahoo_margin(a):
    """Margen de la fila trimestral de Yahoo (antes: el de las piezas; después: el respaldo declarado)."""
    en = a.get("earnings_normalization") or {}
    op = en.get("operating") or {}
    if op.get("yahoo_quarterly") is not None and op.get("revenue"):
        return op["yahoo_quarterly"] / op["revenue"]
    p = en.get("after_tax") or en.get("coherence") or {}
    if p.get("operating_income") is not None and p.get("revenue"):
        return p["operating_income"] / p["revenue"]
    return None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("antes")
    ap.add_argument("despues")
    ap.add_argument("--g46", default="")
    ap.add_argument("--out")
    o = ap.parse_args(argv)
    A, D = _load(o.antes), _load(o.despues)
    both = sorted(set(A) & set(D))
    L = [f"# Margen operativo con una sola verdad: antes y después ({len(both)} empresas)", ""]
    ql, pl, rows = [], [], []
    for s in both:
        a, d = A[s], D[s]
        va, vd = a.get("verdict") or {}, d.get("verdict") or {}
        if va.get("quality_level") != vd.get("quality_level"):
            ql.append(s)
        if va.get("price_level") != vd.get("price_level"):
            pl.append(s)
        ra, rd = _om_row(a), _om_row(d)
        qa, qd = (a.get("quality") or {}).get("score"), (d.get("quality") or {}).get("score")
        pa, pd = (a.get("price_attractiveness") or {}).get("score"), (d.get("price_attractiveness") or {}).get("score")
        en_a, en_d = a.get("earnings_normalization") or {}, d.get("earnings_normalization") or {}
        if (va.get("quality_level"), va.get("price_level"), qa, pa, _rent(a), (ra or {}).get("adjustment")) != \
                (vd.get("quality_level"), vd.get("price_level"), qd, pd, _rent(d), (rd or {}).get("adjustment")):
            rows.append((s, va, vd, qa, qd, pa, pd, _rent(a), _rent(d), ra, rd,
                         en_a.get("normalized_net_income"), en_d.get("normalized_net_income")))
    L += [f"- Cambia el nivel de calidad en **{len(ql)}**: {', '.join(ql) or '—'}.",
          f"- Cambia el nivel de precio en **{len(pl)}**: {', '.join(pl) or '—'}.",
          f"- Cambia alguna puntuación (calidad, precio, Rentabilidad o el margen operativo) en {len(rows)}.", "",
          "| Empresa | Calidad | Precio | Rentabilidad | Margen operativo que puntúa (antes → después) | "
          "Beneficio normalizado (B$) |", "|---|---|---|---|---|---|"]

    def _r(x):
        return "—" if not x else f"{x.get('metric')} {x.get('value')} ({x.get('adjustment'):+})" \
            if isinstance(x.get("adjustment"), int) else f"{x.get('metric')} {x.get('value')}"

    def _b(v):
        return "—" if v is None else f"{v / 1e9:.2f}"
    for s, va, vd, qa, qd, pa, pd, rea, red, ra, rd, na, nd in rows:
        L.append(f"| {s} | {va.get('quality_level')} {qa} → {vd.get('quality_level')} {qd} | "
                 f"{va.get('price_level')} {pa} → {vd.get('price_level')} {pd} | {rea} → {red} | "
                 f"{_r(ra)} → {_r(rd)} | {_b(na)} → {_b(nd)} |")
    g46 = [s for s in (o.g46.split(",") if o.g46 else []) if s in D]
    if g46:
        L += ["", f"## Las {len(g46)} de la puerta (`margen_operativo_unico`)", "",
              "Después, el margen que se enseña es el de las piezas por construcción (una sola cifra). Lo que queda es "
              f"la diferencia entre el que puntúa y la fila trimestral de Yahoo (> {TOL * 100:.0f} pp).", "",
              "| Empresa | Enseñado (EDGAR) | Puntúa | Yahoo trimestral | Diferencia | Cargos operativos fuera | Clase | "
              "Piezas de la normalización |", "|---|---:|---:|---:|---:|---:|---|---|"]
        n = {"resuelta": 0, "fuentes": 0, "no aplica": 0}
        for s in g46:
            d = D[s]
            km = d.get("key_metrics") or {}
            op = (d.get("earnings_normalization") or {}).get("operating") or {}
            shown = km.get("operating_margin")
            scored = km.get("operating_margin_normalized") if km.get("operating_margin_normalized") is not None \
                else shown
            y = _yahoo_margin(d)
            if shown is None or y is None:
                cls = "no aplica"
            elif abs(scored - y) <= TOL:
                cls = "resuelta"
            else:
                cls = "fuentes"
            n[cls] += 1
            L.append(f"| {s} | {_pct(shown)} | {_pct(scored)} | {_pct(y)} | "
                     + ("—" if shown is None or y is None else f"{abs(scored - y) * 100:.1f} pp")
                     + f" | {(-(op.get('gross') or 0)) / 1e9:+.2f} B$ | "
                     + {"resuelta": "resuelta (cargos fuera)", "fuentes": "causa 2: las fuentes no cuadran",
                        "no aplica": "no aplica / sin piezas"}[cls] + " | "
                     + _pieces(op) + " |")
        L += ["", f"Resueltas {n['resuelta']}; quedan por las fuentes {n['fuentes']}; sin piezas o no aplica "
                  f"{n['no aplica']}."]
    txt = "\n".join(L) + "\n"
    if o.out:
        with open(o.out, "w", encoding="utf-8") as fh:
            fh.write(txt)
    sys.stdout.write(txt)


if __name__ == "__main__":
    main()
