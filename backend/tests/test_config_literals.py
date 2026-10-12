"""Las funciones migradas en la etapa 4 leen sus umbrales de la config
(backend/config/*.toml), no de literales numéricos.

El test recorre el AST de cada función migrada y falla si encuentra un literal
numérico que no esté permitido. Se permiten, en general:
  · 0, 1 y 100 (comprobaciones de signo, identidades, contadores y paso a %);
  · índices de lista/tupla y cortes (p[0], items[:cap]);
  · el número de decimales de round(x, n) y de formato;
  · la raíz cuadrada como ** 0.5.
Cualquier otro literal debe ir a la config o figurar en EXCEPTIONS con su
justificación.
"""
import ast
import os

import pytest

LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
BACKEND = os.path.dirname(LIB)

GENERIC_OK = {0, 1, 100}

MIGRATED = {
    "lib/financial_ratios.py": [
        "is_financial_sector", "altman_z_score", "financial_health_score", "piotroski_f_score",
        "calculate_wacc", "classify_company_type", "calculate_growth_quality_score",
        "adjust_valuation_for_growth", "graham_number", "dcf_multi_stage", "dcf_multi_stage_dynamic",
        "calculate_all_ratios", "score_solidez_financiera", "score_solidez_financiera_financial",
        "score_rentabilidad", "score_valoracion", "score_calidad_ganancias", "score_crecimiento",
        "calculate_score_v2", "dcf_sensitivity_analysis",
    ],
    "lib/alert_interpretations.py": [
        "_years_ebitda", "_pe", "_ev_ebitda", "_fcf_yield", "_peg", "_dcf", "_roe", "_spread",
        "_margins", "_leverage", "_coverage", "_liquidity", "_altman", "_fcf", "_earnings_quality",
        "_growth", "_eps_growth", "_piotroski", "_deterioration", "_beta", "_drawdown", "build_signals",
    ],
    "lib/pdf_report.py": [
        "read_vs_sector", "read_pe", "read_roe", "read_spread", "read_current", "read_de",
        "read_coverage", "read_nde", "read_payout", "read_growth", "read_upside", "read_graham",
        "read_beta", "read_pos52", "score_band", "read_buyback", "read_fcf_yield",
    ],
    "lib/validate.py": [
        "growth_guard", "_rule_fcf", "_rule_impossible", "_rule_margins", "_rule_units",
        "_rule_growth", "_rule_split_basis", "_rule_jumps", "validate_outputs",
    ],
    "main.py": ["_get_sector_benchmarks", "_compute_analysis"],
}

# (archivo, función, valor) -> justificación
EXCEPTIONS = {
    ("lib/financial_ratios.py", "dcf_sensitivity_analysis", 0.001):
        "tolerancia de punto flotante al generar los pasos del grid y localizar el caso base",
    ("lib/financial_ratios.py", "dcf_sensitivity_analysis", 2):
        "mediana: n // 2, n % 2 y media de los dos centrales",
    ("lib/validate.py", "_rule_growth", 1e-12):
        "tolerancia de comparación de floats (¿cambió el valor tras la guarda?)",
    ("lib/validate.py", "_rule_growth", 3):
        "definición de CAGR-3Y (3 intervalos)",
    ("lib/validate.py", "_rule_growth", 4):
        "CAGR con el máximo de intervalos disponibles en _statements_fy (5 ejercicios)",
    ("main.py", "_compute_analysis", 15):
        "longitud máxima de un ticker en la validación de entrada de la API",
    ("main.py", "_compute_analysis", 400): "código HTTP",
    ("main.py", "_compute_analysis", 404): "código HTTP",
    ("main.py", "_compute_analysis", 500): "código HTTP",
    ("main.py", "_compute_analysis", 2):
        "quitar el prefijo '✓ '/'✗ ' del detalle de Piotroski (presentación)",
    ("main.py", "_compute_analysis", 9): "máximo del Piotroski F-Score (9 señales, por definición)",
}


def _allowed_positions(fn):
    """ids de nodos Constant que son índices, cortes, decimales de round o ** 0.5."""
    ok = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Subscript):
            for sub in ast.walk(node.slice):
                if isinstance(sub, ast.Constant):
                    ok.add(id(sub))
        elif isinstance(node, ast.Call) and getattr(node.func, "id", None) == "round" and len(node.args) == 2:
            if isinstance(node.args[1], ast.Constant):
                ok.add(id(node.args[1]))
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow) and \
                isinstance(node.right, ast.Constant) and node.right.value == 0.5:
            ok.add(id(node.right))
        elif isinstance(node, ast.JoinedStr):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant):
                    ok.add(id(sub))
    return ok


def _residuals(relpath, funcs):
    path = os.path.join(BACKEND, relpath)
    tree = ast.parse(open(path, encoding="utf-8").read())
    defs = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    missing = [f for f in funcs if f not in defs]
    assert not missing, f"{relpath}: funciones migradas inexistentes {missing}"
    out = []
    for name in funcs:
        fn = defs[name]
        allowed = _allowed_positions(fn)
        for node in ast.walk(fn):
            if not (isinstance(node, ast.Constant) and type(node.value) in (int, float)):
                continue
            if id(node) in allowed or node.value in GENERIC_OK:
                continue
            if (relpath, name, node.value) in EXCEPTIONS:
                continue
            out.append(f"{relpath}:{node.lineno} {name}: {node.value!r}")
    return out


@pytest.mark.parametrize("relpath", sorted(MIGRATED))
def test_no_residual_numeric_literals(relpath):
    residual = _residuals(relpath, MIGRATED[relpath])
    assert residual == [], ("literales numéricos sin migrar a config (o añádelos a EXCEPTIONS con "
                            "su justificación):\n  " + "\n  ".join(residual))


def test_exceptions_are_still_needed():
    """Una excepción que ya no corresponde a ningún literal debe borrarse."""
    for (relpath, func, value), why in EXCEPTIONS.items():
        assert why, (relpath, func, value)
        tree = ast.parse(open(os.path.join(BACKEND, relpath), encoding="utf-8").read())
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == func)
        allowed = _allowed_positions(fn)
        hits = [n for n in ast.walk(fn) if isinstance(n, ast.Constant) and n.value == value
                and type(n.value) is type(value) and id(n) not in allowed]
        assert hits, f"excepción obsoleta: {relpath} {func} {value!r}"


def test_detector_catches_a_literal(tmp_path, monkeypatch):
    """El detector no es un no-op: un umbral en línea se reporta."""
    src = tmp_path / "lib" / "fake.py"
    src.parent.mkdir()
    src.write_text("def f(x):\n    if x >= 0.35:\n        return round(x, 2)\n    return x * 100\n", encoding="utf-8")
    monkeypatch.setattr(__import__(__name__), "BACKEND", str(tmp_path))
    assert _residuals("lib/fake.py", ["f"]) == ["lib/fake.py:2 f: 0.35"]
