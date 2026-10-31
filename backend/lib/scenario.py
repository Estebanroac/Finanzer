"""Rediseño E2a: escenario del usuario con el mismo DCF por etapas del motor (financial_ratios.dcf_multi_stage). No
cambia el veredicto: es una herramienta de exploración, sin estado. Los supuestos se recortan a
config/valuation.toml [scenario]; con los supuestos base (los del análisis, scenario_inputs) da el mismo valor.

Rediseño E3 (Task 7): el margen de flujo de caja (FCF = ingresos × margen), los preajustes Pesimista / Optimista y los
límites de cada control (`extend`), "qué exige el precio" con los supuestos del usuario (el mismo DCF inverso del motor,
reverse_dcf.implied_growth, con su tasa y su terminal) y la tabla de sensibilidad 5 × 5 alrededor de sus supuestos
(los pasos de la del informe, [grid])."""
import math
from typing import Annotated, Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

import reverse_dcf as rd
from financial_ratios import dcf_multi_stage
from settings import cfg

_KEYS = ("high_growth_rate", "high_growth_years", "transition_years", "terminal_growth", "discount_rate")


# ── V6 (revisión de seguridad, B1/B4): lo que el cliente puede mandar. Sin claves de más, solo números finitos y dentro
# de [scenario] input_*; los años, dentro de years_min..years_max (con 2·10⁷ años el DCF tardaba ~40 s y ~800 MB). ──
_L = cfg("valuation.scenario")
_Strict = ConfigDict(extra="forbid", strict=True)


def _num(lo: float, hi: float):
    return Annotated[float, Field(ge=lo, le=hi, allow_inf_nan=False)]


_Amount = _num(-_L["input_amount_max"], _L["input_amount_max"])
_PerShare = _num(-_L["input_per_share_max"], _L["input_per_share_max"])
_Rate = _num(-_L["input_rate_max"], _L["input_rate_max"])
_Margin = _num(-_L["input_margin_max"], _L["input_margin_max"])
_Text = Annotated[str, Field(max_length=_L["input_text_max"])]
_HighYears = Annotated[int, Field(ge=_L["years_min"], le=_L["years_max"])]
_TransYears = Annotated[int, Field(ge=0, le=_L["years_max"])]


class _Base(BaseModel):
    model_config = _Strict
    high_growth_rate: _Rate
    high_growth_years: _HighYears
    transition_years: _TransYears
    terminal_growth: _Rate
    discount_rate: _Rate
    decay_type: Optional[Literal["step"]] = None


class _Bounds(BaseModel):
    model_config = _Strict
    growth: List[_Rate] = Field(max_length=2)
    discount: List[_Rate] = Field(max_length=2)
    terminal: List[_Rate] = Field(max_length=2)
    fcf_margin: Optional[List[_Margin]] = Field(default=None, max_length=2)


class _Preset(BaseModel):
    model_config = _Strict
    high_growth_rate: _Rate
    discount_rate: _Rate
    terminal_growth: _Rate
    fcf_margin: Optional[_Margin] = None


class _Presets(BaseModel):
    model_config = _Strict
    pessimistic: _Preset
    optimistic: _Preset


class _Reverse(BaseModel):
    model_config = _Strict
    flow_per_share: _PerShare
    net_debt_per_share: _PerShare
    rate: _Rate
    terminal_growth: _Rate


class _Inputs(BaseModel):
    model_config = _Strict
    status: Literal["ok", "sin_dato"] = "ok"
    reason: Optional[_Text] = None
    fcf: Optional[_Amount] = None
    shares_outstanding: Optional[Annotated[float, Field(gt=0, le=_L["input_shares_max"], allow_inf_nan=False)]] = None
    net_debt: Optional[_Amount] = None
    price: Optional[_num(0.0, _L["input_per_share_max"])] = None
    currency: Optional[_Text] = None
    base: Optional[_Base] = None
    revenue: Optional[_num(0.0, _L["input_amount_max"])] = None
    fcf_margin: Optional[_Margin] = None
    archetype: Optional[_Text] = None
    bounds: Optional[_Bounds] = None
    presets: Optional[_Presets] = None
    reverse: Optional[_Reverse] = None

    @model_validator(mode="after")
    def _per_share(self):
        """Unas acciones minúsculas disparan el valor por acción: las cifras entre las acciones, dentro del tope."""
        if self.shares_outstanding:
            for name in ("fcf", "net_debt", "revenue"):
                v = getattr(self, name)
                if v is not None and abs(v) / self.shares_outstanding > _L["input_per_share_max"]:
                    raise ValueError(f"{name} por acción fuera de rango")
        return self


class _Assumptions(BaseModel):
    model_config = _Strict
    high_growth_rate: Optional[_Rate] = None
    discount_rate: Optional[_Rate] = None
    terminal_growth: Optional[_Rate] = None
    fcf_margin: Optional[_Margin] = None
    high_growth_years: Optional[_HighYears] = None
    transition_years: Optional[_TransYears] = None


class _Request(BaseModel):
    model_config = _Strict
    inputs: _Inputs
    assumptions: Optional[_Assumptions] = None


class InvalidRequest(ValueError):
    """Cuerpo de /api/v2/scenario fuera de lo admitido: su mensaje (corto, sin eco del valor) va en el 422."""


def parse_request(body: Any):
    """(inputs, assumptions) validados para run(), o InvalidRequest. Las claves que el cliente no manda no aparecen."""
    try:
        req = _Request.model_validate(body)
    except ValidationError as e:
        errs = e.errors(include_url=False, include_input=False)
        where = "; ".join(f"{'.'.join(str(x) for x in er['loc'])}: {er['msg']}" for er in errs[:3])
        raise InvalidRequest(f"escenario no válido ({where})") from None
    inputs = req.inputs.model_dump(exclude_unset=True)
    if inputs.get("status", "ok") == "ok" and "base" not in inputs:
        raise InvalidRequest("faltan los supuestos base del análisis (scenario_inputs)")
    return inputs, (req.assumptions.model_dump(exclude_none=True) if req.assumptions else {})


def _finite(x: Optional[float]) -> Optional[float]:
    return x if x is not None and math.isfinite(x) else None


def _bounds(name: str, S: Dict[str, Any], disc: float):
    return {"high_growth_rate": (S["growth_min"], S["growth_max"]),
            "discount_rate": (S["discount_min"], S["discount_max"]),
            "terminal_growth": (S["terminal_min"], min(S["terminal_max"], disc - S["terminal_gap_min"])),
            "high_growth_years": (S["years_min"], S["years_max"]),
            "transition_years": (0, S["years_max"])}[name]


def _deltas(rng) -> List[float]:
    lo, hi, step = rng
    n = int(round((hi - lo) / step)) + 1
    return [lo + i * step for i in range(n)]


def extend(si: Dict[str, Any], revenue: Optional[float], archetype: Optional[str]) -> Dict[str, Any]:
    """Añade a scenario_inputs (status ok) los ingresos base, el margen de flujo de caja, el arquetipo, los límites de
    cada control y los preajustes (absolutos, dentro de los límites). Aditivo."""
    S = cfg("valuation.scenario")
    base = si["base"]
    margin = (si["fcf"] / revenue) if (revenue and si.get("fcf") is not None) else None
    disc = base["discount_rate"]
    bounds = {"growth": [S["growth_min"], S["growth_max"]], "discount": [S["discount_min"], S["discount_max"]],
              "terminal": [S["terminal_min"], S["terminal_max"]],
              "fcf_margin": (sorted([margin * S["margin_rel_min"], margin * S["margin_rel_max"]]) if margin else None)}
    P = (S["presets"].get(archetype or "") or S["presets"]["default"])
    presets = {}
    for side in ("pessimistic", "optimistic"):
        d = min(max(disc + P[side]["discount"], S["discount_min"]), S["discount_max"])
        t_hi = min(S["terminal_max"], d - S["terminal_gap_min"])
        presets[side] = {
            "high_growth_rate": min(max(base["high_growth_rate"] + P[side]["growth"], S["growth_min"]), S["growth_max"]),
            "discount_rate": d,
            "terminal_growth": min(max(base["terminal_growth"] + P[side]["terminal"], S["terminal_min"]), t_hi),
            "fcf_margin": margin}
    return {**si, "revenue": revenue, "fcf_margin": margin, "archetype": archetype, "bounds": bounds,
            "presets": presets}


def _implied(inputs: Dict[str, Any], fcf: float, used: Dict[str, Any]) -> Dict[str, Any]:
    """Qué crecimiento exige el precio con los supuestos del usuario: el DCF inverso del motor sobre su mismo flujo por
    acción (escalado si el usuario cambia el margen), con la tasa y el terminal del usuario."""
    rv = inputs.get("reverse") or {}
    fps = rv.get("flow_per_share")
    if fps is None or not inputs.get("fcf"):
        return {"state": "sin_dato", "g_star": None, "g10": None, "side": None,
                "reason": "el análisis no tiene DCF inverso con el que comparar"}
    r = rd.implied_growth(inputs.get("price"), fps * fcf / inputs["fcf"], used["discount_rate"],
                          terminal_growth=used["terminal_growth"], net_debt_per_share=rv.get("net_debt_per_share") or 0.0)
    g10 = rd.ten_year_cagr(r["g_star"], terminal_growth=used["terminal_growth"]) if r["state"] == rd.OK else None
    return {"state": r["state"], "g_star": _finite(r["g_star"]), "g10": _finite(g10), "side": r["side"],
            "reason": r["reason"]}


def _sensitivity(inputs: Dict[str, Any], fcf: float, used: Dict[str, Any], S: Dict[str, Any]) -> Dict[str, Any]:
    """Valor por acción con crecimiento (filas, de menos a más) y WACC (columnas) alrededor de los supuestos del
    usuario, con los pasos de la tabla del informe ([grid]); una celda fuera de los límites, o con valor ≤ 0, es None
    y su porqué va en `why` (V4b · 4: «fuera» o «≤ 0», para que la web no pinte un «—» sin motivo)."""
    G = cfg("valuation.grid")
    growth = [used["high_growth_rate"] + d for d in _deltas(G["growth_range"])]
    disc = [used["discount_rate"] + d for d in _deltas(G["discount_range"])]
    values, why = [], []
    for g in growth:
        row, row_why = [], []
        for d in disc:
            ok = (S["growth_min"] <= g <= S["growth_max"] and S["discount_min"] <= d <= S["discount_max"]
                  and used["terminal_growth"] <= d - S["terminal_gap_min"])
            r = dcf_multi_stage(fcf=fcf, shares_outstanding=inputs["shares_outstanding"], high_growth_rate=g,
                                high_growth_years=used["high_growth_years"], transition_years=used["transition_years"],
                                terminal_growth=used["terminal_growth"], discount_rate=d,
                                decay_type=inputs["base"].get("decay_type") or "step",
                                net_debt=inputs.get("net_debt")) if ok else {}
            fv = _finite(r.get("fair_value_per_share")) if r.get("is_valid") else None
            row.append(fv if fv is not None and fv > 0 else None)
            row_why.append(None if fv is not None and fv > 0 else ("fuera" if not ok else "≤ 0"))
        values.append(row)
        why.append(row_why)
    # Revisión V6 (F17): la banda de cada celda frente al precio, la misma regla que la sensibilidad del informe.
    from display import sensitivity_band, sensitivity_band_labels
    price = inputs.get("price")
    return {"growth": growth, "discount": disc, "values": values, "why": why, "price": price,
            "bands": [[sensitivity_band(v, price) for v in row] for row in values],
            "band_labels": sensitivity_band_labels()}


def run(inputs: Dict[str, Any], assumptions: Dict[str, Any]) -> Dict[str, Any]:
    if not inputs or inputs.get("status", "ok") != "ok" or not inputs.get("base"):
        return {"status": "sin_dato", "fair_value": None, "upside": None, "assumptions_used": None, "clamped": [],
                "implied_growth": None, "sensitivity": None,
                "reason": (inputs or {}).get("reason") or "sin supuestos base del análisis"}
    S = cfg("valuation.scenario")
    base = inputs["base"]
    used: Dict[str, Any] = {}
    clamped = []
    # la tasa de descuento primero: acota el crecimiento terminal
    for k in ("discount_rate",) + tuple(x for x in _KEYS if x != "discount_rate"):
        given = k in assumptions and assumptions[k] is not None
        raw = float(assumptions[k] if given else base[k])
        # V6 (B1): el supuesto base llega del cliente: se recorta como los del usuario. Los del motor ya están dentro
        # de los límites (lo comprueba un test sobre el panel): con ellos nada cambia.
        lo, hi = _bounds(k, S, used.get("discount_rate", raw))
        v = min(max(raw, lo), hi)
        if v != raw:
            clamped.append(k)
        used[k] = int(round(v)) if k.endswith("_years") else v
    # un terminal base que quede por encima del margen frente a una tasa de descuento nueva también se recorta
    t_hi = used["discount_rate"] - S["terminal_gap_min"]
    if "discount_rate" in assumptions and used["terminal_growth"] > t_hi:
        used["terminal_growth"] = t_hi
        clamped.append("terminal_growth")
    # Margen de flujo de caja (E3): FCF = ingresos × margen, dentro del rango de exploración del margen propio.
    fcf = inputs["fcf"]
    base_margin, revenue = inputs.get("fcf_margin"), inputs.get("revenue")
    if base_margin and revenue:
        m = base_margin
        if assumptions.get("fcf_margin") is not None:
            lo, hi = sorted([base_margin * S["margin_rel_min"], base_margin * S["margin_rel_max"]])
            raw = float(assumptions["fcf_margin"])
            m = min(max(raw, lo), hi)
            if m != raw:
                clamped.append("fcf_margin")
            fcf = revenue * m
        used["fcf_margin"] = m
    r = dcf_multi_stage(fcf=fcf, shares_outstanding=inputs["shares_outstanding"],
                        high_growth_rate=used["high_growth_rate"], high_growth_years=used["high_growth_years"],
                        transition_years=used["transition_years"], terminal_growth=used["terminal_growth"],
                        discount_rate=used["discount_rate"], decay_type=base.get("decay_type") or "step",
                        net_debt=inputs.get("net_debt"))
    fv = _finite(r.get("fair_value_per_share"))       # V6 (B1): nunca un infinito o un NaN en la respuesta
    implied = _implied(inputs, fcf, used)
    sens = _sensitivity(inputs, fcf, used, S)
    if not r.get("is_valid") or fv is None or fv <= 0:
        return {"status": "sin_dato", "fair_value": None, "upside": None, "assumptions_used": used,
                "clamped": sorted(set(clamped)), "implied_growth": implied, "sensitivity": sens,
                "reason": r.get("invalid_reason") or "el valor del capital no es positivo con estos supuestos"}
    price = inputs.get("price")
    upside = (fv / price - 1) if price else None
    # v4 (PM, color de las barras): la lectura del escenario con las mismas bandas que el DCF del informe
    # (thresholds.score.valoracion.dcf_upside_bounds): «Precio justo» no se pinta de rojo por ir un 0,5 % por debajo
    from display import read_upside
    _r = read_upside(upside * 100) if upside is not None else None
    return {"status": "ok", "fair_value": fv, "upside": upside,
            # el tono del resultado (por encima o por debajo del precio) también lo decide el motor
            "upside_tone": None if upside is None else "pos" if upside >= 0 else "neg",
            "upside_reading": {"label": _r[0], "tone": _r[1]} if _r else None,
            "assumptions_used": used, "clamped": sorted(set(clamped)), "implied_growth": implied,
            "sensitivity": sens, "reason": None}
