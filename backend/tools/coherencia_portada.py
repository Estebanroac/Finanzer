"""
Coherencia web ↔ PDF de las cifras de portada (V2 con fuentes reales; F9 · R3, «una sola verdad por cifra»).

Paso 2 de 2. El paso 1 (frontend/scripts/coherencia-portada.mjs) deja en <carpeta> lo que enseñó la web (web.json:
el DOM de /v2/{T}), el análisis que pidió la página ({T}.analysis.json) y el PDF ({T}.pdf). Aquí:
  1. La cabecera de la web (precio, variación del día, conclusión, calidad, precio y confianza) tiene que estar en la
     portada del PDF (página 1, texto con pypdf como los golden), tal cual: cada cifra con su mismo valor.
  2. Las cifras clave: la web («La empresa») pinta `display.cover.kpis` y la portada del PDF `display.summary.cards`.
     Se emparejan por etiqueta; si no casan, por la etiqueta sin «reportado» (misma métrica con otro nombre: se
     anota). Dos valores distintos son un fallo (❌). El mismo valor con otra precisión («39.33x» y «39.3x») es un
     aviso (≈), no un fallo. Las que solo están en un lado se listan.
  3. Cada cifra de las tarjetas del PDF aparece en el texto de su portada (que el PDF pinta lo que dice el análisis).
Sale con 1 si hay algún fallo.

    ../../finanzer_next/.venv313/bin/python tools/coherencia_portada.py <carpeta> [--out informe.md]
"""
import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

from pypdf import PdfReader

STATE_LABELS = {"no_aplica": "No aplica", "no_significativo": "n. s.", "sin_dato": "Sin dato"}


def norm(s: Optional[str]) -> str:
    """Para comparar cifras: el mismo signo menos, sin espacios (el PDF parte y junta las líneas a su manera)."""
    s = (s or "").replace("−", "-").replace("–", "-").replace(" ", " ").replace(" ", " ")
    return re.sub(r"\s+", "", s).lower()


def label_key(s: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def loose_key(s: Optional[str]) -> str:
    """La etiqueta sin «reportado»: «P/E reportado (TTM)» y «P/E (TTM)» son la misma métrica."""
    return re.sub(r"\s+", " ", label_key(s).replace("reportado", "")).strip()


NUM = re.compile(r"-?\d+(?:[.,]\d+)?")


def same_value(a: str, b: str) -> str:
    """«=» iguales, «≈» la misma cifra con otra precisión, «≠» distintas. Tolera el doble redondeo: 20.548 sale
    20.55 en un lado y 20.5 en el otro (las dos medias unidades, la de cada precisión)."""
    if norm(a) == norm(b):
        return "="
    na, nb = NUM.search(norm(a)), NUM.search(norm(b))
    if not na or not nb or NUM.sub("", norm(a)) != NUM.sub("", norm(b)):
        return "≠"
    da, db = (len(x.group().replace(",", ".").partition(".")[2]) for x in (na, nb))
    va, vb = (float(x.group().replace(",", ".")) for x in (na, nb))
    tol = 0.5 * 10 ** -da + 0.5 * 10 ** -db + 1e-9
    return "≈" if abs(va - vb) <= tol else "≠"


def cover_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    return (reader.pages[0].extract_text() or "") if reader.pages else ""


def card_value(c: Dict[str, Any]) -> str:
    """El valor de una tarjeta de cifras clave tal como lo pinta la portada del PDF (pdf_v2/cover.key_figures)."""
    if c.get("state", "con_dato") != "con_dato":
        return STATE_LABELS.get(c.get("state"), "Sin dato")
    return f"{c.get('value') or ''}{c.get('unit') or ''}"


def check(sym: str, entry: Dict[str, Any], folder: str) -> Tuple[List[Tuple[str, str, str, str]], List[str]]:
    """Filas (qué, web, PDF, «=» / «≈» / «≠») y notas de un ticker."""
    rows: List[Tuple[str, str, str, str]] = []
    notes: List[str] = []
    pdf_path = os.path.join(folder, f"{sym}.pdf")
    if entry.get("error") or not os.path.exists(pdf_path):
        notes.append(f"sin comparar: {entry.get('error') or 'sin PDF (' + str(entry.get('pdf_status')) + ')'}")
        return rows, notes
    web = entry["web"]
    page1 = norm(cover_text(pdf_path))
    with open(os.path.join(folder, f"{sym}.analysis.json"), encoding="utf-8") as fh:
        a = json.load(fh)

    # 1. Cabecera: cada pieza de la web, en la portada del PDF
    for key, name in (("price", "Precio"), ("day_change", "Variación del día"), ("verdict", "Conclusión"),
                      ("quality", "Calidad del negocio"), ("price_score", "Atractivo del precio"),
                      ("confidence", "Confianza del veredicto")):
        v = web.get(key)
        if v is None:
            notes.append(f"{name}: la web no lo enseña")
            continue
        rows.append((name, v, "en la portada" if norm(v) in page1 else "NO está en la portada", "=" if norm(v) in page1 else "≠"))

    # 2. Cifras clave: la web (cover.kpis) frente a la portada del PDF (summary.cards), por etiqueta
    cards = {label_key(c["label"]): c for c in a["display"]["summary"]["cards"][:6]}
    web_kpis = {label_key(k["label"]): k for k in web.get("kpis", [])}
    loose_cards = {loose_key(c["label"]): lk for lk, c in cards.items()}
    paired = set()
    for lk, k in web_kpis.items():
        ck = lk if lk in cards else loose_cards.get(loose_key(k["label"]))
        if ck is None or ck in paired:
            continue
        paired.add(ck)
        c, pv = cards[ck], card_value(cards[ck])
        what = f"Cifra clave · {k['label']}" + ("" if ck == lk else f" (en el PDF, «{c['label']}»)")
        rows.append((what, k["value"], pv, same_value(k["value"], pv)))
    only_web = [web_kpis[x]["label"] for x in web_kpis if x not in cards and loose_cards.get(loose_key(web_kpis[x]["label"])) not in paired]
    only_pdf = [cards[x]["label"] for x in cards if x not in paired]
    if only_web:
        notes.append("solo en la web (La empresa): " + ", ".join(only_web))
    if only_pdf:
        notes.append("solo en la portada del PDF: " + ", ".join(only_pdf))

    # 3. Lo que dicen las tarjetas del PDF está en el texto de su portada
    for c in cards.values():
        pv = card_value(c)
        if norm(pv) not in page1:
            rows.append((f"PDF · {c['label']}", "—", f"{pv} no está en el texto de la portada", "≠"))
    return rows, notes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder")
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)
    with open(os.path.join(args.folder, "web.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    lines = ["# Coherencia web ↔ PDF de la portada", "",
             "Generado por `backend/tools/coherencia_portada.py` (paso 1: `frontend/scripts/coherencia-portada.mjs`).", ""]
    mark = {"=": "✅", "≈": "≈", "≠": "❌"}
    bad = warn = 0
    for sym, entry in data.items():
        rows, notes = check(sym, entry, args.folder)
        fails = sum(r[3] == "≠" for r in rows)
        approx = sum(r[3] == "≈" for r in rows)
        bad, warn = bad + fails, warn + approx
        head = "—" if not rows else ("❌ " + str(fails) if fails else "✅") + (f" · ≈ {approx}" if approx else "")
        lines += [f"## {sym} — {head}", "", "| Qué | Web | PDF | |", "|---|---|---|:-:|"]
        lines += [f"| {q} | {w} | {p} | {mark[st]} |" for q, w, p, st in rows]
        lines += [""] + [f"- {n}" for n in notes] + [""]
    lines.append(f"**Fallos (dos valores distintos): {bad}** · avisos (misma cifra, otra precisión): {warn}")
    text = "\n".join(lines) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(text if not args.out else f"{args.out}: {bad} fallos, {warn} avisos de precisión")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
