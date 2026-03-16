# 🏗️ Arquitectura - Finanzer v3.0.0

## Visión General

Finanzer v3.0.0 introduce una arquitectura modular con separación clara de responsabilidades:

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE PRESENTACIÓN                     │
│                         (app.py)                            │
│   Dash/Plotly · Bootstrap · Layout · Orquestación           │
└─────────────────────────────────────────────────────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  callbacks/   │  │  components/  │  │   analysis/   │
│   search.py   │  │   charts.py   │  │   ratios.py   │
│   chart.py    │  │   cards.py    │  │  scoring.py   │
│ comparison.py │  │   tables.py   │  │   alerts.py   │
└───────────────┘  │ sensitivity.py│  │  sectors.py   │
        │          │   tooltips.py │  │   utils.py    │
        │          │   pdf_gen.py  │  └───────────────┘
        │          └───────────────┘          │
        ▼                  │                  │
┌─────────────────────────────────────────────────────────────┐
│                       utils/                                 │
│                      search.py                               │
│           Resolución de símbolos · Mapeo nombres             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE DATOS                            │
│                    (data_fetcher.py)                        │
│   Yahoo Finance API · Caché LRU · Paralelización            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  CAPA DE CONFIGURACIÓN                      │
│                      (config.py)                            │
│   Constantes · Thresholds · Ajustes por Sector              │
└─────────────────────────────────────────────────────────────┘
```

---

## Estructura de Archivos

```
finanzer/                         ~4,000 líneas (21 archivos)
├── __init__.py                   # Package principal (v3.0.0)
│
├── analysis/                     # Lógica financiera (1,306 líneas)
│   ├── __init__.py               # Exports centralizados (151)
│   ├── utils.py                  # safe_div, format_large_number (115)
│   ├── ratios.py                 # 40+ ratios financieros (338)
│   ├── scoring.py                # Altman Z, Piotroski F, WACC (450)
│   ├── alerts.py                 # Explicaciones educativas (82)
│   └── sectors.py                # Benchmarks por sector (170)
│
├── components/                   # Componentes UI (1,693 líneas)
│   ├── __init__.py               # Lazy loading (71)
│   ├── tooltips.py               # METRIC_TOOLTIPS - 49 métricas (401)
│   ├── cards.py                  # Metric cards con tooltips (88)
│   ├── charts.py                 # Gráficos Plotly (249)
│   ├── tables.py                 # Tablas comparativas (147)
│   ├── sensitivity.py            # Matriz DCF sensibilidad (225)
│   └── pdf_generator.py          # Generador de reportes PDF (512)
│
├── callbacks/                    # Callbacks Dash (423 líneas)
│   ├── __init__.py               # (13)
│   ├── search.py                 # Autocompletado de búsqueda (98)
│   ├── chart.py                  # Cambio de período gráfico (128)
│   └── comparison.py             # Comparador multi-acción (184)
│
├── utils/                        # Utilidades generales (162 líneas)
│   ├── __init__.py               # (17)
│   └── search.py                 # Resolución símbolos, COMPANY_NAMES (145)
│
└── assets/                       # Archivos estáticos
    └── styles.css                # CSS customizado (395 líneas)
```

**Archivos raíz:**
```
app.py              # Aplicación principal Dash (~3,030 líneas) ← Reducido 35%
financial_ratios.py # Funciones originales (~4,475 líneas)
data_fetcher.py     # Cliente de datos (~1,400 líneas)
config.py           # Configuración centralizada (~250 líneas)
stock_database.py   # Base de datos de tickers (~700 líneas)
sector_profiles.py  # Perfiles de sectores (~885 líneas)
```

---

## Módulos Detallados

### 1. finanzer/analysis/

**utils.py** - Funciones helper seguras
```python
safe_div(a, b)           # División sin ZeroDivisionError
safe_multiply(*args)     # Multiplicación con None handling
format_large_number(val) # 1234567890 → "$1.23B"
format_ratio(val, type)  # Formatea ratios para display
```

**ratios.py** - 40+ ratios financieros
```python
# Rentabilidad
roe(), roa(), roic()
operating_margin(), gross_margin(), net_margin()

# Valoración
price_earnings(), price_book(), price_sales()
ev_ebitda(), peg_ratio(), free_cash_flow_yield()

# Liquidez
current_ratio(), quick_ratio(), cash_ratio()

# Solvencia
debt_to_equity(), interest_coverage(), net_debt_to_ebitda()

# REITs
funds_from_operations(), price_to_ffo(), ffo_payout_ratio()
```

**scoring.py** - Modelos institucionales
```python
altman_z_score()         # Predicción de bancarrota (Z > 2.99 = seguro)
piotroski_f_score()      # Solidez financiera (0-9)
calculate_wacc()         # Costo promedio ponderado del capital
calculate_justified_pe() # P/E justificado por fundamentos
```

**alerts.py** - Sistema de explicaciones
```python
ALERT_EXPLANATIONS = {
    ("valoración", "p/e"): "El ratio P/E compara...",
    ("deuda", "interest"): "La cobertura de intereses mide...",
    # 20+ explicaciones por categoría
}

get_alert_explanation(category, reason)  # Retorna explicación educativa
```

**sectors.py** - Configuración sectorial
```python
get_sector_metrics_config(sector)  # Retorna métricas clave por sector
MARKET_BENCHMARKS = {              # Benchmarks S&P 500
    "pe": 28.9, "roe": 0.15, "debt_to_equity": 0.80, ...
}
```

### 2. finanzer/components/

**tooltips.py** - Diccionario de explicaciones
```python
METRIC_TOOLTIPS = {
    "pe": {
        "nombre": "P/E (Precio/Beneficio)",
        "que_es": "Cuántos dólares pagas por cada dólar de ganancia anual.",
        "rangos": "• <15: Posiblemente barata\n• 15-25: Valoración típica...",
        "contexto": "Compara siempre con empresas del mismo sector."
    },
    # ... 49 métricas más
}

LABEL_TO_TOOLTIP = {"P/E": "pe", "ROE": "roe", ...}  # Mapeo de labels
```

**cards.py** - Tarjetas de métricas
```python
create_metric_card(label, value, icon, tooltip_key)
create_metric_with_tooltip(label, value, tooltip_key, uid)
create_score_summary_card(label, score, max_score, icon)
```

**charts.py** - Visualizaciones Plotly
```python
get_score_color(score)              # Score → (color, label)
create_score_donut(score)           # Gráfico circular del score
create_price_chart(symbol, period)  # Gráfico de precio histórico
create_ytd_comparison_chart(...)    # Comparativo YTD
```

**tables.py** - Tablas comparativas
```python
create_comparison_metric_row(metric_name, company_val, sector_val, market_val)
create_comparison_table_header()    # Encabezado estilizado
```

**sensitivity.py** - Matriz DCF
```python
build_sensitivity_section(sensitivity_data, current_price)
get_sensitivity_cell_class(fair_value, price)  # Coloración según valoración
```

**pdf_generator.py** - Exportación PDF
```python
generate_simple_pdf(symbol, company_name, ratios, alerts, score)
# Retorna bytes del PDF listo para descargar
```

### 3. finanzer/utils/

**search.py** - Resolución de símbolos
```python
COMPANY_NAMES = {
    "apple": "AAPL", "google": "GOOGL", "microsoft": "MSFT", ...
}

resolve_symbol(query)     # "apple" → "AAPL"
is_valid_ticker(symbol)   # Valida formato de ticker
normalize_ticker(symbol)  # Normaliza a mayúsculas
```

---

## Uso de Módulos

### Importar componentes de análisis
```python
from finanzer.analysis import (
    roe, roa, roic,
    altman_z_score, piotroski_f_score,
    calculate_wacc, safe_div,
    get_alert_explanation,
    get_sector_metrics_config
)

# Calcular ratios
ratio = roe(net_income=100, average_equity=500)  # 0.2

# Scoring institucional
z, level, interp = altman_z_score(wc, ta, re, ebit, mve, tl, sales)

# Explicaciones educativas
explanation = get_alert_explanation("valoración", "P/E elevado")
```

### Importar componentes UI (requiere Dash)
```python
from finanzer.components import (
    create_metric_card,
    create_score_donut,
    create_comparison_metric_row,
    build_sensitivity_section,
    METRIC_TOOLTIPS
)

# Crear tarjeta
card = create_metric_card("P/E", "15.2x", "📊", "pe")

# Matriz de sensibilidad
section = build_sensitivity_section(sensitivity_data, current_price)
```

### Importar utilidades
```python
from finanzer.utils import resolve_symbol, COMPANY_NAMES

symbol = resolve_symbol("microsoft")  # "MSFT"
```

---

## Flujo de Datos

```
Usuario ingresa "AAPL"
         │
         ▼
    ┌─────────────┐
    │  utils/     │  resolve_symbol("AAPL") → valida ticker
    │  search.py  │
    └─────────────┘
         │
         ▼
    ┌─────────────┐
    │  callbacks/ │  update_search_suggestions() → dropdown
    │  search.py  │
    └─────────────┘
         │ (selección)
         ▼
    ┌─────────────┐
    │  app.py     │  handle_navigation() → análisis completo
    │  (main)     │
    └─────────────┘
         │
         ▼
    ┌─────────────┐
    │data_fetcher │  get_complete_analysis_data("AAPL")
    │  (API)      │  → ThreadPoolExecutor (4 llamadas paralelas)
    └─────────────┘
         │
         ▼
    ┌─────────────┐
    │ analysis/   │  ratios.py: calculate_all_ratios()
    │ scoring.py  │  scoring.py: altman_z, piotroski_f
    │ sectors.py  │  sectors.py: get_sector_metrics_config()
    └─────────────┘
         │
         ▼
    ┌─────────────┐
    │ components/ │  charts.py: create_score_donut()
    │             │  cards.py: create_metric_card()
    │             │  sensitivity.py: build_sensitivity_section()
    │             │  tables.py: create_comparison_metric_row()
    └─────────────┘
         │
         ▼
    ┌─────────────┐
    │  Render     │  7 tabs con métricas, gráficos, alertas
    └─────────────┘
```

---

## Métricas de Código v3.0.0

### Paquete finanzer/

| Módulo | Líneas | Descripción |
|--------|--------|-------------|
| analysis/utils.py | 115 | Funciones helper |
| analysis/ratios.py | 338 | 40+ ratios |
| analysis/scoring.py | 450 | Modelos institucionales |
| analysis/alerts.py | 82 | Explicaciones alertas |
| analysis/sectors.py | 170 | Config. sectores |
| components/tooltips.py | 401 | 49 métricas explicadas |
| components/cards.py | 88 | Tarjetas métricas |
| components/charts.py | 249 | Gráficos Plotly |
| components/tables.py | 147 | Tablas comparativas |
| components/sensitivity.py | 225 | Matriz DCF |
| components/pdf_generator.py | 512 | Generador PDF |
| callbacks/*.py | 423 | Callbacks Dash |
| utils/search.py | 145 | Resolución símbolos |
| assets/styles.css | 395 | CSS customizado |
| **Total finanzer/** | **~4,000** | 21 archivos |

### Reducción de app.py

| Versión | Líneas | Cambio |
|---------|--------|--------|
| v2.9 (original) | 4,670 | — |
| v3.0.0 (modular) | 3,030 | **-35%** |

---

## Testing

```
tests/
├── conftest.py
├── fixtures/
│   ├── companies.py
│   └── expected.py
├── unit/
│   ├── test_altman_z.py
│   ├── test_piotroski.py
│   ├── test_dcf.py
│   ├── test_ratios.py
│   └── test_scoring.py
└── integration/
    ├── test_complete_flow.py
    └── test_data_fetcher.py

# Cobertura: 84% (298 tests)
```

---

## Dependencias

```
dash>=2.14.0              # Framework web
dash-bootstrap-components # UI components
pandas>=2.0.0             # DataFrames
yfinance>=0.2.31          # Yahoo Finance API
plotly>=5.18.0            # Gráficos interactivos
numpy                     # Cálculos numéricos
reportlab                 # Generación PDF
```

---

## Performance

| Métrica | Valor |
|---------|-------|
| Tiempo análisis (cold) | ~2.4s |
| Tiempo con caché | ~0.7s |
| Llamadas API paralelas | 4 |
| Caché TTL | 10 min |
| Memoria típica | ~50MB |

---

## Beneficios de la Arquitectura Modular

1. **Mantenibilidad**: Cada módulo tiene una responsabilidad clara
2. **Testabilidad**: Funciones aisladas, fáciles de probar
3. **Reutilización**: Componentes importables independientemente
4. **Escalabilidad**: Añadir funcionalidades sin tocar app.py
5. **Lazy loading**: Solo carga lo que necesita (components/__init__.py)
6. **Separación de concerns**: Lógica financiera separada de UI
