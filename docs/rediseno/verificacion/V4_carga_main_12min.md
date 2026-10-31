# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T01:51:59. Backend: finanzer_next/backend (mezcla legacy). 20 usuarios durante 12.0 min (carga medida: 724.4 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 317 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.044 s (n = 1656) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -19.8 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 0.0 s; tenencia máx. 0.0 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 1656 | 0 | 0 | 0.015 | 0.044 | 2.101 |
| analysis_cold | 10 | 0 | 0 | 2.657 | 3.359 | 3.359 |
| page | 2246 | 0 | 0 | 0.002 | 0.009 | 0.103 |
| pdf | 217 | 0 | 0 | 0.09 | 0.178 | 1.687 |
| search | 313 | 0 | 0 | 0.128 | 0.363 | 1.213 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.83 s; HTML de /v2/AAPL: 0.002 s; primer análisis de AAPL: 4.7 s.
- Primer análisis de cada empresa: AAPL 4.7 s (200), JPM 2.92 s (200), O 2.75 s (200), NEE 2.68 s (200), XOM 2.8 s (200), PLTR 2.55 s (200), RIVN 2.76 s (200), BCS 3.13 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': None, 's': None, 'cards': 0}.
- Memoria: pico del calentamiento 234.7 MB; al empezar la carga 234.7 MB; pico de la carga 317.4 MB (picos por separado: RSS 230.7 MB, huella física 317.4 MB).

Turnos de análisis: 0 de usuarios y 0 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: None s.

**Resultado: todo en verde.**
