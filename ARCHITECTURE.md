# 🏗️ Arquitectura - Finanzer

## Visión General

Finanzer sigue una arquitectura modular de 4 capas:

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE PRESENTACIÓN                     │
│                         (app.py)                            │
│   Dash/Plotly · Bootstrap · Callbacks · Visualizaciones     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE LÓGICA                           │
│                   (financial_ratios.py)                     │
│   Ratios · Scores · DCF · Alertas · Clasificación           │
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
│            (config.py · sector_profiles.py)                 │
│   Constantes · Thresholds · Ajustes por Sector              │
└─────────────────────────────────────────────────────────────┘
```

---

## Componentes Principales

### 1. app.py (~3,200 líneas)
**Responsabilidad**: Interfaz de usuario y orquestación

```python
# Estructura principal
app = Dash(__name__)

# Layout
app.layout = html.Div([
    # Navbar
    # Search Input
    # Tabs (6 pestañas de análisis)
    # Modals
])

# Callbacks
@app.callback(...)  # Análisis principal
@app.callback(...)  # Generación PDF
@app.callback(...)  # Actualización de tabs
```

**Componentes clave**:
- `METRIC_TOOLTIPS` - Diccionario con ~35 tooltips explicativos
- `create_metric_card()` - Genera tarjetas de métricas con tooltips
- `create_score_donut()` - Gráfico circular del score
- `generate_pdf_content()` - Exportación a PDF

### 2. financial_ratios.py (~4,000 líneas)
**Responsabilidad**: Motor de cálculos financieros

```python
# Modelos institucionales
altman_z_score()        # Predicción de bancarrota
piotroski_f_score()     # Solidez financiera (9 criterios)
dcf_multi_stage()       # Valoración DCF 3 etapas
dcf_multi_stage_dynamic()  # DCF con WACC/growth automático

# Ratios fundamentales
roe(), roa(), roic()    # Rentabilidad
current_ratio(), quick_ratio()  # Liquidez
debt_to_equity(), interest_coverage()  # Solvencia
pe(), pb(), ev_ebitda()  # Valoración

# Sistema de scoring
calculate_comprehensive_score()  # Score 0-100
aggregate_alerts()      # Sistema de alertas
classify_company_type() # Growth vs Value
```

**Funciones principales**:

| Función | Propósito | Inputs | Output |
|---------|-----------|--------|--------|
| `altman_z_score()` | Riesgo bancarrota | 7 métricas | (z, nivel, msg) |
| `piotroski_f_score()` | Solidez | 12 métricas | (score, desglose) |
| `dcf_multi_stage_dynamic()` | Valor intrínseco | FCF, shares, beta... | Dict completo |
| `calculate_all_ratios()` | Todos los ratios | financial_data | Dict ~40 ratios |
| `aggregate_alerts()` | Score + alertas | ratios, contextual | Dict con score |

### 3. data_fetcher.py (~1,400 líneas)
**Responsabilidad**: Obtención de datos financieros

```python
class SimpleCache:
    """Caché LRU con TTL"""
    
class YahooFinanceFetcher:
    """Wrapper para yfinance"""
    get_company_profile()
    get_financial_data()
    get_historical_metrics()
    get_detailed_historical_data()
    
class FinancialDataService:
    """Orquestador principal"""
    get_complete_analysis_data()  # Paralelo con ThreadPoolExecutor
```

**Flujo de datos paralelo**:
```
get_complete_analysis_data(symbol)
    │
    ├── ThreadPoolExecutor(max_workers=4)
    │   ├── get_company_profile()     ─┐
    │   ├── get_financial_data()      ─┼── En paralelo (~1.7s)
    │   ├── get_historical_metrics()  ─┤
    │   └── get_detailed_historical() ─┘
    │
    └── get_sector_averages()  # Secuencial (necesita profile)
    
    Total: ~2.4s (vs 5s secuencial)
```

### 4. config.py (~250 líneas)
**Responsabilidad**: Configuración centralizada

```python
# Thresholds de modelos
ALTMAN_Z_SAFE = 2.99
PIOTROSKI_STRONG = 7

# Parámetros DCF
DCF_RISK_FREE_RATE = 0.045
DCF_TERMINAL_GROWTH = 0.025

# Ajustes por sector
SECTOR_ADJUSTMENTS = {
    "financials": {...},
    "real_estate": {...},
    ...
}
```

---

## Flujo de Datos

### Análisis de una acción

```
Usuario ingresa "AAPL"
         │
         ▼
    ┌─────────────┐
    │  app.py     │  Callback: analyze_stock()
    │  (UI)       │
    └─────────────┘
         │
         ▼
    ┌─────────────┐
    │ data_fetcher│  get_complete_analysis_data("AAPL")
    │  (API)      │  → Llamadas paralelas a Yahoo Finance
    └─────────────┘
         │
         ▼
    ┌─────────────┐
    │ financial_  │  calculate_all_ratios(data)
    │ ratios.py   │  aggregate_alerts(ratios)
    │  (Cálculos) │  dcf_multi_stage_dynamic(...)
    └─────────────┘
         │
         ▼
    ┌─────────────┐
    │  app.py     │  Renderiza:
    │  (UI)       │  - Score card
    └─────────────┘  - 6 tabs con métricas
                     - Gráficos Plotly
                     - Alertas/recomendaciones
```

---

## Sistema de Caché

```python
SimpleCache(default_ttl_minutes=10, max_entries=500)

# Estrategia LRU (Least Recently Used)
# - Evicta entradas expiradas automáticamente
# - Evicta 10% más viejas al alcanzar límite

# TTLs por tipo de dato:
# - Profile: 30 min (cambia poco)
# - Financials: 10 min (default)
# - Historical: 10 min
```

---

## Sistema de Scoring

```
Score Base: 50 pts

Ajustes positivos:
├── Altman Z > 2.99      (+8 pts)
├── Piotroski F >= 7     (+10 pts)
├── ROE > 20%            (+8 pts)
├── FCF positivo         (+5 pts)
├── P/E < 15             (+5 pts)
└── ...

Ajustes negativos:
├── Z-Score < 1.81       (-15 pts)
├── F-Score <= 3         (-10 pts)
├── D/E > 2.0            (-8 pts)
├── FCF negativo         (-5 pts)
└── ...

Score Final = Base + Σ(Ajustes)
Rango: 0-100
```

---

## Manejo de Errores

```python
# Nivel 1: Validación de inputs
if value is None or value <= 0:
    return None  # Graceful degradation

# Nivel 2: Exception handling específico
try:
    result = calculation()
except (ZeroDivisionError, TypeError, ValueError):
    return None, "N/A", "Error específico"
except Exception:
    return None, "N/A", "Error inesperado"

# Nivel 3: Fallbacks en UI
if ratio is None:
    display = "N/A"
else:
    display = f"{ratio:.2f}"
```

---

## Testing

```
tests/
├── conftest.py          # Fixtures compartidos
├── fixtures/
│   ├── companies.py     # Datos de prueba por tipo
│   └── expected.py      # Resultados esperados
│
├── unit/
│   ├── test_altman_z.py
│   ├── test_piotroski.py
│   ├── test_dcf.py
│   ├── test_ratios.py
│   └── test_scoring.py
│
└── integration/
    ├── test_complete_flow.py
    └── test_data_fetcher.py

# Cobertura: 84% (298 tests)
# Tiempo: ~15 segundos
```

---

## Dependencias

```
dash>=2.14.0           # Framework web
dash-bootstrap-components  # UI components
pandas>=2.0.0          # DataFrames
yfinance>=0.2.31       # Yahoo Finance API
plotly>=5.18.0         # Gráficos interactivos
numpy                  # Cálculos numéricos
fpdf2                  # Generación PDF
```

---

## Consideraciones de Performance

1. **Paralelización**: 4 llamadas API en paralelo (ThreadPoolExecutor)
2. **Caché LRU**: Evita llamadas repetidas a la API
3. **Lazy loading**: Tabs se renderizan solo cuando se seleccionan
4. **Gráficos optimizados**: Plotly con displayModeBar=False

**Métricas**:
- Tiempo de análisis: ~2.4s (cold cache)
- Tiempo con caché: ~0.7s
- Memoria: ~50MB típico
