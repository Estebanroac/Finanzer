# 📖 Guía Rápida de Métricas

## Valoración

| Métrica | Fórmula | Bueno | Malo | Uso |
|---------|---------|-------|------|-----|
| **P/E** | Precio / EPS | <15 | >30 | Precio relativo a ganancias |
| **P/B** | Precio / Book Value | <1.5 | >4 | Precio vs activos netos |
| **P/S** | Precio / Ventas | <2 | >5 | Para empresas sin profit |
| **P/FCF** | Precio / FCF por acción | <15 | >30 | Más fiable que P/E |
| **EV/EBITDA** | Enterprise Value / EBITDA | <10 | >15 | Independiente de deuda |
| **PEG** | P/E / Growth Rate | <1 | >2 | P/E ajustado por crecimiento |
| **FCF Yield** | FCF / Market Cap | >7% | <3% | Rendimiento real de caja |

---

## Rentabilidad

| Métrica | Fórmula | Excelente | Bueno | Aceptable |
|---------|---------|-----------|-------|-----------|
| **ROE** | Net Income / Equity | >20% | 15-20% | 10-15% |
| **ROA** | Net Income / Assets | >10% | 6-10% | 3-6% |
| **ROIC** | NOPAT / Invested Capital | >15% | 10-15% | >WACC |
| **Margen Bruto** | Gross Profit / Revenue | >40% | 25-40% | 15-25% |
| **Margen Op.** | Operating Income / Revenue | >20% | 12-20% | 5-12% |
| **Margen Neto** | Net Income / Revenue | >15% | 8-15% | 3-8% |

---

## Liquidez

| Métrica | Fórmula | Bueno | Aceptable | Riesgo |
|---------|---------|-------|-----------|--------|
| **Current Ratio** | Current Assets / Current Liab | >2.0 | 1.2-2.0 | <1.0 |
| **Quick Ratio** | (CA - Inventory) / CL | >1.0 | 0.7-1.0 | <0.5 |
| **Cash Ratio** | Cash / Current Liabilities | >0.5 | 0.2-0.5 | <0.1 |

---

## Solvencia

| Métrica | Fórmula | Conservador | Normal | Alto |
|---------|---------|-------------|--------|------|
| **D/E** | Total Debt / Equity | <0.5 | 0.5-1.5 | >2.0 |
| **D/Assets** | Total Debt / Assets | <0.3 | 0.3-0.5 | >0.6 |
| **Net Debt/EBITDA** | (Debt-Cash) / EBITDA | <2.0 | 2-4 | >5.0 |
| **Interest Coverage** | EBIT / Interest Expense | >5x | 2-5x | <2x |

---

## Modelos Institucionales

### Altman Z-Score
```
Z = 1.2×(WC/TA) + 1.4×(RE/TA) + 3.3×(EBIT/TA) + 0.6×(MC/TL) + 1.0×(S/TA)

> 2.99  → Seguro
1.81-2.99 → Zona gris
< 1.81  → Peligro de bancarrota
```

### Piotroski F-Score (0-9)
```
8-9 → Excepcional (comprar)
6-7 → Bueno
4-5 → Neutral
0-3 → Débil (evitar)
```

### Graham Number
```
√(22.5 × EPS × Book Value)

Si Precio < Graham → Potencialmente barato
```

---

## Métricas para REITs

| Métrica | Fórmula | Bueno |
|---------|---------|-------|
| **FFO** | Net Income + Depreciation | Positivo creciente |
| **P/FFO** | Price / FFO per share | <15 |
| **FFO Payout** | Dividends / FFO | <85% |
| **AFFO** | FFO - CapEx recurrente | Positivo |

---

## Crecimiento

| Métrica | Alto | Moderado | Bajo |
|---------|------|----------|------|
| **Revenue CAGR 3Y** | >15% | 5-15% | <5% |
| **EPS CAGR 3Y** | >20% | 8-20% | <8% |
| **FCF CAGR 3Y** | >15% | 5-15% | <5% |

---

## Red Flags 🚩

- Z-Score < 1.81 (riesgo bancarrota)
- F-Score ≤ 3 (debilidad financiera)
- FCF negativo 3+ años consecutivos
- D/E > 3.0 sin ser financiera/utility
- Interest Coverage < 1.5x
- ROE negativo sin ser startup
- Dilución de acciones >5% anual
- Gross margin cayendo 3+ años
- Accruals > Net Income

---

## Green Flags ✅

- Z-Score > 3.0
- F-Score ≥ 8
- ROIC > WACC + 5%
- FCF/Net Income > 1.0 (5 años)
- D/E bajando y <1.0
- Dividend creciente 10+ años
- Buybacks consistentes
- ROE > 20% sostenido
- Margen mejorando
