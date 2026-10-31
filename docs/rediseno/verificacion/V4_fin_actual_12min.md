# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T04:56:48. Backend: finanzer_next-e4/backend (mezcla v4). 20 usuarios durante 12.0 min (carga medida: 724.0 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 335 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.072 s (n = 1180) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | 9.2 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 1.381 s; tenencia máx. 5.497 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 1180 | 0 | 0 | 0.016 | 0.072 | 3.127 |
| analysis_cold | 10 | 0 | 0 | 1.971 | 5.517 | 5.517 |
| page | 1623 | 0 | 0 | 0.002 | 0.05 | 0.281 |
| pdf | 157 | 0 | 0 | 0.09 | 0.235 | 1.906 |
| peers | 1319 | 0 | 0 | 0.002 | 0.03 | 0.098 |
| prices | 1180 | 0 | 0 | 0.063 | 0.114 | 1.707 |
| scenario | 368 | 0 | 0 | 0.002 | 0.042 | 0.095 |
| search | 248 | 0 | 0 | 0.162 | 0.598 | 1.195 |
| segments | 1180 | 0 | 0 | 0.001 | 0.01 | 2.638 |
| trending | 443 | 0 | 0 | 0.001 | 0.003 | 0.03 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.83 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.65 s.
- Primer análisis de cada empresa: AAPL 2.65 s (200), JPM 1.54 s (200), O 1.4 s (200), NEE 1.97 s (200), XOM 1.46 s (200), PLTR 1.39 s (200), RIVN 1.67 s (200), BCS 1.77 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 78.1, 'cards': 30, 'listo': 30}.
- Memoria: pico del calentamiento 264.6 MB; al empezar la carga 257.0 MB; pico de la carga 335.0 MB (picos por separado: RSS 283.4 MB, huella física 335.0 MB).

Turnos de análisis: 1355 de usuarios y 142 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 104 | 27.32 |
| data_fetcher._data_cache | 160 | 11.53 |
| price_history._cache | 64 | 3.31 |
| yf_adapter._stmt_cache | 336 | 2.8 |
| finnhub_fallback._cache | 96 | 1.96 |
| price_history._chart_cache | 15 | 1.86 |
| universe._state | 4 | 0.35 |
| analysis_queue._summaries | 64 | 0.27 |
| segments._cache | 8 | 0.05 |
| peers._caps | 131 | 0.02 |
| trending._state | 7 | 0.01 |
| yf_adapter._cache | 48 | 0.01 |
