# 📊 Finanzer

**Analizador fundamental de acciones con modelos institucionales**

[![Version](https://img.shields.io/badge/version-2.7-green.svg)]()
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)]()
[![License](https://img.shields.io/badge/license-MIT-orange.svg)]()

---

## 🎯 ¿Qué es?

Finanzer es una aplicación web para análisis fundamental de acciones que implementa modelos de grado institucional:

- **Altman Z-Score** - Predicción de bancarrota
- **Piotroski F-Score** - Solidez financiera (9 criterios)
- **DCF Multi-Stage** - Valoración intrínseca con 3 etapas
- **Sistema de Scoring 100 pts** - Evaluación integral

Comparable a herramientas como Morningstar, S&P Capital IQ o Bloomberg Terminal, pero gratuito y de código abierto.

---

## 🚀 Instalación Rápida

### Requisitos
- Python 3.8+
- pip

### Pasos

```bash
# 1. Clonar/descargar el proyecto
cd ~/Downloads/Finanzer.zip

# 2. Crear entorno virtual (recomendado)
python3 -m venv venv
source venv/bin/activate  # En Mac/Linux
# o: venv\Scripts\activate  # En Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar
python3 app.py

# 5. Abrir en navegador
# http://127.0.0.1:8050
```

### Dependencias principales
```
dash>=2.14.0
dash-bootstrap-components>=1.5.0
pandas>=2.0.0
yfinance>=0.2.31
plotly>=5.18.0
```

---

## 📱 Uso

### Análisis Básico

1. Ingresa el símbolo del ticker (ej: `AAPL`, `NVDA`, `MSFT`)
2. Presiona Enter o haz clic en "Analizar"
3. Revisa las 6 pestañas de análisis:
   - **Valoración** - P/E, P/B, EV/EBITDA, etc.
   - **Rentabilidad** - ROE, ROA, márgenes
   - **Solidez** - Z-Score, F-Score, liquidez
   - **Histórico** - Tendencias y gráficos
   - **Sector** - Comparación con peers
   - **Intrínseco** - DCF y Graham Number

### Interpretación del Score

| Score | Nivel | Significado |
|-------|-------|-------------|
| 80-100 | Excepcional | Oportunidad de compra fuerte |
| 65-79 | Bueno | Empresa sólida |
| 50-64 | Aceptable | Neutral, investigar más |
| 35-49 | Débil | Precaución |
| 0-34 | Pobre | Evitar o vender |

### Exportar PDF

Haz clic en "📄 PDF" para generar un reporte completo descargable.

---

## 🏗️ Arquitectura

```
Finanzer.zip/
├── app.py                 # Aplicación Dash principal
├── financial_ratios.py    # Motor de cálculos financieros
├── data_fetcher.py        # Conexión a Yahoo Finance API
├── config.py              # Configuración centralizada
├── sector_profiles.py     # Perfiles por sector
├── stock_database.py      # Base de datos local
├── requirements.txt       # Dependencias
│
├── tests/                 # Suite de tests (298 tests, 84% coverage)
│   ├── conftest.py
│   ├── test_*.py
│   └── fixtures/
│
└── docs/                  # Documentación
    ├── README.md
    ├── ARCHITECTURE.md
    └── SCORING_MODEL.md
```

---

## 📐 Modelos Implementados

### Altman Z-Score (1968)
Predice probabilidad de bancarrota en 2 años.

```
Z = 1.2×X1 + 1.4×X2 + 3.3×X3 + 0.6×X4 + 1.0×X5

Donde:
X1 = Working Capital / Total Assets
X2 = Retained Earnings / Total Assets
X3 = EBIT / Total Assets
X4 = Market Cap / Total Liabilities
X5 = Sales / Total Assets

Interpretación:
• Z > 2.99: Zona segura
• 1.81-2.99: Zona gris
• Z < 1.81: Zona de peligro
```

### Piotroski F-Score (2000)
9 criterios binarios de solidez financiera.

```
Rentabilidad (4 pts):
1. ROA positivo
2. Operating Cash Flow positivo
3. ROA mejorando vs año anterior
4. Cash Flow > Net Income (calidad)

Apalancamiento (3 pts):
5. Deuda LP bajando
6. Current Ratio mejorando
7. Sin dilución de acciones

Eficiencia (2 pts):
8. Margen bruto mejorando
9. Asset Turnover mejorando

Interpretación:
• 7-9: Solidez excepcional (compra)
• 4-6: Neutral
• 0-3: Debilidad (evitar)
```

### DCF Multi-Stage
Modelo de 3 etapas más realista que DCF tradicional.

```
Etapa 1 (Años 1-5): Alto crecimiento con decay
Etapa 2 (Años 6-10): Transición hacia terminal
Etapa 3 (Año 10+): Perpetuidad (Gordon Growth)

WACC = Rf + β × (Rm - Rf) × E/(E+D) + Rd × (1-T) × D/(E+D)

Valor Intrínseco = Σ FCF_t/(1+WACC)^t + TV/(1+WACC)^n
```

---

## ⚙️ Configuración

Edita `config.py` para ajustar parámetros:

```python
# Tasas de mercado (actualizar periódicamente)
DCF_RISK_FREE_RATE = 0.045      # Treasury 10Y
DCF_MARKET_RISK_PREMIUM = 0.055 # Prima histórica

# Thresholds de scoring
ALTMAN_Z_SAFE = 2.99
PIOTROSKI_STRONG = 7

# Ajustes por sector
SECTOR_ADJUSTMENTS = {
    "financials": {"ignore_debt_equity": True},
    "real_estate": {"use_ffo": True},
    ...
}
```

---

## 🧪 Testing

```bash
# Ejecutar todos los tests
pytest tests/ -v

# Con coverage
pytest tests/ --cov=. --cov-report=html

# Solo tests rápidos
pytest tests/ -m "not slow"
```

**Coverage actual: 84% (298 tests)**

---

## 📈 Roadmap

- [x] Tests unitarios (84% coverage)
- [x] DCF Multi-Stage
- [x] Paralelización (2.4s vs 5s)
- [x] Métricas FFO para REITs
- [x] Configuración centralizada
- [x] Documentación
- [ ] API REST (futuro)
- [ ] Watchlists persistentes
- [ ] Alertas de precio

---

## 🤝 Contribuir

1. Fork el repositorio
2. Crea una rama (`git checkout -b feature/nueva-funcion`)
3. Commit cambios (`git commit -am 'Agregar función'`)
4. Push (`git push origin feature/nueva-funcion`)
5. Abre un Pull Request

---

## 📄 Licencia

MIT License - Libre para uso personal y comercial.

---

## 👨‍💻 Autor

**Esteban** - Desarrollado como herramienta personal de inversión.

---

## ⚠️ Disclaimer

Esta herramienta es solo para fines educativos e informativos. No constituye asesoramiento financiero. Siempre realiza tu propia investigación antes de invertir.
