"""
Muestras forzadas del contrato backend -> frontend: casos que ningún ticker de los juegos cubre, generados con el
mismo display.build_display sobre una salida real modificada. Las usa test_frontend_contract (estricto) y se guardan
en tests/golden/forzados/ para que `npm run check` (sin argumentos) también las vea.

    ../.venv313/bin/python tests/contract_forced.py --write     # tras regenerar los golden

test_forced_samples_are_up_to_date falla si las guardadas no coinciden con las que salen hoy.
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend as fb  # noqa: E402

FORCED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden", "forzados")


def build(outputs):
    """{nombre: análisis} a partir de {ticker: análisis} del juego local."""
    import display
    out = {}
    a = copy.deepcopy(outputs["SNOW"])
    a["score"]["breakdown"]["Crecimiento"].update(conclusive=False, coverage=0.33)
    a["display"] = display.build_display(a)
    out["SNOW_no_concluyente"] = a
    # Etapa 9c, gráficos que ningún ticker cubre: runway en años y caja neta en Deuda neta / EBITDA.
    r = copy.deepcopy(outputs["SNOW"])
    r["archetype_metrics"]["runway"] = {"state": "runway", "years": 1.8}
    r["display"] = display.build_display(r)
    assert r["display"]["charts"]["solvency"]["runway"].get("years") == 1.8
    out["SNOW_runway"] = r
    n = copy.deepcopy(outputs["V"])
    n["key_metrics"]["net_debt_to_ebitda"] = -0.4
    n["display"] = display.build_display(n)
    assert any(g.get("net_cash") for g in n["display"]["charts"]["solvency"]["gauges"])
    out["V_caja_neta"] = n
    # Fase 2b (T5): EBIT < 0 con deuda neta (cobertura negativa). Con la deuda coherente con el EBITDA, SNOW pasó a
    # caja neta y ningún ticker de los juegos lo cubre.
    q = copy.deepcopy(outputs["SNOW"])
    q["key_metrics"].update(net_debt=4e8, interest_coverage=-8.4, interest_coverage_state="negativa")
    q["display"] = display.build_display(q)
    assert any(g.get("negative") for g in q["display"]["charts"]["solvency"]["gauges"])
    out["SNOW_cobertura_negativa"] = q
    return out


def local_outputs():
    res = {}
    for t in ("SNOW", "V"):
        with fb.replay(fb.fixtures_dir("local")) as store:
            res[t] = fb.run_analysis(t, store)
    return res


def write(samples, base=FORCED_DIR):
    os.makedirs(base, exist_ok=True)
    for name, a in samples.items():
        with open(os.path.join(base, f"{name}.json"), "w", encoding="utf-8") as fh:
            fh.write(fb.stable_json(a))


if __name__ == "__main__":
    if "--write" not in sys.argv:
        sys.exit(__doc__)
    s = build(local_outputs())
    write(s)
    print(f"{len(s)} muestras forzadas → {FORCED_DIR}")
