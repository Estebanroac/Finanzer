# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-31T00:36:17. Backend: finanzer_next-premarca/backend (mezcla v4). 20 usuarios durante 3.0 min (carga medida: 184.6 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ❌ | 455 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.567 s (n = 343) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -55.6 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 4.557 s; tenencia máx. 6.883 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 343 | 0 | 0 | 0.031 | 0.567 | 6.159 |
| analysis_cold | 10 | 0 | 0 | 1.842 | 3.56 | 3.56 |
| page | 460 | 0 | 0 | 0.004 | 0.085 | 0.183 |
| pdf | 47 | 0 | 0 | 0.104 | 0.453 | 0.763 |
| peers | 253 | 0 | 0 | 0.003 | 0.059 | 0.132 |
| prices | 343 | 0 | 0 | 0.098 | 0.197 | 1.185 |
| scenario | 104 | 0 | 0 | 0.003 | 0.053 | 0.104 |
| search | 63 | 0 | 0 | 0.123 | 0.286 | 0.313 |
| segments | 343 | 0 | 0 | 0.001 | 0.034 | 0.603 |
| sparklines | 117 | 0 | 0 | 0.006 | 0.07 | 1.559 |
| trending | 117 | 0 | 0 | 0.008 | 0.035 | 0.11 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.63 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.48 s.
- Primer análisis de cada empresa: AAPL 2.48 s (200), JPM 1.75 s (200), O 1.94 s (200), NEE 1.89 s (200), XOM 1.63 s (200), PLTR 1.43 s (200), RIVN 1.43 s (200), BCS 2.33 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 75.8, 'cards': 90, 'listo': 46}.
- Memoria: pico del calentamiento 399.1 MB; al empezar la carga 399.1 MB; pico de la carga 454.8 MB (picos por separado: RSS 454.8 MB, huella física 374.8 MB).

Turnos de análisis: 408 de usuarios y 143 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: hay criterios en rojo.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 134 | 32.75 |
| data_fetcher._data_cache | 196 | 17.79 |
| price_history._cache | 64 | 3.31 |
| yf_adapter._stmt_cache | 336 | 2.86 |
| price_history._chart_cache | 16 | 1.98 |
| finnhub_fallback._cache | 96 | 0.8 |
| sparklines._cache | 120 | 0.72 |
| trending._state | 7 | 0.68 |
| segments._cache | 64 | 0.38 |
| analysis_queue._summaries | 64 | 0.3 |
| universe._state | 4 | 0.29 |
| peers._caps | 217 | 0.04 |
