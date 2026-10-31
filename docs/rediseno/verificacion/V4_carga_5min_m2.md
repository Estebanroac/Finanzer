# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T02:38:38. Backend: finanzer_next-e4/backend (mezcla v4). 20 usuarios durante 5.0 min (carga medida: 303.7 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 442 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.392 s (n = 298) | < 2.0 s |
| Memoria estable (2.ª mitad) | ❌ | 32.8 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 0.439 s; tenencia máx. 3.763 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 298 | 0 | 0 | 0.02 | 0.392 | 1.384 |
| analysis_cold | 10 | 0 | 0 | 1.691 | 1.869 | 1.869 |
| page | 403 | 0 | 0 | 0.002 | 0.051 | 0.098 |
| pdf | 42 | 0 | 0 | 0.09 | 0.184 | 0.287 |
| peers | 901 | 0 | 0 | 0.002 | 0.016 | 0.061 |
| prices | 298 | 0 | 0 | 0.062 | 0.088 | 1.376 |
| scenario | 85 | 0 | 0 | 0.003 | 0.031 | 0.04 |
| search | 58 | 0 | 0 | 0.128 | 0.234 | 0.329 |
| segments | 298 | 0 | 0 | 0.001 | 0.02 | 2.772 |
| trending | 105 | 0 | 0 | 0.002 | 0.005 | 0.038 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.63 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 3.81 s.
- Primer análisis de cada empresa: AAPL 3.81 s (200), JPM 2.15 s (200), O 1.45 s (200), NEE 1.61 s (200), XOM 1.35 s (200), PLTR 1.57 s (200), RIVN 1.49 s (200), BCS 2.07 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 57.1, 'cards': 30, 'listo': 30}.
- Memoria: pico del calentamiento 380.5 MB; al empezar la carga 380.5 MB; pico de la carga 441.7 MB (picos por separado: RSS 433.3 MB, huella física 441.7 MB).

Turnos de análisis: 358 de usuarios y 82 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: hay criterios en rojo.**

## Cachés al final de la carga (tamaño serializado, aproximado)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 104 | 7.35 |
| data_fetcher._data_cache | 160 | 2.42 |
| price_history._cache | 64 | 2.34 |
| yf_adapter._cache | 48 | 1.46 |
| yf_adapter._best_cache | 48 | 1.46 |
| yf_adapter._stmt_cache | 336 | 1.44 |
| price_history._chart_cache | 15 | 1.36 |
| finnhub_fallback._cache | 96 | 0.65 |
| universe._state | 4 | 0.06 |
| analysis_queue._summaries | 64 | 0.03 |
| segments._cache | 8 | 0.01 |
| cost_of_capital._RF_CACHE | 1 | 0.0 |
