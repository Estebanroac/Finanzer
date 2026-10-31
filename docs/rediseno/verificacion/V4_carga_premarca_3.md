# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-31T00:46:14. Backend: finanzer_next-premarca/backend (mezcla v4). 20 usuarios durante 3.0 min (carga medida: 184.3 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ❌ | 454 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.538 s (n = 352) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -71.2 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 4.673 s; tenencia máx. 6.736 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 352 | 0 | 0 | 0.03 | 0.538 | 6.33 |
| analysis_cold | 10 | 0 | 0 | 1.726 | 4.125 | 4.125 |
| page | 472 | 0 | 0 | 0.004 | 0.08 | 0.301 |
| pdf | 47 | 0 | 0 | 0.096 | 0.304 | 0.359 |
| peers | 245 | 0 | 0 | 0.004 | 0.062 | 0.164 |
| prices | 352 | 0 | 0 | 0.098 | 0.178 | 0.815 |
| scenario | 107 | 0 | 0 | 0.003 | 0.051 | 0.065 |
| search | 62 | 0 | 0 | 0.143 | 0.315 | 0.341 |
| segments | 352 | 0 | 0 | 0.001 | 0.024 | 0.084 |
| sparklines | 120 | 0 | 0 | 0.005 | 0.043 | 1.523 |
| trending | 120 | 0 | 0 | 0.007 | 0.037 | 0.071 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.63 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.48 s.
- Primer análisis de cada empresa: AAPL 2.48 s (200), JPM 1.71 s (200), O 1.92 s (200), NEE 2.36 s (200), XOM 1.74 s (200), PLTR 1.3 s (200), RIVN 1.37 s (200), BCS 2.33 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 72.8, 'cards': 90, 'listo': 47}.
- Memoria: pico del calentamiento 405.8 MB; al empezar la carga 405.8 MB; pico de la carga 454.1 MB (picos por separado: RSS 454.1 MB, huella física 371.1 MB).

Turnos de análisis: 417 de usuarios y 167 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: hay criterios en rojo.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 134 | 31.75 |
| data_fetcher._data_cache | 196 | 17.78 |
| price_history._cache | 64 | 3.31 |
| yf_adapter._stmt_cache | 336 | 2.86 |
| price_history._chart_cache | 16 | 1.98 |
| sparklines._cache | 120 | 0.72 |
| trending._state | 7 | 0.68 |
| segments._cache | 64 | 0.37 |
| finnhub_fallback._cache | 96 | 0.34 |
| analysis_queue._summaries | 64 | 0.3 |
| universe._state | 4 | 0.29 |
| peers._caps | 217 | 0.04 |
