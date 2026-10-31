# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T04:28:39. Backend: finanzer_next-e4/backend (mezcla v4). 20 usuarios durante 5.0 min (carga medida: 304.6 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 330 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.399 s (n = 296) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -9.3 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 0.759 s; tenencia máx. 11.609 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 296 | 0 | 0 | 0.018 | 0.399 | 1.112 |
| analysis_cold | 10 | 0 | 0 | 2.486 | 5.104 | 5.104 |
| page | 403 | 0 | 0 | 0.002 | 0.039 | 0.138 |
| pdf | 42 | 0 | 0 | 0.093 | 0.202 | 0.294 |
| peers | 893 | 0 | 0 | 0.002 | 0.023 | 0.096 |
| prices | 296 | 0 | 0 | 0.062 | 0.164 | 4.921 |
| scenario | 83 | 0 | 0 | 0.002 | 0.027 | 0.046 |
| search | 57 | 0 | 0 | 0.261 | 0.994 | 1.061 |
| segments | 296 | 0 | 0 | 0.001 | 0.042 | 2.343 |
| trending | 107 | 0 | 0 | 0.001 | 0.003 | 0.055 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 6.75 s.
- Primer análisis de cada empresa: AAPL 6.75 s (200), JPM 3.87 s (200), O 3.68 s (200), NEE 3.94 s (200), XOM 3.87 s (200), PLTR 3.05 s (200), RIVN 5.7 s (200), BCS 5.13 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 150.2, 'cards': 30, 'listo': 30}.
- Memoria: pico del calentamiento 255.1 MB; al empezar la carga 241.9 MB; pico de la carga 330.4 MB (picos por separado: RSS 281.3 MB, huella física 330.4 MB).

Turnos de análisis: 356 de usuarios y 84 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 72 | 15.14 |
| data_fetcher._data_cache | 160 | 11.59 |
| price_history._cache | 64 | 3.31 |
| yf_adapter._stmt_cache | 336 | 2.8 |
| price_history._chart_cache | 15 | 1.86 |
| finnhub_fallback._cache | 96 | 0.96 |
| universe._state | 4 | 0.35 |
| analysis_queue._summaries | 64 | 0.27 |
| segments._cache | 8 | 0.05 |
| peers._caps | 131 | 0.02 |
| trending._state | 7 | 0.01 |
| yf_adapter._cache | 48 | 0.01 |
