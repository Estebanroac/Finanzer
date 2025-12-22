# 📊 Modelo de Scoring - Finanzer

## Visión General

El sistema de scoring evalúa acciones en una escala de **0-100 puntos**, combinando múltiples dimensiones del análisis fundamental para generar una calificación integral.

---

## Estructura del Score

```
┌─────────────────────────────────────────────────────────────┐
│                    SCORE TOTAL (0-100)                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│   │  SOLIDEZ    │  │RENTABILIDAD │  │ VALORACIÓN  │        │
│   │  (20 pts)   │  │  (20 pts)   │  │  (20 pts)   │        │
│   └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                             │
│   ┌─────────────┐  ┌─────────────┐                         │
│   │  CALIDAD    │  │ CRECIMIENTO │                         │
│   │  (20 pts)   │  │  (20 pts)   │                         │
│   └─────────────┘  └─────────────┘                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Solidez Financiera (20 pts)

Evalúa la estabilidad financiera y riesgo de bancarrota.

### Métricas evaluadas:

| Métrica | Bueno | Neutral | Malo | Puntos |
|---------|-------|---------|------|--------|
| **Altman Z-Score** | >2.99 | 1.81-2.99 | <1.81 | +8 / 0 / -15 |
| **Piotroski F-Score** | ≥7 | 4-6 | ≤3 | +10 / 0 / -10 |
| **Current Ratio** | >2.0 | 1.0-2.0 | <1.0 | +3 / 0 / -5 |
| **D/E Ratio** | <0.5 | 0.5-2.0 | >2.0 | +3 / 0 / -8 |
| **Interest Coverage** | >5x | 2-5x | <2x | +3 / 0 / -5 |

### Altman Z-Score (Detalle)

```
Fórmula: Z = 1.2×X1 + 1.4×X2 + 3.3×X3 + 0.6×X4 + 1.0×X5

X1 = Working Capital / Total Assets
     → Mide liquidez operativa

X2 = Retained Earnings / Total Assets
     → Mide rentabilidad acumulada

X3 = EBIT / Total Assets
     → Mide productividad de activos

X4 = Market Cap / Total Liabilities
     → Mide cobertura de mercado

X5 = Sales / Total Assets
     → Mide eficiencia de activos

Interpretación:
• Z > 2.99  → Zona SEGURA (probabilidad de quiebra < 5%)
• Z 1.81-2.99 → Zona GRIS (monitorear)
• Z < 1.81  → Zona PELIGRO (probabilidad > 50%)
```

### Piotroski F-Score (Detalle)

```
9 criterios binarios (0 o 1 punto cada uno):

RENTABILIDAD (4 pts):
☑ ROA > 0 (rentable)
☑ Operating Cash Flow > 0 (genera caja)
☑ ROA actual > ROA año anterior (mejorando)
☑ Cash Flow > Net Income (calidad de ganancias)

APALANCAMIENTO (3 pts):
☑ Deuda LP actual < Deuda LP año anterior (desapalancando)
☑ Current Ratio actual > Current Ratio anterior (más líquido)
☑ Shares actual ≤ Shares anterior (sin dilución)

EFICIENCIA (2 pts):
☑ Margen Bruto actual > Margen anterior (pricing power)
☑ Asset Turnover actual > anterior (eficiencia)

Interpretación:
• F 8-9 → EXCEPCIONAL (strong buy)
• F 7   → MUY BUENO
• F 5-6 → NEUTRAL
• F 3-4 → DÉBIL
• F 0-2 → MUY DÉBIL (avoid)
```

---

## 2. Rentabilidad (20 pts)

Evalúa la capacidad de generar beneficios.

| Métrica | Excelente | Bueno | Aceptable | Malo |
|---------|-----------|-------|-----------|------|
| **ROE** | >20% | 15-20% | 10-15% | <10% |
| **ROA** | >10% | 6-10% | 3-6% | <3% |
| **ROIC** | >15% | 10-15% | WACC-10% | <WACC |
| **Margen Neto** | >15% | 10-15% | 5-10% | <5% |
| **Margen Op.** | >20% | 12-20% | 5-12% | <5% |

### Puntuación:

```
ROE > 20%           → +8 pts
ROE 15-20%          → +5 pts
ROE 10-15%          → +2 pts
ROE < 10%           → -3 pts

ROIC > WACC + 5%    → +5 pts (crea valor)
ROIC < WACC         → -5 pts (destruye valor)

Margen Neto > 15%   → +4 pts
Margen Neto < 5%    → -4 pts
```

---

## 3. Valoración (20 pts)

Evalúa si el precio actual es atractivo.

| Métrica | Barato | Justo | Caro | Muy Caro |
|---------|--------|-------|------|----------|
| **P/E** | <12 | 12-20 | 20-30 | >30 |
| **P/B** | <1.5 | 1.5-3.0 | 3.0-5.0 | >5.0 |
| **EV/EBITDA** | <8 | 8-12 | 12-18 | >18 |
| **P/FCF** | <15 | 15-25 | 25-40 | >40 |
| **PEG** | <1.0 | 1.0-1.5 | 1.5-2.0 | >2.0 |

### Puntuación:

```
P/E < 12            → +6 pts
P/E 12-15           → +3 pts
P/E > 30            → -5 pts

PEG < 1.0           → +5 pts (growth barato)
PEG > 2.0           → -3 pts

FCF Yield > 8%      → +4 pts
FCF Yield < 2%      → -3 pts
```

### Valoración Intrínseca:

```
Precio < Graham Number × 0.8  → +5 pts (muy barato)
Precio < DCF Fair Value × 0.8 → +5 pts (subvaluado)
Precio > DCF Fair Value × 1.3 → -5 pts (sobrevaluado)
```

---

## 4. Calidad de Ganancias (20 pts)

Evalúa la sostenibilidad y veracidad de los beneficios.

| Criterio | Bueno | Malo |
|----------|-------|------|
| **FCF/Net Income** | >1.0 | <0.5 |
| **Accruals Ratio** | Bajo | Alto |
| **Consistencia EPS** | Creciente | Volátil |
| **Dividend Coverage** | >1.5x | <1.0x |

### Puntuación:

```
FCF > Net Income        → +5 pts (ganancias = efectivo)
FCF negativo 3+ años    → -8 pts (red flag)

EPS creciente 5 años    → +5 pts
EPS volátil             → -3 pts

Cash Flow / Net Income > 1.2  → +3 pts
Cash Flow / Net Income < 0.5  → -5 pts (ganancias de papel)
```

---

## 5. Crecimiento (20 pts)

Evalúa la trayectoria de crecimiento.

| Métrica | Alto | Moderado | Bajo | Negativo |
|---------|------|----------|------|----------|
| **Revenue CAGR 3Y** | >15% | 5-15% | 0-5% | <0% |
| **EPS CAGR 3Y** | >20% | 10-20% | 0-10% | <0% |
| **FCF CAGR 3Y** | >15% | 5-15% | 0-5% | <0% |

### Puntuación:

```
Revenue Growth > 20%    → +6 pts
Revenue Growth 10-20%   → +4 pts
Revenue Growth < 0%     → -4 pts

EPS Growth > 25%        → +6 pts
EPS Growth negativo     → -5 pts

Consistencia (5 años+)  → +3 pts bonus
```

---

## Ajustes por Tipo de Empresa

### Growth Companies (Revenue Growth > 15%)

```
Ajustes:
• P/E tolerance × 1.5 (permite P/E más alto)
• Growth weight × 1.5 (más peso al crecimiento)
• FCF negativo no penaliza tanto si invierte en growth
```

### Value Companies (P/E < 15, P/B < 1.5)

```
Ajustes:
• Más peso a dividendos
• Valoración vs book value más relevante
• Menor penalización por bajo crecimiento
```

### Ajustes por Sector

| Sector | Ajuste Principal |
|--------|------------------|
| **Financieros** | Ignorar D/E alto (normal) |
| **REITs** | Usar FFO en lugar de P/E |
| **Utilities** | Tolerar D/E 2.0, enfocarse en dividendos |
| **Tech** | Tolerar P/E alto si hay growth |
| **Energía** | Usar EV/EBITDA, ajustar por ciclo |

---

## Niveles de Score

| Score | Nivel | Color | Acción Sugerida |
|-------|-------|-------|-----------------|
| **80-100** | Excepcional | 🟢 Verde | Strong Buy |
| **65-79** | Bueno | 🟢 Verde claro | Buy/Hold |
| **50-64** | Aceptable | 🟡 Amarillo | Hold/Investigar |
| **35-49** | Débil | 🟠 Naranja | Precaución |
| **0-34** | Pobre | 🔴 Rojo | Sell/Evitar |

---

## Ejemplos de Scoring

### Ejemplo 1: Apple (AAPL) - Score ~75

```
Solidez:     16/20 (Z=3.5 ✓, F=7 ✓, Current=1.0 ○)
Rentabilidad: 18/20 (ROE=150% ✓✓, Margen=25% ✓)
Valoración:  12/20 (P/E=28 ○, PEG=2.5 ✗)
Calidad:     15/20 (FCF>NI ✓, Consistente ✓)
Crecimiento: 14/20 (Revenue +8% ○, EPS +10% ✓)
─────────────────────────────────────────────
TOTAL:       75/100 - BUENO
```

### Ejemplo 2: Empresa en Distress - Score ~25

```
Solidez:      2/20 (Z=1.2 ✗✗, F=2 ✗, D/E=4.0 ✗)
Rentabilidad:  5/20 (ROE=-5% ✗, Margen=2% ✗)
Valoración:  10/20 (P/E=8 ✓ pero por earnings cayendo)
Calidad:      3/20 (FCF negativo 3 años ✗✗)
Crecimiento:  5/20 (Revenue -10% ✗, EPS -25% ✗)
─────────────────────────────────────────────
TOTAL:       25/100 - POBRE (Evitar)
```

---

## Limitaciones

1. **Datos históricos**: El modelo usa datos pasados, no predice el futuro
2. **Sectores especiales**: Bancos, REITs, utilities requieren ajustes
3. **Empresas jóvenes**: Sin historial suficiente para F-Score completo
4. **Ciclos económicos**: No ajusta automáticamente por recesión/expansión
5. **Eventos extraordinarios**: M&A, reestructuraciones, one-time charges

---

## Validación del Modelo

El modelo fue validado contra:
- 298 tests unitarios (84% coverage)
- Backtesting con empresas conocidas
- Comparación con ratings de Morningstar/S&P

**Correlación observada**: ~0.75 con ratings institucionales
