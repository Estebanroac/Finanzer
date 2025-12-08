# 📊 Stock Analyzer - Dash Edition

Aplicación web **responsive** para análisis fundamental de acciones con diseño mobile-first y dark theme premium.

## ✨ Características

- **40+ indicadores financieros** organizados en categorías
- **Score de inversión 0-100** con desglose transparente
- **Valoración intrínseca** (Graham Number + DCF)
- **Z-Score Altman** y **F-Score Piotroski**
- **Diseño responsive** - funciona perfectamente en móvil
- **Dark theme premium** con gradientes y animaciones

## 📱 Capturas

La app se adapta automáticamente a:
- 📱 Móviles (< 576px)
- 📱 Tablets (576px - 992px)  
- 🖥️ Desktop (> 992px)

## 🚀 Instalación

### 1. Clonar o descargar el proyecto

```bash
cd stock_analyzer_dash
```

### 2. Crear entorno virtual (recomendado)

```bash
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# o en Windows: venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Ejecutar la aplicación

```bash
python app.py
```

La app estará disponible en: **http://localhost:8050**

## 📁 Estructura del Proyecto

```
stock_analyzer_dash/
├── app.py                 # Aplicación principal Dash
├── assets/
│   └── custom.css         # CSS responsive mobile-first
├── data_fetcher.py        # Obtención de datos (Yahoo Finance)
├── financial_ratios.py    # Cálculos y sistema de scoring
├── sector_profiles.py     # Perfiles por sector
├── stock_database.py      # Base de datos de acciones
└── requirements.txt       # Dependencias
```

## 🔧 Configuración para Producción (Render)

### render.yaml

```yaml
services:
  - type: web
    name: stock-analyzer
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:server --bind 0.0.0.0:$PORT
```

### Variables de entorno necesarias:
- `PORT` - Puerto de la app (Render lo asigna automáticamente)

## 📊 Tecnologías

| Componente | Tecnología |
|------------|------------|
| Framework | Dash (Plotly) |
| UI | Dash Bootstrap Components |
| Gráficos | Plotly.js |
| Datos | Yahoo Finance (yfinance) |
| CSS | Custom CSS Mobile-First |

## 🆚 Comparación Streamlit vs Dash

| Aspecto | Streamlit | Dash |
|---------|-----------|------|
| Responsive | ⭐⭐ | ⭐⭐⭐⭐ |
| Performance | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Personalización | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Curva aprendizaje | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Deploy | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

## 📈 Sistema de Scoring

El score se calcula en **5 categorías × 20 puntos = 100 máximo**:

1. **🏛️ Solidez Financiera** (20 pts)
   - Z-Score Altman
   - Current Ratio
   - Debt/Equity
   - Interest Coverage

2. **💰 Rentabilidad** (20 pts)
   - ROE / ROA
   - Márgenes operativos
   - Márgenes netos

3. **📊 Valoración** (20 pts)
   - P/E vs sector
   - EV/EBITDA
   - P/FCF
   - FCF Yield

4. **✅ Calidad de Ganancias** (20 pts)
   - F-Score Piotroski
   - FCF vs Net Income
   - OCF positivo

5. **📈 Crecimiento** (20 pts)
   - Revenue CAGR 3Y
   - EPS Growth
   - FCF Growth

## ⚠️ Disclaimer

Esta herramienta es para **fines educativos**. No constituye asesoría financiera. Siempre haz tu propia investigación antes de invertir.

## 🛠️ Desarrollo

### Ejecutar en modo debug:

```bash
python app.py
```

### Ejecutar con gunicorn (producción):

```bash
gunicorn app:server --bind 0.0.0.0:8050
```

## 📝 Licencia

Uso personal. Desarrollado por Esteban.

---

*Migrado de Streamlit a Dash para mejor compatibilidad móvil - Diciembre 2025*
