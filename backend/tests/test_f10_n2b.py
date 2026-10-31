"""F10 · N2b (decisión del PM tras N2): el ROE estable del P/B en dos etapas converge a la industria GLOBAL sin la
empresa (lib/industry_bench.global_roe), no al resto de su región. La región de la referencia sigue siendo la de la
clasificación de Damodaran (la regla de la región por la geografía de los ingresos se retiró: la prima país sigue con
esa geografía, que mide exposición al riesgo)."""
import industry_bench as IB


def test_two_stage_roe_converges_to_global_industry_without_the_company():
    """CB: Chubb es el 78 % del patrimonio de «Seguros de daños» de Europa (resto: ROE del 30 %); el ROE estable es el
    de la industria global sin ella (≈ 17,6 % en vivo; aquí, sin sus cifras, la mediana de los pares)."""
    g = IB.global_roe("Insurance (Prop/Cas.)", "CB", None, "Switzerland", None, "Chubb")
    assert g is not None and 0.10 < g["value"] < 0.25
    assert "global" in g["text"]
    assert IB.global_roe(None) is None and IB.global_roe(["Banks (Regional)"]) is None


def test_two_stage_text_names_the_roe_source():
    import archetype_metrics as am
    xm = {"book_value_cagr_3y": 0.25, "roe_reference": 0.28, "cost_of_equity": 0.11, "terminal_growth": 0.03,
          "pb": 2.0, "pb_justified": 3.0}
    out = am.apply_two_stage(xm, 0.16, 0.3, 0.02, roe_source="industria «Seguros de daños» global sin la empresa")
    assert out["two_stage"]["applied"] and "global sin la empresa" in out["two_stage"]["text"]
    assert out["two_stage"]["industry_roe_source"].startswith("industria")
