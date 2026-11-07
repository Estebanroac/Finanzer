"""
Revisión externa del informe de COST (30-oct, docs/fiabilidad/revision-cost-2026-10-30.md): los fallos baratos y
generales que entran en la v4.

Hallazgo 2: COST mostraba «Crecimiento del BPA: sin dato, menos de 4 ejercicios» con 10 años de beneficio neto. Yahoo
trae el beneficio del último ejercicio (FY2026, cerrado el 30-ago) pero no su BPA diluido ni sus acciones diluidas
medias: la serie empezaba con un hueco. Regla general: un ejercicio sin BPA toma el de EDGAR y, si el emisor no lo
etiqueta, beneficio neto ÷ acciones diluidas medias de EDGAR.
"""
import pytest

import edgar_backup
import sec_edgar as edgar
from classify import not_applicable
from settings import cfg


def _f(start, end, val, filed, form="10-K", accn="k26"):
    out = {"end": end, "val": val, "filed": filed, "form": form, "accn": accn}
    if start:
        out["start"] = start
    return out


def _ed(concepts):
    facts = {"facts": {"us-gaap": {"Assets": {"units": {"USD": [_f(None, "2026-08-30", 10, "2026-10-08")]}},
                                   **concepts}}}
    return {"status": "ok", "facts_status": "ok", "facts": edgar._index_facts(facts)}


def _info(eps):
    st = {"inc_ends": ["2026-08-31", "2025-08-31", "2024-08-31", "2023-08-31", "2022-08-31"],
          "net_income": [9226e6, 8099e6, 7367e6, 6292e6, None], "diluted_eps": eps}
    return {"currency": "USD", "_as_of": {"type": "ttm", "date": "2026-08-31", "fields": {}}, "_provenance": {},
            "_statements_fy": st}


_FY26 = ("2025-09-01", "2026-08-30")


def test_fy_eps_gap_takes_the_diluted_eps_of_edgar():
    ed = _ed({"EarningsPerShareDiluted": {"units": {"USD/shares": [_f(*_FY26, 20.74, "2026-10-08")]}}})
    info = _info([None, 18.21, 16.56, 14.16, 13.14])
    log = edgar_backup.apply(info, ed)
    assert info["_statements_fy"]["diluted_eps"] == [20.74, 18.21, 16.56, 14.16, 13.14]
    x = next(x for x in log["fy"] if x["field"] == "FY.diluted_eps")
    assert x["fy_end"] == "2026-08-31" and x["concept"] == "us-gaap:EarningsPerShareDiluted"
    assert "BPA diluido" in x["how"]


def test_fy_eps_without_the_tag_is_net_income_over_diluted_shares():
    ed = _ed({"NetIncomeLoss": {"units": {"USD": [_f(*_FY26, 9226e6, "2026-10-08")]}},
              "WeightedAverageNumberOfDilutedSharesOutstanding": {"units": {"shares": [
                  _f(*_FY26, 445e6, "2026-10-08")]}}})
    info = _info([None, 18.21, 16.56, 14.16, 13.14])
    log = edgar_backup.apply(info, ed)
    assert abs(info["_statements_fy"]["diluted_eps"][0] - 9226 / 445) < 1e-9
    x = next(x for x in log["fy"] if x["field"] == "FY.diluted_eps")
    assert "beneficio neto ÷ acciones diluidas medias" in x["how"]


def test_fy_eps_never_replaces_the_one_of_yahoo():
    ed = _ed({"EarningsPerShareDiluted": {"units": {"USD/shares": [_f(*_FY26, 99.0, "2026-10-08")]}}})
    info = _info([20.70, 18.21, 16.56, 14.16, 13.14])
    log = edgar_backup.apply(info, ed)
    assert info["_statements_fy"]["diluted_eps"][0] == 20.70
    assert not [x for x in log["fy"] if x["field"] == "FY.diluted_eps"]


def test_fy_eps_of_edgar_on_another_basis_is_not_mixed():
    # En un ejercicio que dan los dos, el BPA de EDGAR no cuadra con el de Yahoo (otra base: un ADR o un split sin
    # ajustar): la serie no mezcla las dos y se dice por qué.
    ed = _ed({"EarningsPerShareDiluted": {"units": {"USD/shares": [
        _f(*_FY26, 82.96, "2026-10-08"), _f("2024-09-02", "2025-08-31", 72.84, "2026-10-08")]}}})
    info = _info([None, 18.21, 16.56, 14.16, 13.14])
    log = edgar_backup.apply(info, ed)
    assert info["_statements_fy"]["diluted_eps"][0] is None
    assert any(x["field"] == "FY.diluted_eps" and "no cuadra" in x["reason"] for x in log["skipped"])


def test_fy_eps_without_edgar_for_that_year_stays_empty():
    ed = _ed({"EarningsPerShareDiluted": {"units": {"USD/shares": [
        _f("2024-09-02", "2025-08-31", 18.21, "2025-10-08", accn="k25")]}}})
    info = _info([None, 18.21, 16.56, 14.16, 13.14])
    edgar_backup.apply(info, ed)
    assert info["_statements_fy"]["diluted_eps"][0] is None


# ── PEG: un crecimiento que el informe muestra y nombra ──
# El PEG de COST (4,99) era el de Yahoo, con el crecimiento de consenso, que el informe no muestra. Regla general: el
# PEG es P/E ÷ el crecimiento del BPA del informe (el de su fila de Crecimiento, con su ventana); sin él, n.s. con motivo.

def _peg_na(a):
    c = a.get("classification") or {}
    return not_applicable(c.get("archetype"), "peg", c.get("subtype"))


def test_every_peg_shown_uses_the_eps_growth_of_the_report(outputs_by_env):
    for env in ("panel", "local"):
        for s, (a, _pdf) in outputs_by_env(env).items():
            peg, pb = (a.get("key_metrics") or {}).get("peg"), a.get("peg_basis") or {}
            if peg is None or pb.get("bound") or _peg_na(a):
                continue
            assert pb.get("own") and pb.get("eps_cagr_3y"), (env, s, pb)
            # F14 · paso 9: con el BPA más de 10 pp por encima de las ventas, el crecimiento acotado (growth_used)
            assert peg == pytest.approx(pb["pe"] / ((pb.get("growth_used") or pb["eps_cagr_3y"]) * 100)), (env, s)


def test_without_eps_growth_the_peg_is_not_significant_with_its_reason(outputs_by_env):
    for env in ("panel", "local"):
        for s, (a, _pdf) in outputs_by_env(env).items():
            pb = a.get("peg_basis") or {}
            if _peg_na(a) or (a.get("key_metrics") or {}).get("peg") is not None or pb.get("pe") is None:
                continue          # con P/E ≤ 0 (pérdidas) también n.s.: no cuenta como componente ausente
            ns = ((a.get("score_coverage") or {}).get("valoracion") or {}).get("not_significant") or {}
            assert ns.get("PEG"), (env, s, pb)


# ── Hallazgo 4: un limitador que apunta en la dirección del veredicto no contrae el precio ──
# La metodología decía «contraído hacia 50 según la confianza» y COST, con confianza media, no se contraía. La regla que
# ya se aplica: solo contraen los limitadores que contradicen el veredicto o lo vuelven incierto. El escalón de las tasas
# base apunta a «caro» (el precio exige un crecimiento que casi ninguna comparable sostuvo): no contrae un precio por
# debajo de 50 —lo acercaría a 50, más atractivo— y sí uno por encima, al que contradice.

def _cats(score):
    return [{"category": "Valoración", "score": score, "conclusive": True, "applicable": True}]


def _conf(level, basis, step=True):
    return {"level": level, "contraction_basis": basis,
            "base_rate_step": {"share": 0.01, "from": basis, "to": level} if step else None}


def test_base_rate_step_does_not_contract_an_expensive_price():
    from verdict import price_contraction_basis
    assert price_contraction_basis(_conf("media", "alta"), _cats(6)) == "alta"        # COST: precio 30, muy exigente


def test_base_rate_step_contracts_an_attractive_price():
    from verdict import price_contraction_basis
    assert price_contraction_basis(_conf("media", "alta"), _cats(14)) == "media"


def test_other_limiters_always_contract():
    from verdict import price_contraction_basis
    assert price_contraction_basis(_conf("media", "media", step=False), _cats(6)) == "media"
    assert price_contraction_basis(_conf("media", "media", step=False), _cats(14)) == "media"


def test_methodology_states_the_rule_on_web_and_pdf(outputs_by_env):
    a, pdf = outputs_by_env("panel")["AAPL"]
    # F16: la regla del precio es la L1 (P/E frente a la mediana de su grupo, por tercios); la confianza no lo mueve
    for txt in (a["display"]["summary"]["composition"]["caption"], a["display"]["methodology"]["contraction_text"]):
        assert "frente a la mediana de su grupo, situado por tercios" in txt and "la confianza no mueve el precio" in txt
    import pdf_inspect
    assert "situado por tercios" in " ".join(" ".join(pdf_inspect.page_texts(pdf)).split())
    import pdf_v2.methodology as m2
    txt2 = " ".join(getattr(x, "text", "") for x in m2.methodology(a, {}))
    assert "situado por tercios" in txt2 and "contradicen el veredicto" not in txt2


# ── Hallazgo 6: menores ──

def test_one_dcf_figure_in_the_whole_report(outputs_by_env):
    """COST: «$470» en el valor justo y «$468» en la alerta y en la casilla base de la sensibilidad. Una sola cifra: el
    redondeo del valor estimado (numfmt.estimate, F8 · P3) en todas partes."""
    seen = 0
    for env in ("panel", "local"):
        for s, (a, _pdf) in outputs_by_env(env).items():
            fv = (a.get("dcf") or {}).get("fair_value")
            if fv is None:
                continue
            if not a.get("display"):
                continue
            # la cifra de la fila del valor justo (con la moneda de la cotización)
            want = next(r["value"] for r in a["display"]["sections"]["valuation"]["intrinsic"]["rows"]
                        if r["key"] == "dcf_fair_value")
            sens = (a["display"]["sections"]["valuation"].get("sensitivity") or {})
            base = [c["value"] for r in sens.get("rows") or [] for c in r["cells"] if c.get("base")]
            assert base in ([], [want]), (env, s, base, want)
            for grp in a["display"]["sections"]["alerts"]["groups"]:
                for it in grp["items"]:
                    if it.get("category") == "Valor intrínseco" or "DCF" in (it.get("title") or ""):
                        seen += 1
                        assert want in it["detail"] or "DCF" not in it["detail"], (env, s, it["detail"], want)
    assert seen


def test_solidity_summary_does_not_open_with_an_altman_that_does_not_score(outputs_by_env):
    """COST: el capítulo Riesgos abría con «Altman Z de 2.86 (zona segura)» con el Altman referencial (no puntúa en su
    industria). Va como referencia, coherente con su fila; con el Altman que puntúa, como antes."""
    seen = 0
    for env in ("panel", "local"):
        for s, (a, _pdf) in outputs_by_env(env).items():
            if not a.get("display"):
                continue
            sol = dict((x["label"], x["text"]) for x in a["display"]["summary"]["exec_items"]).get("SOLIDEZ") or ""
            if "Altman" not in sol:
                continue
            if (a.get("business_model") or {}).get("altman_referential"):
                seen += 1
                assert not sol.startswith("Altman") and "solo como referencia: no puntúa" in sol, (env, s, sol)
            else:
                assert sol.startswith("Altman"), (env, s, sol)
    assert seen, "ningún Altman referencial en los fixtures"


def test_margin_of_safety_beyond_100_is_shown_bounded_with_the_exact_figure_in_the_detail(outputs_by_env):
    """COST: «−116 %» de margen de seguridad, una precisión que no dice nada más que «el precio pasa del doble del
    valor». Fuera de ±100 % la cifra es «< −100%» (o «> +100%») y la exacta va en el detalle."""
    lo, hi = cfg("thresholds.dcf_display.margin_of_safety_shown_bounds")
    seen = 0
    for env in ("panel", "local"):
        for s, (a, _pdf) in outputs_by_env(env).items():
            mos = (a.get("dcf") or {}).get("margin_of_safety")
            if not a.get("display"):
                continue
            row = next((r for r in a["display"]["sections"]["valuation"]["intrinsic"]["rows"]
                        if r["key"] == "margin_of_safety"), None)
            if mos is None or row is None or row["state"] != "con_dato":
                continue
            exact = f"{round(mos * 100):.0f}%".replace("-", "−")
            if mos < lo:
                seen += 1
                assert row["value"] == "< −100%" and exact in (row["text"] or ""), (env, s, row)
            elif mos > hi:
                assert row["value"] == "> +100%" and exact in (row["text"] or ""), (env, s, row)
            else:
                assert row["value"] == exact, (env, s, row)
    assert seen
