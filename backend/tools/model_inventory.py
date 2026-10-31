"""
Modelo general: inventario de las variables que puntúan o cambian una lectura, el veredicto o la confianza, de las reglas
especiales (por arquetipo, subtipo, sector e industria) y de los tipos de empresa. Lo genera desde el código y la config,
no a mano: docs/modelo/INVENTARIO.md (+ inventario.json).

    cd finanzer_next-mg/backend
    ../../finanzer_next/.venv313/bin/python tools/model_inventory.py                    # muestra: los golden (replay)
    ../../finanzer_next/.venv313/bin/python tools/model_inventory.py --scan ../docs/modelo/ESCANEO_<fecha>.json

Tres fuentes, cada una con lo suyo:
1. El código (AST de lib/financial_ratios.py y del resto de lib/ y main.py): cada componente que registra la cobertura
   (`cov.comp` / `not_sig` / `derived_comp`), su categoría, su banda en config, la clave «no aplica» que lo apaga y la
   línea; las ramas por arquetipo o subtipo; cada lectura de la config (`cfg(...)`) por módulo.
2. La config (TOML, con sus comentarios): umbrales, bandas, listas «no aplica», ajustes por sector, listas de industrias,
   y si el umbral está marcado PROVISIONAL o calibrado.
3. Una muestra medida: el motor corrido con la cobertura instrumentada (qué componentes se registraron en cada empresa y
   cómo: con dato, sin dato, no aplica, no significativo; y su ajuste). Por defecto, los fixtures del panel y de local
   (replay, sin red); con --scan, las ~500 empresas de tools/universe_scan.py. De ahí sale a qué arquetipos aplica cada
   variable en la práctica y qué variables votan lo mismo (correlación de sus ajustes).

Lo único escrito a mano es `META` (fórmula y referencia de cada componente, para leer la tabla) y `TARGET_TYPES` (la
propuesta de tipos objetivo); un test (tests/test_model_inventory.py) falla si el código registra un componente que META
no conoce.
"""
import argparse
import ast
import contextlib
import json
import math
import os
import re
import statistics
import subprocess
import sys
import threading
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
REPO = os.path.dirname(BACKEND)
LIB = os.path.join(BACKEND, "lib")
CONFIG = os.path.join(BACKEND, "config")
DOCS = os.path.join(REPO, "docs", "modelo")
for _p in (LIB, BACKEND):
    if _p not in sys.path:
        sys.path.insert(0, _p)

ARCHETYPES = ["MATURE", "GROWTH_PROFITABLE", "CYCLICAL", "GROWTH_PRE_PROFIT", "FINANCIAL", "REIT", "UTILITY"]
ARCH_SHORT = {"MATURE": "MAD", "GROWTH_PROFITABLE": "CRE", "CYCLICAL": "CIC", "GROWTH_PRE_PROFIT": "PRE",
              "FINANCIAL": "FIN", "REIT": "REIT", "UTILITY": "UTI"}
SUBTYPE_LITERALS = {"banco", "aseguradora", "conglomerado", "financiera"}
SCORE_FILE = os.path.join(LIB, "financial_ratios.py")

# Fórmula (clave de assets/metric_definitions.json, la definición que ve el lector, o el texto) y referencia contra la
# que se lee: «absoluta» (bandas fijas en thresholds.toml), «sector» (sectors.toml), «industria» (Damodaran),
# «propia» (su historia), «modelo» (Altman, Piotroski, DCF).
META: Dict[str, Tuple[str, ...]] = {
    "Altman Z": ("altman", "modelo (zona del Z por SIC)"),
    "Runway": ("runway", "absoluta"),
    "Current ratio": ("current_ratio", "absoluta"),
    "Deuda neta/EBITDA": ("net_debt_to_ebitda", "absoluta (bandas de REIT o de utility)",
                          "thresholds.score.solidez.reit_nde_points", "thresholds.score.solidez.utility_nde_points"),
    "D/E": ("de", "sector (× umbral D/E del sector)"),
    "Cobertura de intereses": ("interest_coverage", "absoluta (bandas propias de utility)"),
    "Salud bancaria": ("financial_health", "absoluta (sectors.financials.benchmarks)",
                       "thresholds.score.solidez_financial.health_offset",
                       "thresholds.score.solidez_financial.health_multiplier"),
    "D/E bancario": ("de", "absoluta (sectors.financials.benchmarks)"),
    "P/B": ("pb", "absoluta (sectors.financials.benchmarks)"),
    "ROE": ("roe", "sector (roe_high / roe_low)"),
    "ROA": ("roa", "sector (roa_high / roa_low)"),
    "Margen operativo": ("operating_margin", "industria (pp frente a Damodaran; si no, absoluta). PRE: absoluta propia"),
    "Margen neto": ("net_margin", "industria (pp frente a Damodaran; si no, absoluta)"),
    "ROIC−WACC": ("roic_wacc_spread", "absoluta (diferencial en pp)"),
    "FFO / activos": ("FFO / activos totales", "absoluta (quintiles de 24 REIT, fase 7)"),
    "Margen FFO": ("FFO / ingresos", "absoluta (PROVISIONAL)"),
    "Margen bruto": ("gross_margin", "absoluta (PROVISIONAL)"),
    "Mejora del margen operativo": ("margen operativo FY − FY anterior (pp)", "propia (interanual)"),
    "Margen FCF − SBC": ("fcf_minus_sbc", "absoluta"),
    "P/B frente al ROE regulado": ("pb_roe", "propia (P/B justificado con el ROE autorizado por el regulador)"),
    "P/B frente a ROE": ("pb_roe", "propia (P/B justificado (ROE − g)/(Ke − g))"),
    "P/TBV frente a ROTE": ("ptbv", "propia (P/TBV justificado)"),
    "Bloque P/B y P/TBV": ("pb_block", "derivado (media de sus miembros)",
                           "thresholds.score.valoracion.multiples_block_max_by_members"),
    "P/FFO": ("p_ffo", "absoluta (contrastada en la fase 7)"),
    "Rentabilidad por dividendo": ("dividend_yield", "absoluta (bandas de utility)"),
    "EV/Ventas": ("ev_sales", "absoluta (PROVISIONAL)"),
    "Regla de 40": ("rule_of_40", "absoluta"),
    "P/E": ("pe", "industria o sector (× su P/E)"),
    "P/FCF": ("pfcf", "absoluta"),
    "EV/EBITDA": ("ev_ebitda", "industria o sector (× su EV/EBITDA)"),
    "PEG": ("peg", "absoluta"),
    "Bloque de múltiplos": ("multiples_block", "derivado (media de P/E, Forward P/E, P/FCF, EV/EBITDA, PEG)",
                            "thresholds.score.valoracion.multiples_block_max_by_members"),
    "DCF": ("dcf_upside", "modelo (valor frente al precio, con su fiabilidad)"),
    "DCF inverso": ("reverse_dcf", "tasas base (crecimiento implícito frente a comparables); el flujo lo dice el "
                                   "nombre: FFO, FCF, FCF − SBC o el de mantenimiento"),
    "Estabilidad del ROE": ("desviación típica del ROE anual", "absoluta"),
    "Eficiencia (aprox.)": ("gastos no financieros / ingresos", "absoluta"),
    "Crecimiento del valor en libros": ("CAGR 3 años del valor en libros tangible", "absoluta"),
    "Payout sobre FFO": ("dividendos / FFO", "absoluta"),
    "Piotroski F": ("piotroski", "modelo (9 criterios)"),
    "Flujo operativo": ("flujo de caja operativo > 0", "signo"),
    "FCF": ("free_cash_flow", "signo"),
    "FCF − SBC": ("fcf_minus_sbc", "signo"),
    "FCF / beneficio neto": ("FCF / beneficio neto", "absoluta"),
    "Retorno total": ("total_return", "absoluta (frente al Ke de un REIT)"),
    "Crecimiento de ingresos": ("revenue_growth", "absoluta (MATURE con dividendo ≥ 4 %: retorno total)"),
    "Crecimiento del BPA": ("earnings_growth", "absoluta"),
    "Crecimiento del FCF": ("CAGR 3 años del FCF (por acción en REIT; FCF − SBC en PRE)", "absoluta"),
}

# Propuesta de tipos objetivo (lista cerrada del usuario, 28-oct-2026): a qué tipo iría cada tipo actual. Es juicio.
TARGET = ["empresa general", "banco", "aseguradora", "REIT", "utility", "sin beneficios aún"]
TARGET_TYPES: Dict[str, Tuple[str, str]] = {
    "MATURE": ("empresa general", "es el caso por defecto; sus herramientas son las generales"),
    "GROWTH_PROFITABLE": ("empresa general", "no tiene herramienta propia (`not_applicable` vacío, «provisional» desde "
                                             "la fase 3): solo cambia la etiqueta"),
    "CYCLICAL": ("empresa general", "lo que cambia es el MÉTODO (ciclo medio, normalizados), no la contabilidad: "
                                    "una opción de normalización de cualquier empresa"),
    "GROWTH_PRE_PROFIT": ("sin beneficios aún", "se queda: sin beneficio, los múltiplos de beneficio y el Altman no "
                                                 "tienen sentido"),
    "FINANCIAL · banco": ("banco", "se queda (balance = producto)"),
    "FINANCIAL · aseguradora": ("aseguradora", "se queda; hoy comparte TODAS las herramientas del banco"),
    "FINANCIAL · conglomerado": ("aseguradora", "subtipo de aseguradora (BRK-B): o aseguradora, o empresa general "
                                                "con su negocio asegurador como segmento"),
    "FINANCIAL · financiera": ("banco", "prestamistas de Credit Services y financieras ambiguas: contabilidad de banco"),
    "REIT": ("REIT", "se queda (FFO)"),
    "UTILITY": ("utility", "se queda (base regulada, FCF negativo por diseño)"),
}


# ═══════════════════════ Muestra medida: la cobertura instrumentada ═══════════════════════

_TL = threading.local()
_PATCHED = [False]


def _install():
    if _PATCHED[0]:
        return
    import financial_ratios as fr
    cls = fr.CategoryCoverage
    o_comp, o_sig, o_der = cls.comp, cls.not_sig, cls.derived_comp

    def _push(fn, name, state, adj):
        lst = getattr(_TL, "regs", None)
        if lst is not None:
            lst.append([fn, str(name), state, adj])

    def comp(self, name, points, adj, reason=None, na=None, rescale=True):
        # El estado se lee por su efecto: F10 · B1 hace que `comp` marque no significativo (vía not_sig) un componente
        # sin dato con el denominador ≤ 0.
        fn = sys._getframe(1).f_code.co_name
        _TL.in_comp = True
        try:
            out = o_comp(self, name, points, adj, reason, na, rescale)
        finally:
            _TL.in_comp = False
        state = ("no_aplica" if name in self.not_applicable else
                 "no_significativo" if name in self.not_significant else
                 "con_dato" if adj is not None else "sin_dato")
        _push(fn, name, state, adj)
        return out

    def not_sig(self, name, reason):
        if not getattr(_TL, "in_comp", False):
            _push(sys._getframe(1).f_code.co_name, name, "no_significativo", None)
        return o_sig(self, name, reason)

    def derived_comp(self, name, points, adj):
        _push(sys._getframe(1).f_code.co_name, name, "derivado" if adj is not None else "sin_dato", adj)
        return o_der(self, name, points, adj)

    cls.comp, cls.not_sig, cls.derived_comp = comp, not_sig, derived_comp
    _PATCHED[0] = True


@contextlib.contextmanager
def record_components():
    """[[función, componente, estado, ajuste]] registrados por el motor en este hilo mientras dure el bloque."""
    _install()
    _TL.regs = []
    try:
        yield _TL.regs
    finally:
        _TL.regs = None


def fixture_sample() -> Dict[str, Dict[str, Any]]:
    """El motor sobre los fixtures del panel y de local (replay, sin red), con la cobertura instrumentada."""
    tests = os.path.join(BACKEND, "tests")
    if tests not in sys.path:
        sys.path.insert(0, tests)
    import logging
    logging.disable(logging.CRITICAL)
    import fixture_backend as fb
    from fastapi import HTTPException
    out: Dict[str, Dict[str, Any]] = {}
    for env in ("panel", "local"):
        with fb.replay(fb.fixtures_dir(env)) as store:
            for sym in fb.env_tickers(env):
                key = sym if env == "panel" else f"{sym}@local"
                if env == "local" and sym in out:
                    continue
                with record_components() as regs:
                    try:
                        a = fb.run_analysis(sym, store)
                    except HTTPException:
                        continue
                c = a.get("classification") or {}
                out[key] = {"archetype": c.get("archetype"), "subtype": c.get("subtype"), "components": list(regs),
                            "breakdown": {k: [{"metric": x.get("metric"), "adjustment": x.get("adjustment")}
                                              for x in v.get("adjustments") or []]
                                          for k, v in ((a.get("score") or {}).get("breakdown") or {}).items()}}
    logging.disable(logging.NOTSET)
    return out


# ═══════════════════════ El código ═══════════════════════

def _parse(path: str) -> ast.Module:
    with open(path, encoding="utf-8") as fh:
        return ast.parse(fh.read(), filename=path)


def _rel(path: str) -> str:
    return os.path.relpath(path, REPO)


def _const_str(n: ast.AST) -> Optional[str]:
    return n.value if isinstance(n, ast.Constant) and isinstance(n.value, str) else None


def _parents(tree: ast.AST) -> Dict[ast.AST, ast.AST]:
    par = {}
    for p in ast.walk(tree):
        for c in ast.iter_child_nodes(p):
            par[c] = p
    return par


def _func_of(node, par) -> Optional[ast.FunctionDef]:
    while node in par:
        node = par[node]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node
    return None


def _guards(node, par) -> List[str]:
    """Las condiciones de los `if` que encierran el nodo (con «no» si está en la rama else)."""
    out = []
    child = node
    while child in par:
        p = par[child]
        if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)):
            break
        if isinstance(p, ast.If):
            t = ast.unparse(p.test)
            out.append(t if child in p.body else f"no ({t})")
        if isinstance(p, ast.IfExp):
            t = ast.unparse(p.test)
            out.append(t if child is p.body else f"no ({t})")
        child = p
    return list(reversed(out))


def _aliases(tree: ast.Module) -> Dict[str, str]:
    """Nombre del módulo -> ruta de config: `_SC = cfg("thresholds.score")`."""
    out = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            p = _cfg_path(n.value, out)
            if p:
                out[n.targets[0].id] = p
    return out


def _cfg_path(v: ast.AST, aliases: Dict[str, str]) -> Optional[str]:
    if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "cfg" and v.args:
        return _const_str(v.args[0])
    if isinstance(v, ast.Subscript) and isinstance(v.value, ast.Name) and v.value.id in aliases:
        k = _const_str(v.slice)
        return f"{aliases[v.value.id]}.{k}" if k else None
    return None


def _func_aliases(fn: ast.FunctionDef, mod_aliases: Dict[str, str]) -> Dict[str, str]:
    al = dict(mod_aliases)
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            p = _cfg_path(n.value, al)
            if p:
                al[n.targets[0].id] = p
    return al


def _keys_in(expr: ast.AST, al: Dict[str, str]) -> List[str]:
    out = []
    for n in ast.walk(expr):
        p = _cfg_path(n, al) if isinstance(n, (ast.Subscript, ast.Call)) else None
        if p:
            out.append(p)
    return out


def _na_key(expr: Optional[ast.AST], fn: ast.FunctionDef) -> Optional[str]:
    """La clave de sectors.archetypes.not_applicable que apaga el componente."""
    if expr is None:
        return None
    if isinstance(expr, ast.Subscript) and isinstance(expr.value, ast.Name):      # _na["pe"]
        return _const_str(expr.slice)
    if isinstance(expr, ast.Name):                                                   # _na_opm
        for n in ast.walk(fn):
            if isinstance(n, ast.Assign):
                tg = n.targets[0]
                names = [tg] if isinstance(tg, ast.Name) else list(getattr(tg, "elts", []))
                vals = [n.value] if isinstance(tg, ast.Name) else list(getattr(n.value, "elts", []))
                for t, v in zip(names, vals):
                    if isinstance(t, ast.Name) and t.id == expr.id and isinstance(v, ast.Call) and len(v.args) >= 2:
                        return _const_str(v.args[1])
    if isinstance(expr, ast.Call) and len(expr.args) >= 2:
        return _const_str(expr.args[1]) or "(por clave)"
    if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute):
        return "dcf"
    return ast.unparse(expr)[:40]


def _names_of(expr: ast.AST, fn: ast.FunctionDef, par) -> List[str]:
    s = _const_str(expr)
    if s:
        return [s]
    if isinstance(expr, ast.IfExp):
        return _names_of(expr.body, fn, par) + _names_of(expr.orelse, fn, par)
    if isinstance(expr, ast.BoolOp):
        return [x for v in expr.values for x in _names_of(v, fn, par)][-1:]
    if isinstance(expr, ast.Name):
        # variable de un bucle sobre tuplas literales: (("Crecimiento del BPA", ...), ("Crecimiento del FCF", ...))
        node = expr
        while node in par:
            node = par[node]
            if isinstance(node, ast.For):
                tg = node.target
                idx = next((i for i, e in enumerate(getattr(tg, "elts", [])) if isinstance(e, ast.Name)
                            and e.id == expr.id), None)
                if idx is not None and isinstance(node.iter, (ast.Tuple, ast.List)):
                    return [x for e in node.iter.elts if isinstance(e, ast.Tuple) and len(e.elts) > idx
                            for x in _names_of(e.elts[idx], fn, par)]
                if isinstance(tg, ast.Tuple) and idx is not None:
                    return ["(dinámico: " + ast.unparse(node.iter)[:40] + ")"]
    return ["(" + ast.unparse(expr)[:50] + ")"]


def _loop_envs(node, par) -> List[Dict[str, ast.AST]]:
    """Si el nodo está en un `for a, b, … in ((…), (…))` sobre tuplas literales, una sustitución por vuelta."""
    p = node
    while p in par:
        p = par[p]
        if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)):
            break
        if isinstance(p, ast.For) and isinstance(p.target, ast.Tuple) and isinstance(p.iter, (ast.Tuple, ast.List)):
            names = [e.id if isinstance(e, ast.Name) else None for e in p.target.elts]
            envs = []
            for e in p.iter.elts:
                if isinstance(e, ast.Tuple) and len(e.elts) == len(names):
                    envs.append({nm: v for nm, v in zip(names, e.elts) if nm})
            if envs:
                return envs
    return [{}]


def _subst(e: Optional[ast.AST], env: Dict[str, ast.AST]) -> Optional[ast.AST]:
    if e is None or not env:
        return e
    if isinstance(e, ast.Name) and e.id in env:
        return env[e.id]
    return e


def _category_of(fn: ast.FunctionDef) -> Optional[str]:
    for n in ast.walk(fn):
        if isinstance(n, ast.Dict):
            for k, v in zip(n.keys, n.values):
                if _const_str(k) == "category" and _const_str(v):
                    return _const_str(v)
    return None


def scored_components() -> List[Dict[str, Any]]:
    """Cada `cov.comp / not_sig / derived_comp` del motor con su categoría, banda, clave «no aplica», condiciones y línea.
    Las ramas que pasan sus componentes a `_rentabilidad_branch` como tuplas se leen en la función que los arma."""
    tree = _parse(SCORE_FILE)
    par = _parents(tree)
    mod_al = _aliases(tree)
    out = []
    branch_callers = {}
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
        for n in ast.walk(fn):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "_rentabilidad_branch":
                branch_callers[fn.name] = _const_str(n.args[0]) or ast.unparse(n.args[0])
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
        al = _func_aliases(fn, mod_al)
        cat = _category_of(fn)
        for n in ast.walk(fn):
            if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr in ("comp", "not_sig", "derived_comp") and n.args):
                continue
            if fn.name == "_rentabilidad_branch":
                continue
            kw = {k.arg: k.value for k in n.keywords}
            pts = n.args[1] if len(n.args) > 1 and n.func.attr != "not_sig" else None
            rescale = not (isinstance(kw.get("rescale"), ast.Constant) and kw["rescale"].value is False)
            for env in _loop_envs(n, par):
                sub = lambda e: _subst(e, env)  # noqa: E731
                for nm in {canon(x): None for x in _names_of(sub(n.args[0]), fn, par)}:
                    out.append({"name": nm, "kind": n.func.attr, "category": cat, "function": fn.name,
                                "file": _rel(SCORE_FILE), "line": n.lineno,
                                "points": _keys_in(sub(pts), al) if pts is not None else [],
                                "na_key": _na_key(sub(kw.get("na")) if kw.get("na") is not None else None, fn),
                                "guards": _guards(n, par), "rescale": rescale})
        if fn.name in branch_callers:
            for n in ast.walk(fn):
                tup = None
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "append" \
                        and n.args and isinstance(n.args[0], ast.Tuple):
                    tup = n.args[0]
                if tup is not None and tup.elts and (_const_str(tup.elts[0])):
                    keys = _keys_in(tup.elts[1], al) if len(tup.elts) > 1 else []
                    out.append({"name": _const_str(tup.elts[0]), "kind": "comp", "category": "Rentabilidad",
                                "function": fn.name, "file": _rel(SCORE_FILE), "line": n.lineno, "points": keys,
                                "na_key": None, "guards": [f"archetype == {branch_callers[fn.name]}"], "rescale": True})
                if isinstance(n, ast.For) and isinstance(n.iter, ast.Tuple):
                    for e in n.iter.elts:
                        if isinstance(e, ast.Tuple) and e.elts and _const_str(e.elts[0]):
                            keys = [k for x in e.elts[1:] for k in _keys_in(x, al)]
                            out.append({"name": _const_str(e.elts[0]), "kind": "comp", "category": "Rentabilidad",
                                        "function": fn.name, "file": _rel(SCORE_FILE), "line": e.lineno,
                                        "points": [k for k in keys if k.endswith("_points")], "na_key": None,
                                        "guards": [f"archetype == {branch_callers[fn.name]}"], "rescale": True})
    # Dedupe: un mismo (nombre, función, línea) solo una vez
    seen, res = set(), []
    for c in out:
        k = (c["name"], c["function"], c["line"], c["kind"])
        if k not in seen:
            seen.add(k)
            res.append(c)
    return res


def bonus_adjustments() -> List[Dict[str, Any]]:
    """Ajustes que puntúan en el desglose (un dict con "metric" y "adjustment") en funciones del score: los que no pasan
    por la cobertura (bonos, topes) se ven comparando con los componentes."""
    tree = _parse(SCORE_FILE)
    par = _parents(tree)
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Dict):
            keys = [_const_str(k) for k in n.keys]
            if "metric" in keys and "adjustment" in keys:
                v = n.values[keys.index("metric")]
                fn = _func_of(n, par)
                label = _const_str(v) or (ast.unparse(v)[:60] if not isinstance(v, ast.JoinedStr) else
                                          "".join(x.value if isinstance(x, ast.Constant) else "{…}" for x in v.values))
                out.append({"metric": label, "function": fn.name if fn else None, "line": n.lineno,
                            "file": _rel(SCORE_FILE)})
    return out


def archetype_branches(files: Iterable[str]) -> List[Dict[str, Any]]:
    """Cada comparación con un arquetipo o un subtipo (`archetype == REIT`, `subtype == "banco"`, `in (REIT, UTILITY)`)."""
    names = set(ARCHETYPES)
    out = []
    for path in files:
        tree = _parse(path)
        par = _parents(tree)
        for n in ast.walk(tree):
            if not isinstance(n, ast.Compare):
                continue
            parts = [n.left, *n.comparators]
            hit = set()
            for p in parts:
                for x in ast.walk(p):
                    if isinstance(x, ast.Name) and x.id in names:
                        hit.add(x.id)
                    s = _const_str(x)
                    if s in names:
                        hit.add(s)
                    elif s in SUBTYPE_LITERALS and any(isinstance(y, ast.Name) and "subtype" in y.id or
                                                       (isinstance(y, ast.Attribute) and "subtype" in y.attr) or
                                                       (_const_str(y) == "subtype")
                                                       for q in parts for y in ast.walk(q)):
                        hit.add(f"subtipo:{s}")
            if hit:
                fn = _func_of(n, par)
                out.append({"file": _rel(path), "line": n.lineno, "function": fn.name if fn else "(módulo)",
                            "types": sorted(hit), "condition": ast.unparse(n)[:110]})
    return out


def not_applicable_sites(files: Iterable[str]) -> List[Dict[str, Any]]:
    from settings import cfg
    na_keys = {k for v in cfg("sectors.archetypes.not_applicable").values() for k in v}
    out = []
    for path in files:
        tree = _parse(path)
        par = _parents(tree)
        for n in ast.walk(tree):
            # ctx.na("gross_margin") (alertas) y "pe" in na (display): la lista ya resuelta
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "na" and n.args \
                    and _const_str(n.args[0]) in na_keys:
                fn = _func_of(n, par)
                out.append({"file": _rel(path), "line": n.lineno, "function": fn.name if fn else None,
                            "key": _const_str(n.args[0])})
                continue
            if isinstance(n, ast.Compare) and _const_str(n.left) in na_keys and len(n.ops) == 1 \
                    and isinstance(n.ops[0], (ast.In, ast.NotIn)) and re.search(r"\bna\b|na_keys|_na\b",
                                                                                 ast.unparse(n.comparators[0])):
                fn = _func_of(n, par)
                out.append({"file": _rel(path), "line": n.lineno, "function": fn.name if fn else None,
                            "key": _const_str(n.left)})
                continue
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("not_applicable",
                                                                                          "subtype_not_applicable"):
                fn = _func_of(n, par)
                key = _const_str(n.args[1]) if len(n.args) > 1 else None
                if key is None and len(n.args) > 1 and isinstance(n.args[1], ast.Name):
                    # {k: not_applicable(archetype, k) for k in ("altman", ...)}
                    comp = par.get(n)
                    while comp is not None and not isinstance(comp, ast.DictComp):
                        comp = par.get(comp)
                    if comp is not None and comp.generators and isinstance(comp.generators[0].iter, ast.Tuple):
                        for e in comp.generators[0].iter.elts:
                            if _const_str(e):
                                out.append({"file": _rel(path), "line": n.lineno, "function": fn.name if fn else None,
                                            "key": _const_str(e)})
                        continue
                out.append({"file": _rel(path), "line": n.lineno, "function": fn.name if fn else None,
                            "key": key or "(por variable)"})
        for n in tree.body:     # _RENT_NA_COMMON = (("roe", "ROE"), ...): las lee _rentabilidad_branch
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Tuple) and n.value.elts and all(
                    isinstance(e, ast.Tuple) and e.elts and _const_str(e.elts[0]) in na_keys for e in n.value.elts):
                for e in n.value.elts:
                    out.append({"file": _rel(path), "line": n.lineno, "function": ast.unparse(n.targets[0]),
                                "key": _const_str(e.elts[0])})
    return out


def cfg_reads(files: Iterable[str]) -> List[Dict[str, Any]]:
    """Cada lectura de la config: `cfg("ruta")` y sus alias de módulo (`_SC["solidez"]` ...)."""
    out = []
    for path in files:
        tree = _parse(path)
        par = _parents(tree)
        mod_al = _aliases(tree)
        for n in ast.walk(tree):
            p = None
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "cfg" and n.args:
                p = _const_str(n.args[0]) or (ast.unparse(n.args[0])[:60] if n.args else None)
            if p:
                fn = _func_of(n, par)
                out.append({"file": _rel(path), "line": n.lineno, "function": fn.name if fn else "(módulo)", "key": p})
        for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            al = _func_aliases(fn, mod_al)
            for n in ast.walk(fn):
                if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id in al \
                        and n.value.id not in ("cfg",) and _const_str(n.slice):
                    out.append({"file": _rel(path), "line": n.lineno, "function": fn.name,
                                "key": f"{al[n.value.id]}.{_const_str(n.slice)}"})
    return out


def classification_rules() -> List[Dict[str, Any]]:
    """Las salidas de classify.classify: arquetipo, código de regla, subtipo y línea."""
    path = os.path.join(LIB, "classify.py")
    tree = _parse(path)
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "out" and len(n.args) >= 3:
            arch = n.args[0].id if isinstance(n.args[0], ast.Name) else ast.unparse(n.args[0])
            kw = {k.arg: k.value for k in n.keywords}
            out.append({"line": n.lineno, "archetype": arch, "rule": _const_str(n.args[2]) or ast.unparse(n.args[2]),
                        "subtype": _const_str(kw["subtype"]) if "subtype" in kw else None,
                        "ambiguous": ast.unparse(kw["ambiguous"]) if "ambiguous" in kw else "False"})
    return out


# ═══════════════════════ La config ═══════════════════════

def toml_notes(name: str) -> Dict[str, Dict[str, Any]]:
    """{ruta: {value, comment, block, provisional, calibrated}} con el comentario de la línea y el bloque de encima."""
    import tomllib
    path = os.path.join(CONFIG, f"{name}.toml")
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    notes: Dict[str, Dict[str, Any]] = {}
    section, block, sec_comment = [], [], ""
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            s = line.strip()
            if s.startswith("#"):
                block.append(s.lstrip("# ").strip())
                continue
            m = re.match(r"^\[([^\]]+)\]\s*(#.*)?$", s)
            if m:
                section = [x.strip().strip('"') for x in m.group(1).split(".")]
                sec_comment = (m.group(2) or "").lstrip("# ").strip() + " " + " ".join(block)
                block = []
                continue
            m = re.match(r'^("?[^=\s"]+"?)\s*=\s*(.*)$', s)
            if m:
                key = m.group(1).strip('"')
                cm = re.search(r"\s#\s?(.*)$", m.group(2))
                comment = cm.group(1).strip() if cm else ""
                full = ".".join([name, *section, key])
                txt = " ".join(block) + " " + comment + " " + sec_comment
                notes[full] = {"line": i, "comment": comment, "block": " ".join(block)[-400:],
                               "provisional": "PROVISIONAL" in txt,
                               "calibrated": bool(re.search(r"contrastad|calibrad|cuantil|quintil|p80|mediana", txt, re.I))}
                block = []
            elif not s:
                block = []
    return notes


def cfg_value(path: str) -> Any:
    from settings import cfg
    try:
        v = cfg(path)
    except Exception:  # noqa: BLE001
        return None
    return list(v) if isinstance(v, tuple) else v


def _short(v: Any, n: int = 60) -> str:
    if isinstance(v, (list, tuple)):
        s = "[" + ", ".join(f"{x:g}" if isinstance(x, float) else str(x) for x in v) + "]"
    elif isinstance(v, float):
        s = f"{v:g}"
    else:
        s = str(v)
    return s if len(s) <= n else s[:n - 1] + "…"


def bands_for(points_key: str) -> List[Tuple[str, Any]]:
    """La banda que acompaña a una clave de puntos: `x_points` -> `x_bounds` / `x_mults` en la misma tabla."""
    base = points_key.rsplit(".", 1)
    if len(base) < 2:
        return []
    table, leaf = base
    stem = re.sub(r"_points(_high|_medium)?$", "", leaf)
    out = []
    for suf in ("_bounds", "_mults", "_vs_industry_pp", "_ratio_bounds", "_upside_bounds", "_value_bounds",
                "_value_mults"):
        for cand in {f"{table}.{stem}{suf}", f"{table}.{stem.replace('_value', '')}{suf}"}:
            v = cfg_value(cand)
            if v is not None:
                out.append((cand, v))
    return out


def duplicated_config() -> List[Dict[str, Any]]:
    """Claves con la misma hoja y el mismo valor en tablas distintas de thresholds/sectors/valuation: candidatas a ser
    una sola."""
    from settings import cfg
    flat: Dict[str, Any] = {}

    def walk(o, p):
        if hasattr(o, "keys"):
            for k in o:
                walk(o[k], f"{p}.{k}")
        else:
            flat[p] = o
    for f in ("thresholds", "valuation", "sectors"):
        walk(cfg(f), f)
    by: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for p, v in flat.items():
        leaf = p.rsplit(".", 1)[-1]
        if p.startswith(("sectors.benchmarks.", "sectors.score_thresholds.overrides", "sectors.benchmarks")) \
                or leaf.startswith("w_"):          # pesos de orden de las alertas: coincidir no es duplicar
            continue
        by[(leaf, json.dumps(v, default=str))].append(p)
    return [{"leaf": k[0], "value": json.loads(k[1]), "keys": v} for k, v in by.items() if len(v) > 1]


def same_bands() -> List[Dict[str, Any]]:
    """Juegos de puntos idénticos con nombres distintos: la misma escala repetida por arquetipo."""
    from settings import cfg
    by: Dict[str, List[str]] = defaultdict(list)
    sc = cfg("thresholds.score")
    for t in sc:
        if hasattr(sc[t], "keys"):
            for k, v in sc[t].items():
                if k.endswith("_points") and isinstance(v, tuple):
                    by[json.dumps(list(v))].append(f"{t}.{k}")
    return [{"points": json.loads(k), "keys": v} for k, v in by.items() if len(v) > 1]


# ═══════════════════════ Composición ═══════════════════════

def canon(name: str) -> str:
    """Un componente con el nombre armado en tiempo de ejecución es uno solo: «DCF inverso (FFO)», «DCF inverso (FCF −
    SBC)»… -> «DCF inverso» (el flujo sale de reverse_dcf)."""
    return "DCF inverso" if str(name).startswith("DCF inverso") else str(name)


def applicability(sample: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """{(categoría, componente): {arquetipo: Counter(estado)}} y el número de empresas por arquetipo."""
    fn_cat = {}
    tree = _parse(SCORE_FILE)
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
        fn_cat[fn.name] = _category_of(fn) or ("Rentabilidad" if fn.name == "_rentabilidad_branch" else None)
    table: Dict[Tuple[str, str], Dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    n_arch: Counter = Counter()
    adj: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(dict)
    for sym, r in sample.items():
        arch = r.get("archetype")
        if not arch:
            continue
        n_arch[arch] += 1
        for fn, name, state, a in r.get("components") or []:
            key = (fn_cat.get(fn) or fn, canon(name))
            table[key][arch][state] += 1
            if a is not None and state in ("con_dato", "derivado"):
                adj[key][sym] = a
    return {"table": table, "n_arch": n_arch, "adj": adj}


def _weight(vals: Dict[str, float]) -> Dict[str, Any]:
    """Cuánto pesa en la práctica: empresas con ajuste, |ajuste| medio y share de las que mueve (≠ 0)."""
    xs = list(vals.values())
    if not xs:
        return {"n": 0, "mean_abs": None, "moves": None}
    return {"n": len(xs), "mean_abs": sum(abs(x) for x in xs) / len(xs), "moves": sum(1 for x in xs if x) / len(xs)}


def correlations(adj: Dict[Tuple[str, str], Dict[str, float]], min_n: int = 12, min_r: float = 0.6) -> List[Dict[str, Any]]:
    """Pares de componentes cuyos ajustes se mueven juntos en la muestra (Pearson, |r| ≥ min_r, ≥ min_n empresas)."""
    keys = [k for k, v in adj.items() if len(v) >= min_n and len(set(v.values())) > 1
            and not k[1].startswith("Bloque")]       # el bloque es la media de sus miembros: correlación por definición
    out = []
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            common = sorted(set(adj[a]) & set(adj[b]))
            if len(common) < min_n:
                continue
            xs, ys = [adj[a][s] for s in common], [adj[b][s] for s in common]
            if len(set(xs)) < 2 or len(set(ys)) < 2:
                continue
            r = statistics.correlation(xs, ys)
            if abs(r) >= min_r:
                same = sum(1 for x, y in zip(xs, ys) if (x > 0) == (y > 0) and (x < 0) == (y < 0))
                out.append({"a": a, "b": b, "r": r, "n": len(common), "same_sign": same / len(common)})
    return sorted(out, key=lambda x: -abs(x["r"]))


def build(sample: Dict[str, Dict[str, Any]], sample_label: str) -> Dict[str, Any]:
    from settings import cfg
    files = [os.path.join(LIB, f) for f in sorted(os.listdir(LIB)) if f.endswith(".py") and f not in ("model_invariants.py",)]
    files.append(os.path.join(BACKEND, "main.py"))
    comps = scored_components()
    notes = {}
    for f in ("thresholds", "sectors", "valuation"):
        notes.update(toml_notes(f))
    app = applicability(sample)
    na_cfg = {k: list(v) for k, v in cfg("sectors.archetypes.not_applicable").items()}
    na_sub = {k: list(v) for k, v in cfg("sectors.archetypes.not_applicable_subtype").items()}

    # Un componente = (categoría, nombre). Sitios en el código, bandas, «no aplica» y aplicabilidad medida.
    by_comp: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for c in comps:
        key = (c["category"] or "?", c["name"])
        d = by_comp.setdefault(key, {"category": key[0], "name": key[1], "sites": [], "points": set(), "na_keys": set(),
                                     "guards": set(), "kinds": set()})
        d["sites"].append(f"{c['file']}:{c['line']}")
        d["points"].update(c["points"])
        if c["na_key"]:
            d["na_keys"].add(c["na_key"])
        d["guards"].update(g for g in c["guards"] if re.search(r"archetype|REIT|UTILITY|FINANCIAL|GROWTH|CYCLICAL|"
                                                                 r"MATURE|_reit|_gpp|_cyc|is_reit|is_financial|subtype", g))
        d["kinds"].add(c["kind"])
    for (cat, name), x in app["table"].items():
        if (cat, name) not in by_comp:
            by_comp[(cat, name)] = {"category": cat, "name": name, "sites": [], "points": set(), "na_keys": set(),
                                    "guards": set(), "kinds": {"(solo medido)"}}
    rows = []
    for key, d in by_comp.items():
        measured = app["table"].get(key, {})
        appl = {}
        for arch in ARCHETYPES:
            st = measured.get(arch)
            if st:
                if st.get("con_dato") or st.get("sin_dato") or st.get("derivado"):
                    appl[arch] = "A"
                elif st.get("no_significativo") and not st.get("no_aplica"):
                    appl[arch] = "ns"
                else:
                    appl[arch] = "–"
            elif app["n_arch"].get(arch):
                appl[arch] = "–"          # el arquetipo está en la muestra y el componente no se registró
            else:
                na_hit = any(k in na_cfg.get(arch, []) for k in d["na_keys"])
                appl[arch] = "–?" if na_hit else "?"
        n_app = sum(1 for v in appl.values() if v in ("A", "ns"))
        scope = ("muerta" if n_app == 0 and not any(v == "?" for v in appl.values()) else
                 "universal" if n_app == len(ARCHETYPES) else
                 "casi universal" if n_app >= len(ARCHETYPES) - 2 else "específica")
        meta = META.get(d["name"])
        bands = []
        if meta and len(meta) > 2:
            d["points"].update(meta[2:])
        for pk in sorted(d["points"]):
            bands.append((pk, cfg_value(pk)))
            bands += bands_for(pk)
        prov = any((notes.get(k) or {}).get("provisional") for k, _ in bands)
        calib = any((notes.get(k) or {}).get("calibrated") for k, _ in bands)
        rows.append({**{k: (sorted(v) if isinstance(v, set) else v) for k, v in d.items()},
                     "formula": meta[0] if meta else None, "reference": meta[1] if meta else None,
                     "bands": [(k, v) for k, v in bands], "applies": appl, "scope": scope,
                     "threshold_source": "PROVISIONAL" if prov else ("calibrado" if calib else "fijado a mano / modelo"),
                     "weight": _weight(app["adj"].get(key) or {}),
                     "measured": {a: dict(c) for a, c in measured.items()}})
    cat_order = {"Solidez Financiera": 0, "Rentabilidad": 1, "Valoración": 2, "Calidad de Ganancias": 3, "Crecimiento": 4}
    rows.sort(key=lambda r: (cat_order.get(r["category"], 9), r["scope"] != "universal", r["name"]))

    # Ajustes que puntúan fuera de la cobertura (medidos en el desglose)
    comp_names = {r["name"] for r in rows}
    outside: Counter = Counter()
    for r in sample.values():
        for cat, xs in (r.get("breakdown") or {}).items():
            for x in xs:
                m = str(x.get("metric") or "")
                if (x.get("adjustment") or 0) != 0 and not any(_matches(m, n) for n in comp_names) \
                        and m not in ("Cobertura", "No aplica"):
                    outside[(cat, re.sub(r"\d[\d.,]*", "#", m))] += 1

    branches = archetype_branches(files)
    na_sites = not_applicable_sites(files)
    reads = cfg_reads(files)
    return {"meta": {"commit": git_commit(), "sample": sample_label, "companies": sum(app["n_arch"].values()),
                     "by_archetype": dict(app["n_arch"])},
            "components": rows, "outside_coverage": [{"category": k[0], "metric": k[1], "companies": v}
                                                     for k, v in outside.most_common()],
            "classification_rules": classification_rules(), "branches": branches, "na_sites": na_sites,
            "na_config": na_cfg, "na_subtype": na_sub, "cfg_reads": reads,
            "sector_overrides": {k: dict(v) for k, v in cfg("sectors.score_thresholds.overrides").items()},
            "duplicated_config": duplicated_config(), "same_bands": same_bands(),
            "correlations": correlations(app["adj"]), "notes": notes}


_MOVES = [
    (r"^thresholds\.score\.(solidez|rentabilidad|valoracion|calidad|crecimiento|solidez_financial|category|coverage)",
     0, "puntuación (bandas y puntos)"),
    (r"^thresholds\.score\.(quality|price|total|border_points|category_labels)|^thresholds\.quality_persistence",
     1, "veredicto (bandas de calidad y precio, contracción, persistencia)"),
    (r"^thresholds\.(confidence|dcf_reliability)", 2, "confianza (convergencia, cobertura, fuente, fiabilidad del DCF)"),
    (r"^thresholds\.alerts", 3, "fortalezas y alertas"),
    (r"^thresholds\.(pdf|quality_readings|premortem|roce)|^base_rates|^review|^market\.(signals|context)",
     4, "lecturas del informe que no puntúan"),
    (r"^sectors\.(archetypes|business_model|financials)", 5, "tipo de empresa y excepciones"),
    (r"^sectors\.(benchmarks|score_thresholds)|^industries", 6, "referencias (sector, industria, mercado)"),
    (r"^thresholds\.(normalization|growth)|^valuation|^market\.beta_choice|^betas|^country_risk", 7,
     "métodos (normalización, crecimiento, coste de capital, DCF, modelos)"),
]


def _moves(top: str) -> Tuple[int, str]:
    for pat, order, what in _MOVES:
        if re.search(pat, top):
            return order, what
    return 9, "datos y presentación"


def _matches(metric: str, comp: str) -> bool:
    m, c = metric.lower(), comp.lower()
    if c == "roe" and m.startswith("roic (en lugar del roe"):
        return True
    alias = {"altman z": "altman z-score", "current ratio": "liquidez corriente", "d/e": "deuda/equity",
             "roic−wacc": "roic frente al wacc", "piotroski f": "piotroski f-score",
             "flujo operativo": "flujo de caja operativo", "fcf": "flujo de caja libre", "salud bancaria": "solidez bancaria",
             "p/b": "price/book", "d/e bancario": "d/e bancario", "p/ffo": "p/ffo (reit)",
             "rentabilidad por dividendo": "rentabilidad por dividendo (utility)", "dcf": "dcf directo"}
    c2 = alias.get(c, c)
    return m.startswith(c) or m.startswith(c2) or m.replace(" normalizado", "").startswith(c) \
        or (c == "retorno total" and m.startswith("retorno total"))


def git_commit() -> Optional[str]:
    try:
        return subprocess.check_output(["git", "-C", REPO, "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return None


# ═══════════════════════ Markdown ═══════════════════════

def _cell(s: Any) -> str:
    return str(s).replace("|", "/").replace("\n", " ")


def write_md(inv: Dict[str, Any], path: str, scan: Optional[Dict[str, Any]] = None) -> None:
    M = inv["meta"]
    rows = inv["components"]
    L: List[str] = []
    A = L.append
    A("# Inventario del modelo de Finanzer")
    A("")
    A(f"> Generado por `backend/tools/model_inventory.py` desde el código (commit `{M['commit']}`), la config "
      f"(`backend/config/*.toml`) y una muestra medida: {M['sample']} ({M['companies']} empresas: "
      + ", ".join(f"{ARCH_SHORT.get(k, k)} {v}" for k, v in sorted(M["by_archetype"].items(), key=lambda kv: -kv[1]))
      + "). No editar a mano. Lo escrito a mano está marcado como *juicio* (la fórmula y la referencia de cada "
        "componente, la propuesta de tipos objetivo y las candidatas a simplificar).")
    A("")
    A("Arquetipos: " + ", ".join(f"**{ARCH_SHORT[a]}** = {a}" for a in ARCHETYPES) + ". En la tabla de "
      "aplicabilidad, **A** = aplica (se registra, con o sin dato), **ns** = solo como no significativo, **–** = no "
      "aplica (no se registra o se registra como «no aplica»), **?** = el arquetipo no está en la muestra.")
    A("")

    # ── 1. Resumen numérico ──
    A("## 1. Resumen numérico")
    A("")
    sc = Counter(r["scope"] for r in rows)
    A(f"- **{len(rows)} variables que puntúan** (componentes de la cobertura de las 5 categorías): "
      f"**{sc['universal']} universales** (aplican a los 7 arquetipos), **{sc['casi universal']} casi universales** "
      f"(a 5 o 6: las apagan las listas «no aplica»), **{sc['específica']} específicas** (a 4 o menos; casi todas, a "
      f"uno solo) y **{sc['muerta']} muertas** (se registran pero no aplican a ningún arquetipo de la muestra: "
      + ", ".join(f"«{r['name']}» ({r['category']})" for r in rows if r["scope"] == "muerta") + ").")
    A(f"- **{len(inv['outside_coverage'])} ajustes que puntúan fuera de la cobertura** (bonos y topes que no cuentan como "
      "componente: Forward P/E, tope por ROIC − WACC…), medidos en el desglose de la muestra.")
    br = inv["branches"]
    A(f"- **{len(br)} ramas por arquetipo o subtipo en el código** (comparaciones `archetype == …`, `subtype == …`) en "
      f"{len({b['file'] for b in br})} archivos; las que más: "
      + ", ".join(f"`{f}` {n}" for f, n in Counter(b["file"] for b in br).most_common(6)) + ".")
    n_na = sum(len(v) for v in inv["na_config"].values())
    A(f"- **{n_na} entradas «no aplica»** por arquetipo en `sectors.archetypes.not_applicable` "
      + "(" + ", ".join(f"{ARCH_SHORT.get(k, k)} {len(v)}" for k, v in inv["na_config"].items()) + ") y "
      f"{sum(len(v) for v in inv['na_subtype'].values())} por subtipo; las leen {len(inv['na_sites'])} sitios del código.")
    ov = inv["sector_overrides"]
    A(f"- **{sum(len(v) for v in ov.values())} ajustes de umbral por sector** en "
      f"{sum(1 for v in ov.values() if v)} sectores (`sectors.score_thresholds.overrides`), todos marcados PROVISIONAL.")
    reads = inv["cfg_reads"]
    A(f"- **{len({r['key'] for r in reads})} claves de config leídas** en {len(reads)} sitios (lecturas, alertas, "
      "veredicto, confianza; §4).")
    A("")
    A("Por arquetipo: cuántas variables puntúan en cada uno y cuántas son solo suyas.")
    A("")
    A("| Arquetipo | Empresas en la muestra | Variables que aplican | Universales | Casi universales | Específicas | Solo suyas |")
    A("|---|---:|---:|---:|---:|---:|---:|")
    for arch in ARCHETYPES:
        ap = [r for r in rows if r["applies"].get(arch) in ("A", "ns")]
        only = [r for r in ap if sum(1 for v in r["applies"].values() if v in ("A", "ns")) == 1]
        c = Counter(r["scope"] for r in ap)
        A(f"| {arch} | {M['by_archetype'].get(arch, 0)} | {len(ap)} | {c['universal']} | {c['casi universal']} | "
          f"{c['específica']} | {len(only)} |")
    A("")

    # ── 2. Tipos de empresa ──
    A("## 2. Tipos de empresa: los de hoy frente a la lista cerrada objetivo")
    A("")
    A("Objetivo (decisión del usuario, 28-oct-2026): " + ", ".join(f"**{t}**" for t in TARGET) + ".")
    A("")
    cr = inv["classification_rules"]
    counts = (scan or {}).get("archetypes") or {}
    subs = (scan or {}).get("subtypes") or {}
    A("| Tipo de hoy | Reglas de `classify.py` que lo deciden (línea) | Empresas en el universo | Iría a (*juicio*) | Por qué |")
    A("|---|---|---:|---|---|")
    keys = ["MATURE", "GROWTH_PROFITABLE", "CYCLICAL", "GROWTH_PRE_PROFIT", "FINANCIAL · banco", "FINANCIAL · aseguradora",
            "FINANCIAL · conglomerado", "FINANCIAL · financiera", "REIT", "UTILITY"]
    for k in keys:
        arch, _, sub = k.partition(" · ")
        rr = [f"`{x['rule']}` ({x['line']})" for x in cr if x["archetype"] == arch and (x["subtype"] or "") == sub]
        n = subs.get(k) if sub else counts.get(arch)
        tgt, why = TARGET_TYPES[k]
        A(f"| {k} | {', '.join(rr)} | {n if n is not None else '—'} | {tgt} | {why} |")
    A("")
    sh = Counter(TARGET_TYPES[k][0] for k in keys)
    A("**Qué sobra o se solapa** (*juicio*, con las cifras de arriba):")
    A("")
    A("- **Sobran como tipos 3 de 7 arquetipos**: GROWTH_PROFITABLE (sin ninguna herramienta propia: su lista «no aplica» "
      "está vacía y puntúa exactamente con las de MATURE), CYCLICAL (cambia el método —ciclo medio, P/FCF y EV/EBITDA "
      "normalizados, sin P/E ni PEG— no la contabilidad) y MATURE, que es la «empresa general». Los tres se pueden "
      "fundir en uno: la normalización del ciclo pasa a ser una propiedad medida (la historia de EDGAR ya decide "
      "`historia_ciclica`) que cualquier empresa puede tener.")
    A("- **FINANCIAL es dos tipos con un solo juego de herramientas**: banco y aseguradora comparten la solidez bancaria, "
      "el D/E bancario, el P/B y P/TBV justificados y la estabilidad del ROE; solo los distingue el margen neto (F9 · R4: "
      "no aplica al banco). La lista objetivo los separa: la aseguradora necesitará su ratio combinado o su resultado "
      "técnico, hoy inexistentes.")
    A("- **Subtipos que se solapan**: «conglomerado» (aseguradora con ≥ 50 % de ingresos no aseguradores, BRK-B) y "
      "«financiera» (Credit Services con balance y financieras ambiguas) no tienen herramienta propia: el primero es "
      "una aseguradora, el segundo un banco.")
    A("- **Excepciones dentro de un tipo que ya son reglas generales**: las redes de pago y las gestoras dentro de "
      "Financial Services ya son MATURE (empresa general); las industrias de circulante negativo y de Altman "
      "referencial (§5.4) son lecturas por modelo de negocio, no tipos.")
    A("- Con la propuesta, el universo queda en: " + ", ".join(f"{t} ({sh[t]} tipos de hoy)" for t in TARGET) + ".")
    A("")

    # ── 3. Variables que puntúan ──
    A("## 3. Variables que puntúan")
    A("")
    A("Una fila por componente de la cobertura (`CategoryCoverage.comp`, `not_sig`, `derived_comp`). **Banda**: la clave "
      "de puntos y su umbral en config con su valor. **Origen del umbral**: PROVISIONAL si el TOML lo marca así, "
      "«calibrado» si su comentario cita la muestra con que se fijó. **Fórmula** y **referencia**: *juicio* (META).")
    A("")
    cat = None
    for r in rows:
        if r["category"] != cat:
            cat = r["category"]
            A(f"### {cat}")
            A("")
            A("| Variable | Fórmula | Referencia | Banda (config) | Origen del umbral | "
              + " | ".join(ARCH_SHORT[a] for a in ARCHETYPES)
              + " | Alcance | Peso medido (empresas · \\|ajuste\\| medio · % que mueve) | «No aplica» | Condición en el código | Dónde |")
            A("|---|---|---|---|---|" + "---|" * len(ARCHETYPES) + "---|---|---|---|---|")
        bands = "; ".join(f"`{k.split('.', 2)[-1]}` = {_short(v, 40)}" for k, v in r["bands"][:4]) or "—"
        A(f"| **{_cell(r['name'])}** | {_cell(r['formula'] or '—')} | {_cell(r['reference'] or '—')} | {_cell(bands)} | "
          f"{r['threshold_source'] if r['bands'] else '—'} | "
          + " | ".join(r["applies"][a] for a in ARCHETYPES)
          + f" | {r['scope']} | "
          + (f"{r['weight']['n']} · {r['weight']['mean_abs']:.1f} · {r['weight']['moves']:.0%}" if r["weight"]["n"] else "—")
          + f" | {', '.join(f'`{k}`' for k in r['na_keys']) or '—'} | "
            f"{_cell('; '.join(r['guards'])[:120]) or '—'} | {', '.join(r['sites'][:3]) or '(solo medido)'} |")
    A("")
    if inv["outside_coverage"]:
        A("### Ajustes que puntúan fuera de la cobertura")
        A("")
        A("Aparecen en el desglose con un ajuste distinto de 0 pero no son un componente de la cobertura: no cuentan en "
          "el reescalado ni en «sin dato». Medidos en la muestra (empresas en las que puntúan).")
        A("")
        A("| Categoría | Ajuste | Empresas |")
        A("|---|---|---:|")
        for x in inv["outside_coverage"]:
            A(f"| {x['category']} | {_cell(x['metric'])} | {x['companies']} |")
        A("")

    # ── 4. Lo que cambia lecturas, veredicto o confianza ──
    A("## 4. Lo que cambia una lectura, el veredicto o la confianza sin ser un componente")
    A("")
    A("Cada tabla de la config que el código lee, por lo que mueve, con los módulos que la leen (archivo:primera "
      "línea) y cuántas claves. Los valores están en `backend/config/`.")
    A("")
    groups: Dict[str, Dict[str, Any]] = {}
    for r in reads:
        k = r["key"]
        parts = k.split(".")
        top = (".".join(parts[:3]) if k.startswith("thresholds.score.") else parts[0]
               if parts[0] in ("base_rates", "industries", "betas", "betas_regional", "country_risk", "review")
               else ".".join(parts[:2]))
        g = groups.setdefault(top, {"keys": set(), "sites": {}})
        g["keys"].add(k)
        g["sites"].setdefault(r["file"].split("/")[-1], r["line"])
        g["sites"][r["file"].split("/")[-1]] = min(g["sites"][r["file"].split("/")[-1]], r["line"])
    A("| Mueve | Tabla de config | Claves | La leen |")
    A("|---|---|---:|---|")
    for top in sorted(groups, key=lambda t: (_moves(t)[0], t)):
        order, what = _moves(top)
        if order >= 9:
            continue
        g = groups[top]
        A(f"| {what} | `{top}` | {len(g['keys'])} | "
          + ", ".join(f"{f}:{ln}" for f, ln in sorted(g["sites"].items())) + " |")
    A("")

    # ── 5. Reglas especiales ──
    A("## 5. Reglas especiales")
    A("")
    A("### 5.1 «No aplica» por arquetipo y por subtipo (config)")
    A("")
    keys_all = sorted({k for v in inv["na_config"].values() for k in v} | {k for v in inv["na_subtype"].values() for k in v})
    A("| Clave | " + " | ".join(ARCH_SHORT[a] for a in ARCHETYPES) + " | Subtipos | La leen |")
    A("|---|" + "---|" * len(ARCHETYPES) + "---|---|")
    for k in keys_all:
        cells = ["–" if k in inv["na_config"].get(a, []) else "" for a in ARCHETYPES]
        subs_ = [s for s, v in inv["na_subtype"].items() if k in v]
        sites = [f"{x['file'].split('/')[-1]}:{x['line']}" for x in inv["na_sites"] if x["key"] == k]
        A(f"| `{k}` | " + " | ".join(cells) + f" | {', '.join(subs_) or ''} | {', '.join(sites[:4])}"
          + (f" (+{len(sites) - 4})" if len(sites) > 4 else "") + " |")
    A("")
    A("### 5.2 Ramas por arquetipo o subtipo en el código")
    A("")
    A("| Archivo | Ramas | Arquetipos que nombra | Funciones (ramas) |")
    A("|---|---:|---|---|")
    by_file: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for b in br:
        by_file[b["file"]].append(b)
    for f, xs in sorted(by_file.items(), key=lambda kv: -len(kv[1])):
        types = Counter(t for x in xs for t in x["types"])
        fns = Counter(x["function"] for x in xs)
        A(f"| `{f}` | {len(xs)} | " + ", ".join(f"{ARCH_SHORT.get(t, t)} {n}" for t, n in types.most_common())
          + " | " + ", ".join(f"`{k}` {n}" for k, n in fns.most_common(6)) + (" …" if len(fns) > 6 else "") + " |")
    A("")
    A("<details><summary>Todas las ramas (archivo:línea, función, condición)</summary>")
    A("")
    for b in br:
        A(f"- `{b['file']}:{b['line']}` · `{b['function']}` · `{_cell(b['condition'])}`")
    A("")
    A("</details>")
    A("")
    A("### 5.3 Ajustes de umbral por sector")
    A("")
    ks = sorted({k for v in ov.values() for k in v})
    A("| Sector | " + " | ".join(f"`{k}`" for k in ks) + " |")
    A("|---|" + "---|" * len(ks))
    for s, v in ov.items():
        A(f"| {s} | " + " | ".join(_short(v[k], 8) if k in v else "" for k in ks) + " |")
    A("")
    A(f"Los umbrales por defecto (`sectors.score_thresholds.default`) y las medianas por sector "
      f"(`sectors.benchmarks.sectors`, {len(cfg_value('sectors.benchmarks.sectors') or {})} sectores) son PROVISIONALES "
      "(«fijados a mano en versiones anteriores», cabecera de `sectors.toml`). La referencia de industria de Damodaran "
      "(`config/industries.toml`) ya los sustituye en los márgenes y en P/E y EV/EBITDA; el ROE, el ROA y el D/E siguen "
      "con los del sector.")
    A("")
    A("### 5.4 Listas de industrias y excepciones")
    A("")
    lists = [("sectors.archetypes.cyclical_industries", "industrias cíclicas siempre"),
             ("sectors.archetypes.cyclical_conditional_industries", "cíclicas condicionales (si hay reversión)"),
             ("sectors.archetypes.utility_industries", "utilities reguladas"),
             ("sectors.archetypes.financial_mature_industries", "financieras que son MATURE"),
             ("sectors.archetypes.payment_network_industries", "redes de pago (MATURE si activos/ingresos ≤ 3)"),
             ("sectors.business_model.negative_working_capital_industries", "circulante negativo estructural: el "
                                                                              "current ratio no puntúa"),
             ("sectors.business_model.altman_referential_industries", "Altman referencial (no vota)"),
             ("sectors.business_model.captive_finance_segment_patterns", "financiera cautiva por segmentos: Altman "
                                                                         "referencial"),
             ("sectors.financials.sector_names", "sectores tratados como financieros")]
    A("| Lista | Qué hace | Entradas | La leen |")
    A("|---|---|---:|---|")
    for k, what in lists:
        v = cfg_value(k) or []
        leaf = k.rsplit(".", 1)[-1]
        sites = sorted({f"{r['file'].split('/')[-1]}:{r['line']}" for r in reads if r["key"].endswith(leaf)})
        A(f"| `{k}` | {what} | {len(v)} | {', '.join(sites[:3])} |")
    A("")
    A("### 5.5 No significativo, referencial e informativo")
    A("")
    ns = [r for r in rows if "not_sig" in r["kinds"]]
    A("Componentes que pueden salir **no significativos** (no cuentan en la cobertura, tienen su línea en el desglose): "
      + ", ".join(f"**{r['name']}** ({r['category']})" for r in ns) + ".")
    A("")
    A("Además, en `score_solidez_financiera`: el Altman **referencial** (industrias de §5.4 y financiera cautiva) y el D/E "
      "**informativo** (REIT, o caja neta); el ROE se sustituye por el ROIC con apalancamiento alto (D/E > umbral del "
      "sector); el **tope por ROIC − WACC** (`thresholds.score.rentabilidad.spread_caps`) limita la Rentabilidad.")
    A("")

    # ── 6. Candidatas a simplificar ──
    A("## 6. Candidatas a simplificar")
    A("")
    A("### 6.1 Variables que votan lo mismo (medido)")
    A("")
    cr_ = inv["correlations"]
    A(f"Pares de componentes cuyos ajustes se mueven juntos en la muestra (correlación de Pearson de los ajustes, |r| ≥ "
      f"0,6, al menos 12 empresas con los dos). «Mismo signo»: empresas en que los dos suman, restan o son 0 a la vez.")
    A("")
    A("| Componente A | Componente B | r | Empresas | Mismo signo |")
    A("|---|---|---:|---:|---:|")
    for x in cr_[:25]:
        A(f"| {x['a'][0]} · {x['a'][1]} | {x['b'][0]} · {x['b'][1]} | {x['r']:.2f} | {x['n']} | {x['same_sign']:.0%} |")
    if not cr_:
        A("| (ninguno con la muestra actual) | | | | |")
    A("")
    A("### 6.2 Duplicadas en la config")
    A("")
    A("Misma hoja y mismo valor en tablas distintas (una sola fuente por concepto evitaría que diverjan):")
    A("")
    for d in sorted(inv["duplicated_config"], key=lambda d: -len(d["keys"]))[:20]:
        A(f"- `{d['leaf']}` = {_short(d['value'], 40)}: " + ", ".join(f"`{k}`" for k in d["keys"]))
    A("")
    A("Mismos puntos con nombres distintos (la misma escala repetida por arquetipo):")
    A("")
    for d in sorted(inv["same_bands"], key=lambda d: -len(d["keys"])):
        A(f"- {d['points']}: " + ", ".join(f"`{k}`" for k in d["keys"]))
    A("")
    A("### 6.3 Propuestas de simplificación, por impacto (*juicio*, con la evidencia de §3, §6.1 y del escaneo)")
    A("")
    for title, body in SIMPLIFY:
        A(f"- **{title}** {body}")
    A("")
    A("## 7. Cómo se regenera")
    A("")
    A("```bash")
    A("cd backend && ../../finanzer_next/.venv313/bin/python tools/model_inventory.py            # muestra: fixtures")
    A("cd backend && ../../finanzer_next/.venv313/bin/python tools/model_inventory.py --scan ../docs/modelo/ESCANEO_<fecha>.json")
    A("```")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


SIMPLIFY = [
    ("1 · Una sola referencia por métrica: la industria de Damodaran (sin la propia empresa) en el score, en la fila y en "
     "la alerta.",
     "Hoy el ROE y el ROA —el ROE es la variable que más pesa del modelo: ±3,7 de media en 479 empresas— y el D/E se leen "
     "contra tablas por sector escritas a mano (PROVISIONALES), las filas contra Damodaran y las alertas contra el sector "
     "o contra umbrales absolutos (P/E > 35x, EV/EBITDA > 25x): de ahí las fortalezas y alertas con el tono contrario a "
     "su fila del escaneo. Quita `sectors.score_thresholds` (12 sectores, 80 ajustes). La parte «sin la propia empresa» "
     "es la N2 de F10."),
    ("2 · Rentabilidad: de 5 votos (ROE, ROA, margen operativo, margen neto, ROIC − WACC) a 2.",
     "ROIC − WACC (ROE − Ke en banco y aseguradora, el mismo que alimenta su P/B justificado) y un margen frente a la "
     "industria. Medido: ROE y ROIC − WACC r = 0,81 (407 empresas), margen operativo y neto 0,76 (462), ROE y ROA 0,67 "
     "(479). El ROE ya se cambia por el ROIC con apalancamiento alto y el tope por ROIC − WACC (44 empresas) ya manda."),
    ("3 · Calidad de ganancias: OCF > 0 y FCF > 0 (dos signos que suman +3 y +3 casi siempre) → FCF / beneficio.",
     "Los dos signos mueven 1.476 y 1.404 puntos en el universo, casi todo en la misma dirección; el cociente FCF / "
     "beneficio (o FCF / ingresos sin beneficio, y dividendo / FFO en el REIT, que es el mismo cociente) ya lleva esa "
     "información y separa a las empresas."),
    ("4 · Múltiplos de beneficio: P/E, Forward P/E y PEG → un voto (F10 · N4).",
     "El Forward P/E puntúa como bono FUERA de la cobertura en 174 empresas; el PEG y el crecimiento del BPA, r = 0,73. "
     "El P/FFO del REIT y el EV/Ventas del pre-beneficio son el mismo «precio frente a su beneficio del tipo»: un "
     "miembro de beneficio por tipo dentro del bloque."),
    ("5 · Denominador ≤ 0 ⇒ «no significativo» con motivo, en un solo sitio (`CategoryCoverage`).",
     "El 59 % de los 289 vacíos sin motivo del escaneo son ROE y D/E con patrimonio negativo, P/E, P/FCF y EV/EBITDA "
     "con beneficio, FCF o EBITDA negativos: hoy cuentan como «sin dato» sin decir por qué y restan cobertura. Una "
     "regla general sustituye a las excepciones de cada métrica (ROE con ROA > 3 %, D/E negativo, cobertura con EBIT "
     "< 0)."),
    ("6 · Una serie anual única (EDGAR) para la historia de 10 años, el gráfico histórico y el crecimiento.",
     "Las 11 cifras dobles del escaneo son de la historia de 10 años frente al gráfico (o dentro de ella): beneficio "
     "atribuido frente a disponible para el accionista común (EIX, IVZ, TKO), un concepto de ingresos parcial (NTAP, "
     "−10 %) y ejercicios de transición duplicados (LHX, KDP). Es la M5 de la hoja de ruta, aplicada a todos los "
     "bloques."),
    ("7 · Apalancamiento y cobertura: D/E + deuda neta/EBITDA (bandas de REIT y de utility) + cobertura (bandas de "
     "utility) → deuda neta/EBITDA y cobertura frente a su industria.",
     "Quita cuatro juegos de bandas absolutas por tipo (`reit_nde_*`, `utility_nde_*`, `utility_coverage_*`) y la "
     "excepción «D/E informativo en REIT»; D/E y cobertura votan juntos (r = 0,80 en la muestra de los fixtures)."),
    ("8 · Tipos: MATURE + GROWTH_PROFITABLE + CYCLICAL → empresa general; FINANCIAL → banco y aseguradora.",
     "GROWTH_PROFITABLE no tiene ninguna herramienta propia; CYCLICAL cambia el método (ciclo medio, normalizados), que "
     "puede ser una propiedad medida de cualquier empresa. Quita además las dos variables muertas de la solidez bancaria "
     "(«D/E bancario» y «P/B», que la lista «no aplica» de FINANCIAL apaga siempre) y deja al pre-beneficio (1 empresa "
     "en el universo) como el único tipo sin beneficio."),
    ("9 · Crecimiento: el método robusto de los ingresos para toda serie (BPA, FCF, FFO por acción) y el retorno total "
     "(dividendo + crecimiento por acción) para todos.",
     "La parte del BPA y del PEG es la N3 de F10; generalizarla quita la excepción de MATURE con dividendo ≥ 4 % y el "
     "retorno total solo para REIT."),
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", help="json de tools/universe_scan.py (muestra: el universo)")
    ap.add_argument("--out", default=DOCS)
    args = ap.parse_args(argv)
    scan = None
    if args.scan:
        with open(args.scan, encoding="utf-8") as fh:
            scan = json.load(fh)
        sample = {s: {"archetype": r["archetype"], "subtype": r.get("subtype"), "components": r.get("components") or [],
                      "breakdown": r.get("breakdown") or {}}
                  for s, r in (scan.get("components") or {}).items()}
        label = f"el escaneo del universo del {scan['meta']['date']} (`{os.path.basename(args.scan)}`)"
    else:
        sample = fixture_sample()
        label = "los fixtures del panel y de local en replay (sin red)"
    inv = build(sample, label)
    os.makedirs(args.out, exist_ok=True)
    js = dict(inv)
    js.pop("notes")
    with open(os.path.join(args.out, "inventario.json"), "w", encoding="utf-8") as fh:
        json.dump(js, fh, ensure_ascii=False, indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o))
    write_md(inv, os.path.join(args.out, "INVENTARIO.md"), scan)
    print(f"inventario: {os.path.join(args.out, 'INVENTARIO.md')} ({len(inv['components'])} variables)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
