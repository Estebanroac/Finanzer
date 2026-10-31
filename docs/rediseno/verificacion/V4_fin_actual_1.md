# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T04:06:49. Backend: finanzer_next-e4/backend (mezcla v4). 20 usuarios durante 5.0 min (carga medida: 304.4 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 396 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.42 s (n = 295) | < 2.0 s |
| Memoria estable (2.ª mitad) | ❌ | 27.3 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 0.444 s; tenencia máx. 9.342 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 295 | 0 | 0 | 0.017 | 0.42 | 1.005 |
| analysis_cold | 10 | 0 | 0 | 1.549 | 2.747 | 2.747 |
| page | 402 | 0 | 0 | 0.002 | 0.044 | 0.146 |
| pdf | 42 | 0 | 0 | 0.088 | 0.217 | 0.659 |
| peers | 904 | 0 | 0 | 0.001 | 0.023 | 0.071 |
| prices | 295 | 0 | 0 | 0.061 | 0.147 | 1.648 |
| scenario | 87 | 0 | 0 | 0.002 | 0.027 | 0.061 |
| search | 60 | 0 | 0 | 0.076 | 0.228 | 0.268 |
| segments | 295 | 0 | 0 | 0.001 | 0.037 | 2.181 |
| trending | 107 | 0 | 0 | 0.001 | 0.003 | 0.022 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.002 s; primer análisis de AAPL: 6.4 s.
- Primer análisis de cada empresa: AAPL 6.4 s (200), JPM 4.15 s (200), O 3.58 s (200), NEE 3.64 s (200), XOM 3.59 s (200), PLTR 3.31 s (200), RIVN 3.49 s (200), BCS 4.0 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 129.2, 'cards': 30, 'listo': 30}.
- Memoria: pico del calentamiento 314.8 MB; al empezar la carga 314.7 MB; pico de la carga 395.6 MB (picos por separado: RSS 328.3 MB, huella física 395.6 MB).

Turnos de análisis: 355 de usuarios y 82 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: hay criterios en rojo.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 104 | 27.49 |
| data_fetcher._data_cache | 160 | 11.59 |
| price_history._cache | 64 | 3.31 |
| yf_adapter._stmt_cache | 336 | 2.8 |
| price_history._chart_cache | 15 | 1.86 |
| finnhub_fallback._cache | 96 | 1.31 |
| universe._state | 4 | 0.35 |
| analysis_queue._summaries | 64 | 0.27 |
| segments._cache | 8 | 0.05 |
| peers._caps | 131 | 0.02 |
| trending._state | 7 | 0.01 |
| yf_adapter._cache | 48 | 0.01 |
