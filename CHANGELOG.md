# Changelog - Stock Analyzer

## v2.2 - Sistema Adaptativo Growth/Value + Dark/Light Mode (Diciembre 2025)

### 🌓 Dark/Light Mode (NUEVO)
- **Toggle de tema**: Botón flotante en esquina inferior derecha
- **Persistencia**: El tema seleccionado se guarda en localStorage
- **CSS Variables**: Sistema completo de variables para colores, bordes, sombras
- **Transiciones suaves**: Cambio de tema sin parpadeos
- **Componentes adaptados**: Cards, tablas, inputs, tabs, alertas, badges

### 🎯 Mejoras al Modelo Financiero
- **score_valoracion() mejorado**: Ahora considera la calidad del crecimiento para ajustar penalizaciones de P/E alto
- **classify_company_type()**: Nueva función que clasifica empresas en deep_value, value, garp, growth, speculative_growth, dividend, o blend
- **calculate_growth_quality_score()**: Evalúa la calidad del crecimiento (0-100) basado en revenue, EPS, FCF, ROE/ROIC, y márgenes
- **DCF Dinámico**: Usa WACC específico de la empresa (CAPM) y growth histórico en lugar de valores fijos (8%, 3%)

### 📈 Impacto en Scores
- Empresas growth de alta calidad pueden ganar 3-6 puntos extra en valoración
- Empresas GARP con fundamentos excepcionales reciben bonus de +2 pts
- Las penalizaciones por P/E alto se reducen si la calidad del crecimiento lo justifica
- Sesgo anti-growth reducido significativamente

### 🔧 Nuevos Campos en Resultados
- `company_type`: Tipo de empresa identificado (value, growth, garp, etc.)
- `growth_quality_score`: Score de calidad del crecimiento (0-100)
- `growth_quality_label`: Etiqueta descriptiva

### 📝 Documentación
- Carpeta `tests/` con suite de tests de snapshot (40+ tests)
- `GUIA_MEJORAS.md` con documentación de cambios
- `INSTRUCCIONES.txt` para instalación

---

## v2.1 - Hardening de Producción (Diciembre 2025)

### 🔒 Seguridad
- **Debug mode**: Ahora controlado por variable de entorno `DEBUG` (default: `false`)
- **Validación de input**: Símbolos sanitizados con regex permisivo (acepta BRK.A, BRK-B, etc.)
- **Logging estructurado**: Reemplazados 15+ `print()` por `logging` configurado

### ⚡ Performance  
- **Imports optimizados**: `yfinance` movido al inicio del módulo (eliminados 3 imports redundantes dentro de funciones)
- **Caché con límites**: `SimpleCache` ahora tiene límite de 500 entradas con LRU eviction para prevenir memory leaks

### 📝 Documentación
- Agregado `.env.example` con variables de entorno documentadas
- README actualizado con instrucciones de configuración

### 🔧 Técnico
- `app.py`: v2.0 → v2.1
- `data_fetcher.py`: v2.0 → v2.1

---

## Cambios NO realizados (por riesgo de daño colateral)

Los siguientes cambios fueron identificados pero **no implementados** para preservar el funcionamiento:

1. **Refactorización de app.py** - Dividir en múltiples archivos podría romper callbacks de Dash
2. **Exception handling específico** - Remover `except Exception` genérico podría causar crashes inesperados
3. **Cambio de flujo PDF** - `dcc.send_bytes` no garantiza compatibilidad cross-browser
4. **Rate limiting** - Requiere infraestructura adicional (Redis/memcached)

Estos cambios se recomiendan para una futura versión 3.0 con testing extensivo.
