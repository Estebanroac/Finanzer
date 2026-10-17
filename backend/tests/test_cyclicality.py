"""Fase 3 (T2, D4): ciclicidad y crecimiento rentable medidos con la historia de EDGAR; subtipo financiero; ajuste de
splits y errores de escala de la historia por acción."""
import cyclicality as cy
import sec_edgar
from classify import CYCLICAL, FINANCIAL, GROWTH_PROFITABLE, MATURE, classify


def H(revenue, eps=None, shares=None, ni=None, disc=None, contract=None, oi=None, first=2010):
    """Historia sintética como la de sec_edgar.history: listas del ejercicio más antiguo al más reciente."""
    def f(vals):
        return {"values": [{"fy_end": f"{first + i}-12-31", "value": v} for i, v in enumerate(vals or [])
                           if v is not None]}
    return {"revenue": f(revenue), "diluted_eps": f(eps), "diluted_shares": f(shares), "net_income": f(ni),
            "discontinued": f(disc), "contract_revenue": f(contract), "operating_income": f(oi)}


# Ciclo repetido (tipo XOM/CAT): caídas de ingresos en 2012, 2015–16 y 2020 con el BPA hundido.
CYCLE = H([100, 110, 85, 95, 100, 80, 70, 90, 105, 75, 95, 110],
          eps=[5, 6, 2, 4, 5, 1.5, -1, 3, 5, 0.5, 4, 6])
# Crecimiento estable con un cargo puntual (tipo PG/JNJ): el BPA cae sin caída de ventas.
STEADY = H([100, 104, 108, 112, 117, 121, 126, 131, 136, 142, 148, 154],
           eps=[5, 5.2, 5.4, 1.5, 5.8, 6, 6.2, 6.5, 2.0, 7, 7.3, 7.6])
# Reestructuración única (tipo KO, refranquicia): un episodio, sin desplomes del BPA.
RESTRUCT = H([100, 102, 104, 106, 108, 95, 84, 76, 78, 82, 86, 90],
             eps=[2, 2.1, 2.2, 2.3, 2.4, 2.3, 2.2, 2.1, 2.3, 2.4, 2.5, 2.6])


def test_repeated_cycle_is_cyclical():
    r = cy.classify_history(CYCLE)
    assert r["enough"] and r["cyclical"]
    assert set(r["triggers"]) == {"caidas_de_ingresos_repetidas", "desplomes_del_bpa_con_caida_de_ingresos"}
    assert [ep[0][:4] for ep in r["measures"]["decline_episodes"]] == ["2012", "2015", "2019"]


def test_one_off_charges_are_not_a_cycle():
    r = cy.classify_history(STEADY)
    assert r["enough"] and not r["cyclical"]
    assert r["measures"]["design"]["eps_shock_years"]          # el diseño original los contaba
    assert r["measures"]["eps_collapse_with_decline"] == []


def test_single_restructuring_is_not_a_cycle():
    r = cy.classify_history(RESTRUCT)
    assert len(r["measures"]["decline_episodes"]) == 1 and not r["cyclical"]


def test_short_history_does_not_decide():
    r = cy.classify_history(H([100, 80, 100, 70, 100]))
    assert not r["enough"] and not r["cyclical"]


def test_perimeter_years_cut_the_series():
    # Escisión material en 2015 (operaciones discontinuadas ≥ 10% del beneficio): la caída de ese año no cuenta.
    h = H([100, 110, 85, 95, 100, 60, 62, 64, 66, 68, 70, 72],
          eps=[5, 6, 2, 4, 5, 1, 4, 4.2, 4.4, 4.6, 4.8, 5],
          ni=[10] * 12, disc=[None] * 5 + [8] + [None] * 6)
    m = cy.measure(h)
    assert m["perimeter_years"] == ["2015-12-31"]
    assert [ep[0][:4] for ep in m["decline_episodes"]] == ["2012"]


def test_per_share_basis_when_shares_grow():
    # Las acciones crecen un 10% anual: los ingresos agregados no caen, por acción sí.
    rev = [100 * 1.05 ** i for i in range(12)]
    sh = [10 * 1.10 ** i for i in range(12)]
    m = cy.measure(H(rev, shares=sh))
    assert m["basis"] == "por_accion"


def test_growth_profitable_measures_per_share():
    rev = [100 * 1.25 ** i for i in range(8)]
    sh = [10 * 1.02 ** i for i in range(8)]
    g = cy.growth_profitable_measures(H(rev, shares=sh))
    assert g["basis"] == "por_accion"
    assert abs(g["revenue_ps_cagr_3y"] - (1.25 / 1.02 - 1)) < 1e-9


def _cls(industry, history, eps=1.0, om=0.25, sector="Technology", fcf_sbc=None):
    return classify(sector=sector, industry=industry, eps_ttm=eps, net_margin_ttm=0.1, statements_fy={},
                    history=history, operating_margin_ttm=om, fcf_sbc_margin=fcf_sbc)


def test_history_overrides_industry_both_ways():
    # Industria de lista cíclica sin ciclo en 12 ejercicios: no es cíclica.
    c = _cls("Oil & Gas Integrated", STEADY, om=0.05, sector="Energy")
    assert c["archetype"] == MATURE and c["confidence"] == "normal" and not c["alerts"]
    # Industria no cíclica con un ciclo repetido: cíclica por su historia.
    c = _cls("Household & Personal Products", CYCLE, om=0.05, sector="Consumer Defensive")
    assert c["archetype"] == CYCLICAL and c["rule"] == "historia_ciclica"


def test_short_history_falls_back_to_industry_with_low_confidence():
    c = _cls("Oil & Gas Integrated", H([100, 90, 95, 100, 105]), sector="Energy")
    assert c["archetype"] == CYCLICAL and c["rule"] == "industria_ciclica" and c["confidence"] == "baja"
    assert "historia corta" in c["reason"]


def test_growth_profitable_rule_and_frontier():
    rev = [100 * 1.25 ** i for i in range(12)]
    sh = [10.0] * 12
    h = H(rev, eps=[1 + i for i in range(12)], shares=sh)
    c = _cls("Software - Infrastructure", h, om=0.30)
    assert c["archetype"] == GROWTH_PROFITABLE and c["confidence"] == "normal" and not c["frontier"]
    # Sin beneficio no es crecimiento rentable.
    assert _cls("Software - Infrastructure", h, eps=-0.5, om=0.30)["archetype"] != GROWTH_PROFITABLE
    # Margen operativo bajo, pero FCF − SBC suficiente: vale como margen.
    c = _cls("Software - Infrastructure", h, om=0.02, fcf_sbc=0.20)
    assert c["archetype"] == GROWTH_PROFITABLE and c["inputs"]["growth_profitable"]["margin_used"] == "FCF − SBC"
    # 16% a 3 años: a ±20% del umbral (15%) cambia → frontera, confianza baja.
    rev = [100 * 1.16 ** i for i in range(12)]
    c = _cls("Software - Infrastructure", H(rev, eps=[1 + i for i in range(12)], shares=sh), om=0.30)
    assert c["archetype"] == GROWTH_PROFITABLE and c["confidence"] == "baja"
    assert any(f.startswith("min_revenue_ps_cagr_3y") for f in c["frontier"])


def test_insurer_subtypes():
    ins = H([100] * 10, contract=[5] * 10)
    c = _cls("Insurance - Property & Casualty", ins, sector="Financial Services")
    assert c["archetype"] == FINANCIAL and c["subtype"] == "aseguradora"
    conglo = H([100] * 10, contract=[70] * 10)
    c = _cls("Insurance - Diversified", conglo, sector="Financial Services")
    assert c["subtype"] == "conglomerado" and c["subtype_label"] == "Conglomerado"
    assert _cls("Banks - Diversified", None, sector="Financial Services")["subtype"] == "banco"


# ── sec_edgar: splits y errores de escala de la historia por acción ──

def _facts(shares, eps):
    """companyfacts mínimo: Assets para la taxonomía y la moneda; acciones y BPA con sus filings."""
    return {"facts": {"us-gaap": {
        "Assets": {"units": {"USD": [{"end": "2021-12-31", "val": 1, "form": "10-K", "filed": "2022-02-01"}]}},
        "WeightedAverageNumberOfDilutedSharesOutstanding": {"units": {"shares": shares}},
        "EarningsPerShareDiluted": {"units": {"USD/shares": eps}}}}}


def _f(y, val, filed):
    return {"start": f"{y}-01-01", "end": f"{y}-12-31", "val": val, "form": "10-K", "filed": filed}


def test_split_adjusts_unrestated_years():
    # 4:1 en 2021: el 10-K de 2021 reexpresa 2019–2021; 2017–2018 quedan con la cifra de su informe.
    shares = [_f(2017, 100, "2018-02-01"), _f(2018, 100, "2019-02-01"), _f(2019, 100, "2020-02-01"),
              _f(2020, 100, "2021-02-01"),
              _f(2019, 400, "2022-02-01"), _f(2020, 400, "2022-02-01"), _f(2021, 400, "2022-02-01")]
    eps = [_f(2017, 8.0, "2018-02-01"), _f(2018, 8.0, "2019-02-01"), _f(2019, 8.0, "2020-02-01"),
           _f(2020, 8.0, "2021-02-01"),
           _f(2019, 2.0, "2022-02-01"), _f(2020, 2.0, "2022-02-01"), _f(2021, 2.0, "2022-02-01")]
    fx = _facts(shares, eps)
    sh = {v["fy_end"][:4]: v["value"] for v in sec_edgar.annual_history(fx, "diluted_shares")["values"]}
    ep = {v["fy_end"][:4]: v["value"] for v in sec_edgar.annual_history(fx, "diluted_eps")["values"]}
    assert sh == {"2017": 400, "2018": 400, "2019": 400, "2020": 400, "2021": 400}
    assert ep == {"2017": 2.0, "2018": 2.0, "2019": 2.0, "2020": 2.0, "2021": 2.0}


def test_eps_restatement_is_not_a_split():
    # El BPA de 2019 se reexpresa ×1.5 (cambio contable) sin cambio en las acciones: no es un split.
    shares = [_f(y, 100, f"{y + 1}-02-01") for y in (2019, 2020, 2021)]
    eps = [_f(2019, 2.0, "2020-02-01"), _f(2020, 2.0, "2021-02-01"), _f(2019, 3.0, "2021-02-01"),
           _f(2021, 2.0, "2022-02-01")]
    ep = {v["fy_end"][:4]: v["value"] for v in sec_edgar.annual_history(_facts(shares, eps), "diluted_eps")["values"]}
    assert ep == {"2019": 3.0, "2020": 2.0, "2021": 2.0}


def test_scale_error_is_dropped():
    # Acciones de 2018 en miles (1,000 veces menos): se descartan y se declaran.
    shares = [_f(2018, 0.1, "2019-02-01"), _f(2019, 100, "2020-02-01"), _f(2020, 101, "2021-02-01"),
              _f(2021, 102, "2022-02-01")]
    h = sec_edgar.annual_history(_facts(shares, []), "diluted_shares")
    assert [v["fy_end"][:4] for v in h["values"]] == ["2021", "2020", "2019"]
    assert h["dropped_scale_errors"] == ["2018-12-31"]


def test_cyclical_with_structural_growth_keeps_cyclical():
    # §1.1 paso 6: cíclica que además crece con beneficio → CYCLICAL con la nota de crecimiento estructural.
    rev = [100, 130, 95, 140, 190, 150, 120, 200, 280, 220, 330, 480]
    h = H(rev, eps=[2, 4, 0.5, 4, 7, 3, -1, 6, 10, 2, 12, 20], shares=[10.0] * 12)
    c = _cls("Semiconductors", h, om=0.35)
    assert c["archetype"] == CYCLICAL and c["structural_growth"] and "crecimiento estructural" in c["reason"]


def test_share_break_cuts_the_per_share_series():
    # Salida a bolsa con conversión de preferentes (tipo PLTR): las acciones medias saltan ×1.7 y ×2; los ingresos
    # por acción a través del salto no son comparables. La serie por acción empieza en la última ruptura.
    rev = [595, 743, 1093, 1542, 1906, 2225, 2866, 4475]
    sh = [544, 577, 979, 1924, 2064, 2298, 2451, 2565]
    h = H(rev, eps=[-1, -1, -1, -0.3, -0.2, 0.1, 0.2, 0.6], shares=sh, first=2018)
    assert cy.share_breaks(h, 0.5) == ["2020-12-31", "2021-12-31"]
    g = cy.growth_profitable_measures(h)
    assert g["share_break"] == "2021-12-31" and g["revenue_ps_cagr_5y"] is None
    assert abs(g["revenue_ps_cagr_3y"] - ((4475 / 2565) / (1906 / 2064)) ** (1 / 3) + 1) < 1e-9
    m = cy.measure(h)
    assert m["basis"] == "por_accion" and m["decline_episodes"] == []      # sin la falsa caída de 2020–21
