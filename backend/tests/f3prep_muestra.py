"""
Preparación de la fase 3: muestra del DCF inverso y del ROTE implícito sobre el panel, en replay (sin red).

    cd finanzer_next/backend
    ../.venv313/bin/python tests/f3prep_muestra.py > /tmp/muestra.md

Solo documentación para el planificador (docs/fiabilidad/F3PREP_MUESTRA.md): no cambia el motor. Por ticker toma
del análisis las entradas del DCF directo (FCF base, acciones, WACC, deuda neta) y calcula:
  · g*: crecimiento anual del FCF por acción que exige el precio (lib/reverse_dcf.py, estructura "step");
  · la banda frente al CAGR del FCF a 3 años que ya calcula el motor (la fila "Crecimiento FCF…" de Crecimiento:
    por acción si aplica su regla de dilución o en REIT, FCF − SBC en pre-beneficio; las cíclicas no la tienen);
  · g del DCF directo en estructura "step": el g* que devuelve el valor razonable del motor (para ver cuánto
    cambia su crecimiento cuando el motor usa decaimiento lineal o exponencial);
  · g* con base FCF − SBC (F3_DISENO §2.2) donde la base del DCF es el FCF TTM;
  · en bancos y aseguradoras, ROTE y ROE implícitos frente a los del motor, con la sensibilidad de ±2 pp.
"""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_backend as fb  # noqa: E402
from bank_implied import implied_roe, implied_rote, rote_sensitivity  # noqa: E402
from financial_ratios import dcf_multi_stage_dynamic  # noqa: E402
from reverse_dcf import classify_implied_growth, implied_growth  # noqa: E402


def pct(x, d=1):
    return "—" if x is None else f"{x * 100:+.{d}f}%"


def run(sym):
    with fb.replay(fb.fixtures_dir(fb.PANEL_ENV)) as store:
        store.load(sym)
        try:
            a = fb.run_analysis(sym, store)
        except Exception as e:   # SPY: el motor lo rechaza (422, ETF)
            return {"rejected": str(getattr(e, "status_code", e))}
    return json.loads(json.dumps(a, default=str))


def fcf_cagr(a):
    for adj in ((a.get("score") or {}).get("breakdown") or {}).get("Crecimiento", {}).get("adjustments", []):
        if (adj.get("metric") or "").startswith("Crecimiento FCF"):   # 3Y, por acción 3Y o − SBC 3Y
            return adj.get("raw"), adj.get("reason")
    return None, "sin fila Crecimiento FCF 3Y en el score"


def main():
    logging.disable(logging.CRITICAL)
    rows, banks = [], []
    for t in fb.env_tickers(fb.PANEL_ENV):
        a = run(t)
        if a.get("rejected"):
            rows.append(f"| {t} | — | — | — | — | — | — | rechazado por el motor ({a['rejected']}) | — | — | — | — | — |")
            continue
        arch = a["classification"]["archetype"]
        km, d, st = a.get("key_metrics") or {}, a.get("dcf") or {}, a.get("dcf_status") or {}
        price, shares = a.get("price"), km.get("shares_outstanding")
        if arch == "FINANCIAL":
            banks.append((t, a))
            continue
        motor_dcf = d.get("fcf_input") is not None
        fcf = d.get("fcf_input") if motor_dcf else km.get("free_cash_flow")
        wacc = d.get("wacc") if motor_dcf else (a.get("wacc") or {}).get("value")
        nd = km.get("net_debt") or 0.0
        fcf_ps, nd_ps = (fcf / shares if fcf is not None else None), nd / shares
        r = implied_growth(price, fcf_ps, wacc, net_debt_per_share=nd_ps)
        ach, ach_why = fcf_cagr(a)
        band = classify_implied_growth(r["g_star"], ach)["band"] if r["state"] == "ok" else "—"
        state = r["state"] + (f" ({r['side']})" if r["side"] else "")
        if motor_dcf:
            chk = dcf_multi_stage_dynamic(fcf=fcf, shares_outstanding=shares, wacc=wacc, total_debt=nd, cash=0.0,
                                          revenue_growth_3y=d["growth_rate"])
            assert chk["fair_value_per_share"] == d["fair_value"], (t, chk["fair_value_per_share"], d["fair_value"])
            eq = implied_growth(d["fair_value"], fcf_ps, wacc, net_debt_per_share=nd_ps)
            direct = f"{pct(d['growth_rate'])} {chk['decay_type']} → {pct(eq['g_star'])}"
            upside = f"{d['upside']:+.0f}%"
        else:
            direct, upside = f"no aplica ({st.get('state')})", "—"
        # Base FCF − SBC (§2.2) cuando la base del DCF es el FCF TTM al que el motor resta la SBC
        sbc = a.get("sbc") or {}
        if fcf is not None and sbc.get("fcf") == fcf and sbc.get("value") is not None:
            rs = implied_growth(price, sbc["value"] / shares, wacc, net_debt_per_share=nd_ps)
            g_sbc = f"{pct(rs['g_star'])} ({sbc['sbc_to_revenue']:.0%} de ingr.)" if rs["state"] == "ok" else rs["state"]
        else:
            g_sbc = "—"
        rows.append(f"| {t} | {arch} | {price:.2f} | {'—' if fcf_ps is None else f'{fcf_ps:.2f}'} | "
                    f"{pct(wacc, 2)} | {nd_ps:.2f} | **{pct(r['g_star'])}** | {state} | {pct(ach)} | {band} | "
                    f"{direct} | {upside} | {g_sbc} |")

    print("| Ticker | Arquetipo | Precio | FCF/acc. base | WACC | Deuda neta/acc. | g* | Estado | CAGR FCF 3a (motor) "
          "| Banda | g del DCF directo (decay → step) | Upside DCF directo | g* con FCF − SBC (SBC/ingresos) |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    print("\n".join(rows))
    print()
    print("| Ticker | Precio | Ke | g | P/TBV | ROTE motor | ROTE implícito | P/TBV justif. | ida y vuelta | "
          "P/B | ROE motor | ROE implícito | P/TBV con ROTE implícito −2 / −1 / +1 / +2 pp |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for t, a in banks:
        am = a["archetype_metrics"]
        ke, g = am["cost_of_equity"], am["terminal_growth"]
        ir, ie = implied_rote(am["ptbv"], ke, g), implied_roe(am["pb"], ke, g)
        back = implied_rote(am["ptbv_justified"], ke, g)["value"]
        ok = "exacta" if back is not None and abs(back - am["rote"]) < 1e-12 else f"{back}"
        sens = rote_sensitivity(am["ptbv"], ke, g)
        s = " / ".join(f"{row['ptbv_justified']:.2f}x" if row["ptbv_justified"] else "—"
                       for row in sens["rows"] if row["delta"] != 0)
        print(f"| {t} | {a['price']:.2f} | {pct(ke, 2)} | {pct(g)} | {am['ptbv']:.2f}x | {pct(am['rote'])} | "
              f"**{pct(ir['value'])}** | {am['ptbv_justified']:.2f}x | {ok} | {am['pb']:.2f}x | {pct(am['roe_fy'])} | "
              f"{pct(ie['value'])} | {s} |")


if __name__ == "__main__":
    main()
