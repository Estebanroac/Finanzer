# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-31T00:25:49. Backend: finanzer_next-premarca/backend (mezcla v4). 20 usuarios durante 3.0 min (carga medida: 184.5 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ❌ | 463 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.224 s (n = 364) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | 0.9 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 4.529 s; tenencia máx. 6.429 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 364 | 0 | 0 | 0.036 | 0.224 | 6.852 |
| analysis_cold | 10 | 0 | 0 | 1.934 | 3.287 | 3.287 |
| page | 481 | 0 | 0 | 0.004 | 0.08 | 0.234 |
| pdf | 48 | 0 | 0 | 0.098 | 0.247 | 2.319 |
| peers | 230 | 0 | 0 | 0.005 | 0.059 | 0.153 |
| prices | 364 | 0 | 0 | 0.099 | 0.177 | 0.886 |
| scenario | 105 | 0 | 0 | 0.003 | 0.065 | 0.113 |
| search | 61 | 0 | 0 | 0.179 | 0.768 | 1.093 |
| segments | 364 | 0 | 0 | 0.001 | 0.03 | 0.161 |
| sparklines | 117 | 0 | 0 | 0.006 | 0.048 | 1.706 |
| trending | 117 | 0 | 0 | 0.009 | 0.049 | 0.081 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.63 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.32 s.
- Primer análisis de cada empresa: AAPL 2.32 s (200), JPM 1.66 s (200), O 2.21 s (200), NEE 1.91 s (200), XOM 1.61 s (200), PLTR 1.67 s (200), RIVN 1.44 s (200), BCS 2.33 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 75.8, 'cards': 90, 'listo': 48}.
- Memoria: pico del calentamiento 405.7 MB; al empezar la carga 405.6 MB; pico de la carga 462.6 MB (picos por separado: RSS 462.6 MB, huella física 377.1 MB).

Turnos de análisis: 430 de usuarios y 149 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: hay criterios en rojo.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 131 | 34.51 |
| data_fetcher._data_cache | 186 | 16.83 |
| price_history._cache | 64 | 3.31 |
| yf_adapter._stmt_cache | 336 | 2.83 |
| price_history._chart_cache | 16 | 1.98 |
| finnhub_fallback._cache | 96 | 0.95 |
| sparklines._cache | 120 | 0.72 |
| trending._state | 7 | 0.68 |
| segments._cache | 64 | 0.4 |
| analysis_queue._summaries | 64 | 0.3 |
| universe._state | 4 | 0.29 |
| peers._caps | 238 | 0.04 |
