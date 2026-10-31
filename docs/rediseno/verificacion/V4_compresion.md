# V4 · Compresión de las respuestas (encargo del PM, 2026-10-18)

**Qué se hizo (598a611).**
- `lib/web_guard.Compress` envuelve `GZipMiddleware` de Starlette y es la capa más externa, así que la CSP calcula sus
  hashes sobre el HTML sin comprimir.
- Comprime la API y los estáticos de `/v2` y `/` a partir de `gzip_minimum_bytes` (1 KB), con `gzip_level` 5.
- Los PDF (`gzip_exclude_paths`: `/api/pdf/`, `/api/v2/pdf/`) van tal cual: ya vienen comprimidos y recomprimirlos solo
  gasta CPU.
- No hay respuestas en streaming de contenido; los estáticos grandes (`FileResponse`) se comprimen por trozos.
- Tests por HTTP real (`test_v6_http.py`):
  - un JSON comprimido se descomprime en el mismo JSON;
  - una respuesta de menos de 1 KB va sin comprimir;
  - un PDF va sin comprimir y byte a byte igual;
  - el HTML va comprimido y su CSP lleva el hash del script.

**Nivel de compresión** (análisis de AAPL, 214 KB, coste de CPU por respuesta en local):

| Nivel | Tamaño | ms por respuesta |
|---|---|---|
| 1 | 50 KB (23,6 %) | 0,8 |
| **5 (elegido)** | 41 KB (19,6 %) | 1,5 |
| 6 | 41 KB (19,2 %) | 2,0 |
| 9 (el de Starlette por defecto) | 40 KB (18,8 %) | 7,3 |

**Antes y después** (backend real en local, en caché, mejor de 10 peticiones):

| Endpoint | Sin compresión | Con gzip | Tiempo |
|---|---|---|---|
| `/api/analysis/AAPL` | 143 KB | 36,7 KB (−74 %) | 12,5 → 13,5 ms (+1 ms de CPU) |
| `/api/v2/prices/AAPL` | 296 KB | 69,7 KB (−76 %) | 50,4 → 53,5 ms (+3 ms) |

**Carga corta (5 min, 20 usuarios; el cliente pide gzip).** El arnés no limita la CPU (`--cpus` no existe en macOS sin
contenedor), así que el coste en Render se estima por petición.

| Corrida | Pico | p95 de `/api/analysis` en caché | 5xx |
|---|---|---|---|
| Sin compresión (V4_fin_actual 1–3) | 396 / 339 / 334 MB | 0,42 / 0,41 / 0,43 s | 0 |
| Con gzip (1) | 402 MB | 0,435 s | 0 |
| Con gzip (2) | 377 MB | 0,48 s | 0 |

El p95 sube unos 0,02–0,05 s (de 0,41–0,43 a 0,435–0,48 s): dentro del ruido de la carga y muy lejos del límite de
2 s. La memoria no cambia (377–402 MB, dentro de la variación de ±40 MB entre corridas).

**Estimación para Render (0,1 CPU).**
- Coste: unos 15 ms de CPU por respuesta del análisis y unos 30 ms por la serie de precios (10 veces lo local).
- Ahorro: lo que el origen envía a Cloudflare baja un 75 %. En la cuota de 0,1 CPU, el envío de 143–296 KB también
  cuesta.
- Los estáticos (JS/CSS de Next) se comprimen al servirse, pero Cloudflare los cachea por extensión: el origen los
  comprime una vez por despliegue, no en cada visita.
- Cloudflare ya comprime hacia el navegador (br): para el usuario final, el cambio es sobre todo menos tráfico entre
  Render y Cloudflare.
