"""
Beneficio y patrimonio del accionista ordinario (fase 2b, T7; F2_PRECEDENCIA §2.1, fila "Beneficio neto").

El beneficio de los propietarios de la dominante incluye lo que cobran los instrumentos de patrimonio que no son
acciones ordinarias: los cupones AT1 de un banco IFRS (BCS: 7,172 − 6,175 = 997 millones de GBP en 2025, igual en
EDGAR: ProfitLossAttributableToOwnersOfParent frente a ...OrdinaryEquityHoldersOfParentEntity) y los dividendos
preferentes en EE. UU. (JPM, BAC). La precedencia manda que el beneficio neto sea el del ordinario ("el ROE y el BPA
usan el del ordinario"); la ruta quoteSummary ya lo hacía (`netIncomeToCommon`) y el plan B y el TTM no.

Patrimonio del ordinario = patrimonio de los propietarios − preferentes − AT1:
  · preferentes: Yahoo ya los resta en "Common Stock Equity" (JPM 362,438 − 20,045 = 342,393);
  · AT1: en un IFRS, Yahoo deja "Common Stock Equity" igual al patrimonio y lo da en "Other Equity Interest" (BCS
    12,725 = `ifrs-full:OtherEquityInterest` de EDGAR). Esa fila solo es AT1 si el emisor paga cupones a esos
    instrumentos (beneficio de los propietarios > del ordinario): en TM, SHEL o TSM es otra partida del patrimonio.
Lo usan el ROE y el valor contable por acción (P/B). El patrimonio total sigue en el D/E y el Altman (el AT1 es
capital). Las filas anuales del ordinario quedan en `_statements_fy` para el ROTE ajustado por AT1 de la fase 3.
"""
from typing import Any, Dict, Optional

# Diferencia mínima, relativa, para considerar que hay preferentes en el patrimonio (redondeos de la fuente).
_REL_TOL = 0.001


def apply(info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Fija info["netIncome"] (del ordinario) e info["commonEquity"]; devuelve el registro (-> data_provenance.ordinary)
    o None si la fuente no da el desglose del corte."""
    from yf_adapter import _tag_provenance
    src = info.get("_ordinary_src")
    ao = info.get("_as_of") or {}
    if not src or ao.get("type") not in ("ttm", "fy") or src.get("period_type") != ao.get("type"):
        return None
    cut = ao.get("date")
    fields = ao.get("fields") or {}
    out: Dict[str, Any] = {"period_end": cut, "period_type": ao["type"], "source": "Yahoo (estados de yfinance)",
                           "net_income_owners": None, "net_income_common": None, "distributions": None,
                           "equity_owners": None, "preferred": None, "at1": None, "equity_common": None, "notes": []}

    def same_cut(key):
        f = fields.get(key) or {}
        return info.get(key) is not None and f.get("period_end") == cut and f.get("source") != "sec_edgar"

    ni, nic = info.get("netIncome"), src.get("netIncomeToCommon")
    dist = 0.0
    if nic is not None and same_cut("netIncome"):
        dist = ni - nic
        out.update(net_income_owners=ni, net_income_common=nic, distributions=dist)
        if dist < 0:
            out["notes"].append("beneficio del ordinario mayor que el de los propietarios: no se aplica")
            dist = 0.0
        elif dist:
            info["netIncome"] = nic
            if info.get("_eps_net_income") == ni:
                info["_eps_net_income"] = nic
            _tag_provenance(info, "derivado",
                            f"beneficio atribuido al accionista ordinario: el de los propietarios ({ni:,.0f}) sin "
                            f"los cupones AT1 o dividendos preferentes ({dist:,.0f})", paths=["netIncome"],
                            overwrite=True)
    elif nic is None:
        out["notes"].append("la fuente no da el beneficio del ordinario del corte")
    se, cse, oei = info.get("totalStockholderEquity"), src.get("commonStockEquity"), src.get("otherEquityInterest")
    if se is None or not same_cut("totalStockholderEquity") or cse is None:
        out["notes"].append("sin el patrimonio del ordinario del corte en la fuente")
        info["_ordinary"] = out
        return out
    preferred = se - cse if se - cse > _REL_TOL * abs(se) else 0.0
    at1 = oei if (oei is not None and oei > 0 and dist > 0 and not preferred) else 0.0
    common = cse - at1
    out.update(equity_owners=se, preferred=preferred, at1=at1, equity_common=common)
    if abs(common - se) > _REL_TOL * abs(se):
        info["commonEquity"] = common
        parts = " y ".join(x for x in (f"preferentes {preferred:,.0f}" if preferred else None,
                                       f"AT1 {at1:,.0f}" if at1 else None) if x)
        _tag_provenance(info, "derivado", f"patrimonio del accionista ordinario: el de los propietarios ({se:,.0f}) "
                        f"sin {parts}", paths=["commonEquity"], overwrite=True)
        if info.get("_data_path") == "plan_b_yfinance" and info.get("bookValue") is not None:
            # El plan B lo calcula como patrimonio / acciones; la ruta quoteSummary trae el de Yahoo (ya del ordinario).
            info["bookValue"] = info["bookValue"] * common / se
            _tag_provenance(info, "derivado", "patrimonio del accionista ordinario / acciones", paths=["bookValue"],
                            overwrite=True)
    info["_ordinary"] = out
    return out
