# F13 · Paso 9b: el flujo que financia el crecimiento (opción b, decisión del usuario, 5-nov-2026)

El paso 9 midió tres formas de elegir el flujo del DCF de una empresa en expansión (`GOLDEN_DIFF_F13_P9.md`). El
usuario eligió la **(b)**: el flujo que financia el crecimiento, año a año.

## Qué cambia

- **El modelo del DCF** (`financial_ratios.dcf_multi_stage`, parámetro `reinvestment_roic`). El flujo de partida es el
  de mantenimiento: flujo operativo − D&A, sin pasar del capex real, − SBC. Cada año se descuenta ese flujo
  × (1 − g del año ÷ ROIC), que es la reinversión que exige el crecimiento (g = tasa de reinversión × ROIC). Al converger
  g al terminal, la reinversión baja.
- **La fase estable reinvierte g ÷ min(ROIC, WACC).** En el valor terminal, la inversión nueva rinde su coste de
  capital: ninguna ventaja competitiva dura para siempre (Damodaran). Con el ROIC también en el terminal, NVO (ROIC del
  36 %) reinvertía solo el 7 % y su DCF subía al +109 %; con el WACC, el 25 %.
- **Solo si crecer crea valor (ROIC > WACC).** Por debajo, el valor del DCF baja con g y la reinversión no tiene una
  lectura única: el inverso tendría dos soluciones o ninguna. TSLA (ROIC 5 % frente a un WACC del 11 %) y TM (4,5 %
  frente a 8,1 %) siguen con el flujo de hoy, y el DCF lo dice: «su ROIC no supera el coste del capital: crecer no crea
  valor…». Tampoco se aplica sin flujo de mantenimiento positivo (APD).
- **La misma estructura en todas partes:**
  - el DCF inverso (`reverse_dcf.equity_value_per_share` / `implied_growth`, `reverse_reading.reading`);
  - la tabla de sensibilidad (`dcf_sensitivity_analysis`);
  - el escenario del usuario (`scenario`: `base.reinvestment_roic`, `reverse.roic`, aceptados por la validación
    estricta de `/api/v2/scenario`).

  Con el mismo g, el directo y el inverso dan el mismo valor (test). Si ningún crecimiento llega al precio porque crecer
  destruye valor, el inverso lo dice («fuera de rango») en lugar de quedarse sin lectura.
- **Segunda lectura:** el FCF − SBC de hoy. En el directo, «con él, el valor sería X (Y %)»; en el inverso, «Con el
  flujo del periodo: …». El ROIC es el de `key_metrics`, el mismo del diferencial ROIC − WACC.

## Efecto en las 110 congeladas (paso 8 → 9b)

| Empresa | DCF con reinversión | Con el FCF de hoy | Inverso (crecimiento a 10 años) | Veredicto |
|---|---|---|---|---|
| META ★ | −12 % | −97 % | 16,9 %, muy exigente | muy exigente (media) → **exigente (baja)** |
| MSFT | −35 % | −67 % | 19,0 %, muy exigente | muy exigente → **exigente** (baja) |
| AMZN | −75 % | (FCF ≤ 0) | 29,1 %, muy exigente | muy exigente → **exigente** (baja) |
| LLY | −11 % | −48 % | 23,0 %, muy exigente | muy exigente → **exigente** (baja) |
| ORCL ★ | −14 % | (≤ 0) | 10,0 %, exigente | atractivo → **razonable** (media): antes el mantenimiento sin reinversión la daba por barata |
| TXN | −69 % | −63 % | 22,5 %, muy exigente | exigente; confianza media → baja (tasas base) |
| GOOGL | −47 % | (≤ 0) | 20,8 %, muy exigente | sin cambio de banda |
| WMT | −66 % | −79 % | 20,7 %, muy exigente | sin cambio |
| TSLA, APD | — | — | — | sin cambio: ROIC ≤ WACC (TSLA) o sin flujo de mantenimiento (APD) |

Bandas: 4 hacia barata y 1 hacia cara. Nadie pasa de exigente a barata: el inverso sigue diciendo que el precio exige
mucho crecimiento, y la confianza de META y TXN baja por las tasas base. Regla `flujo_por_intensidad`: 4 → **0**.

## Golden

Todos los análisis llevan los campos nuevos (`dcf` `inputs.reinvestment_roic`, `reverse_dcf.*.roic`, ambos null fuera
de expansión), así que se regeneran todos. Cambios de fondo en el panel:

| Empresa | Antes | Después |
|---|---|---|
| AMZN | DCF no significativo (FCF − SBC ≤ 0); muy exigente | DCF −74 %; **exigente** |
| MSFT | DCF −61 %; muy exigente | −39 %; **exigente** |
| TSM | DCF −32 %; exigente | −15 %; **razonable** |
| **NVO ⚠** | DCF +3 %; razonable (confianza baja) | **+83 %; atractivo (confianza media)** |
| TM | — | sin cambio de veredicto (ROIC < WACC: flujo de hoy) |

**NVO, el caso a vigilar.** ROIC del 36 % y crecimiento del 13,4 % (CAGR de ingresos de 3 años); su capex (≈ 13 B$,
5,5 veces la D&A) dobla lo que ese crecimiento exige a ese ROIC. El modelo lo lee así: su FCF de hoy (7,5 B$) está
hundido por una inversión mayor que la que necesita su crecimiento. Si el crecimiento futuro es menor que el de los
últimos 3 años, el valor también. Eso es el paso 11 (E7: crecimiento con ventas, BPA y tasa base), no este.

Tests:
- `tests/test_f13_paso9.py` (8);
- los ejemplos reales de dos tests pasan de MSFT a UL, que conserva la convergencia y la confianza media
  (`test_cost_of_capital`, `test_quality_price`);
- el del DCF no significativo, de AMZN a SNOW (`test_panel_cases`);
- el del escalón de las tasas base que no contrae, de MSFT a NVDA (`test_f10_n4`). Con el DCF nuevo, el precio de
  MSFT es «exigente» y el escalón lo contradice, así que sí contrae: es la regla de COST, ya existente.

Suite: 6672 passed.
