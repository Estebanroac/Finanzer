# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-30T14:50:53. Backend: finanzer_next-v4f8/backend (mezcla v4). 20 usuarios durante 3.0 min (carga medida: 184.8 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 408 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.423 s (n = 382) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -0.2 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 6.182 s; tenencia máx. 6.926 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 382 | 0 | 0 | 0.029 | 0.423 | 8.472 |
| analysis_cold | 10 | 0 | 0 | 2.543 | 6.042 | 6.042 |
| page | 505 | 0 | 0 | 0.004 | 0.093 | 0.232 |
| pdf | 50 | 0 | 0 | 0.095 | 0.455 | 2.779 |
| peers | 187 | 0 | 0 | 0.003 | 0.063 | 0.127 |
| prices | 382 | 0 | 0 | 0.103 | 0.218 | 1.193 |
| scenario | 116 | 0 | 0 | 0.003 | 0.062 | 0.097 |
| search | 64 | 0 | 0 | 0.162 | 0.336 | 0.4 |
| segments | 382 | 0 | 0 | 0.001 | 0.022 | 0.244 |
| sparklines | 123 | 0 | 0 | 0.005 | 0.05 | 1.863 |
| trending | 123 | 0 | 0 | 0.008 | 0.035 | 0.065 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 3.48 s.
- Primer análisis de cada empresa: AAPL 3.48 s (200), JPM 5.14 s (200), O 2.94 s (200), NEE 5.02 s (200), XOM 2.48 s (200), PLTR 2.23 s (200), RIVN 1.73 s (200), BCS 2.82 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 103.3, 'cards': 90, 'listo': 47}.
- Memoria: pico del calentamiento 406.8 MB; al empezar la carga 339.0 MB; pico de la carga 407.7 MB (picos por separado: RSS 407.7 MB, huella física 402.6 MB).

Turnos de análisis: 450 de usuarios y 147 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 133 | 30.54 |
| data_fetcher._data_cache | 190 | 17.2 |
| price_history._cache | 64 | 3.34 |
| yf_adapter._stmt_cache | 336 | 2.85 |
| price_history._chart_cache | 16 | 1.98 |
| finnhub_fallback._cache | 96 | 1.58 |
| sparklines._cache | 120 | 0.72 |
| trending._state | 7 | 0.68 |
| segments._cache | 64 | 0.38 |
| analysis_queue._summaries | 64 | 0.3 |
| universe._state | 4 | 0.29 |
| peers._caps | 217 | 0.04 |
