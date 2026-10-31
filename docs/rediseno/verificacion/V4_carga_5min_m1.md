# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T02:11:16. Backend: finanzer_next-e4/backend (mezcla v4). 20 usuarios durante 5.0 min (carga medida: 304.7 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 381 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.388 s (n = 311) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | 6.9 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 1.329 s; tenencia máx. 3.798 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 311 | 0 | 0 | 0.014 | 0.388 | 2.11 |
| analysis_cold | 10 | 0 | 0 | 1.682 | 3.803 | 3.803 |
| page | 420 | 0 | 0 | 0.001 | 0.054 | 0.111 |
| pdf | 42 | 0 | 0 | 0.079 | 0.237 | 0.318 |
| peers | 878 | 0 | 0 | 0.001 | 0.017 | 0.092 |
| prices | 311 | 0 | 0 | 0.062 | 0.124 | 2.63 |
| scenario | 87 | 0 | 0 | 0.001 | 0.028 | 0.081 |
| search | 59 | 0 | 0 | 0.08 | 0.225 | 0.339 |
| segments | 311 | 0 | 0 | 0.001 | 0.028 | 5.021 |
| trending | 109 | 0 | 0 | 0.001 | 0.002 | 0.002 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.42 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.88 s.
- Primer análisis de cada empresa: AAPL 2.88 s (200), JPM 2.23 s (200), O 1.53 s (200), NEE 1.94 s (200), XOM 2.12 s (200), PLTR 2.12 s (200), RIVN 1.45 s (200), BCS 2.54 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 57.1, 'cards': 30, 'listo': 30}.
- Memoria: pico del calentamiento 314.8 MB; al empezar la carga 295.9 MB; pico de la carga 380.9 MB (picos por separado: RSS 354.7 MB, huella física 380.9 MB).

Turnos de análisis: 371 de usuarios y 84 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**
