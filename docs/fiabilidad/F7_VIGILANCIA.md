# Fase 7 · Vigilancia semanal del panel

*Operador F67prep, 15-oct-2026, rama `fiabilidad/f67-prep`. Plan: [`../PLAN_FIABILIDAD.md`](../PLAN_FIABILIDAD.md)
§4, fase 7, punto 1 ("rotura de fuente = cambio de veredicto sin cambio de precio ni de datos"). Herramienta:
`backend/tests/vigilancia.py`; tests sin red: `backend/tests/test_vigilancia.py` (16).*

## Cómo se usa

```
cd finanzer_next/backend
../.venv313/bin/python tests/vigilancia.py                 # corre y compara con la corrida más reciente
../.venv313/bin/python tests/vigilancia.py --prev <DIR>    # compara con otra corrida
../.venv313/bin/python tests/vigilancia.py --solo-comparar <DIR> --prev <DIR> [--salida <DIR>]   # sin red
```

1. **Corrida** (reutiliza `panel_run.run("live")`, no lo duplica): una petición a `/api/health` para despertar el
   servicio (descartada), el panel completo (hoy 32 tickers, con BCS) contra `https://finanzer.app` a concurrencia 3
   y, como en `panel_run`, la separación "solo Rf / solo precio / reales" frente al replay de cada fixture
   (`live_vs_replay.json`). Se niega a correr de 15:55 a 16:45 de Nueva York y con concurrencia > 3. Un timeout o una
   conexión cortada no tumba la corrida: queda como HTTP 599 (alerta de error).
2. **Salida** en `~/Downloads/finanzer_vigilancia/<AAAA-MM-DD>/`: `alertas.md` (lo primero que se lee),
   `comparacion.json`, `resumen.csv/md`, JSON, PDF, texto y PNG por ticker, y `meta.json` (hora, commit de
   `/api/health` o `null`, sello de `/build-stamp.json`, lo que tardó en despertar).
3. **Código de salida**: 1 si hay alguna alerta; 0 si no.

### Severidades

| Severidad | Cuándo |
|---|---|
| **Alerta · rotura de fuente** | Cambia el arquetipo, el nivel de calidad, el nivel de precio o la confianza **con el mismo código** (mismo commit, o commits sin cambios en `backend/`, `frontend/out/`, `requirements.txt` ni `build.sh`), **el precio dentro de ±0.5%** y **los mismos estados** (mismo periodo y mismas cifras). Si solo se movió la Rf (≥ 1 pb) o el precio dentro del ±0.5%, se contrasta: replay del fixture con la Rf y el precio de cada corrida (la técnica de `panel_run`). Si el replay también cambia de nivel → aviso (efecto frontera); si no → alerta. La causa cita los datos de otras fuentes que cambiaron (Finnhub: BPA, beta, forward P/E, crecimientos; acciones; ruta de datos) |
| **Alerta · error** | HTTP distinto de 200 (SPY debe dar 422), un análisis con `errors`, o un PDF que no se genera |
| **Aviso** | p95 de `/api/analysis` o `/api/pdf` > 50% peor; un campo que pasa de dato a "sin dato" (`key_metrics.*`, Altman, Piotroski, DCF); un cambio de nivel explicado por el código, el periodo de los estados, otras cifras de los estados con el mismo periodo ("la fuente cambia sin periodo nuevo, revisar"), campos que aparecen/desaparecen, el precio (> ±0.5%) o la Rf; tickers que entran o salen del panel |
| **Degradado** | Sin el commit de alguna de las dos corridas, **nunca se alerta** por un cambio de nivel: se avisa y se dice "no se puede distinguir una rotura de un cambio de código". Un sello de build distinto sí prueba cambio de código (uno igual no prueba nada) |

Corridas antiguas sin `meta.json` (F0, F1): el commit se puede declarar con `--commit-anterior` / `--commit-actual`;
`alertas.md` lo marca "declarado por el operador".

## Semana 0 (15-oct-2026)

- Comando: `cd backend && ../.venv313/bin/python tests/vigilancia.py --prev ~/Downloads/finanzer_f1_panel_2026-10-15/live`
  (corrida de 14:03:03 a 14:05:48 NY; salida: "corrida en /Users/joseestebanroa/Downloads/finanzer_vigilancia/2026-10-15
  · commit desconocido · despertar 0.3 s" y "0 alertas, 1 avisos").
- 32 tickers, todos con HTTP 200 salvo SPY (422, el esperado); 31 PDF generados; ningún `errors`.
- `meta.json`: `commit: null` (producción `8ed57a0` aún no expone el commit: llega con `356f49c` de la 2a), sello
  de build `3829bd87…`. El servicio ya estaba despierto (lo desperté a las 13:59:49: **42.7 s**).
- Latencias (concurrencia 3): `/api/analysis` p50 6.66 s · p95 11.59 s · máx 14.56 s; `/api/pdf` p50 7.73 s · p95
  11.98 s · máx 13.08 s (F1 a las 10:46: 6.91 / 12.18 / 14.03 y 8.39 / 12.48 / 15.20).

## Validación contra F0 y F1

Salidas de cada comparación en `~/Downloads/finanzer_f7_validacion_2026-10-15/val_*/alertas.md`. Commits declarados
según la bitácora: F0 live contra producción `9e78f3b` (registro #4/#5); F1 live tras el push `4e90ff6` (registro
#15); semana 0 contra `8ed57a0` (estado actual; `git diff 4e90ff6 8ed57a0 -- backend/ frontend/out/` vacío).

| Comparación | Commits | Código según la herramienta | Alertas | Avisos (resumen) |
|---|---|---|---|---|
| Semana 0 frente a F1 | sin declarar | desconocido | 0 | JNJ exigente → razonable: precio 259.41 → 254.05 (−2.1%) y beta de Finnhub distinta; "no se puede distinguir…" |
| Semana 0 frente a F1 | 4e90ff6 → 8ed57a0 | **igual** (commits sin cambios en backend/ ni frontend/out/) | 0 | JNJ "explicado por: precio −2.1%; cambian datos de otras fuentes: key_metrics.beta" |
| Semana 0 frente a F0 | sin declarar | desconocido | 0 | BCS entra; JNJ confianza alta → media; NVO atractivo → razonable (+3.5% de precio); dividend yield y shareholder yield a "sin dato" en NVDA, NVO y TSM; todos con "no se puede distinguir…" |
| Semana 0 frente a F0 | 9e78f3b → 8ed57a0 | **distinto** | 0 | Los mismos, "explicado por: cambio de código (commit distinto: 9e78f3b → 8ed57a0)" |
| F1 frente a F0 | sin declarar / 9e78f3b → 4e90ff6 | desconocido / distinto | 0 / 0 | JNJ razonable → exigente (Finnhub impone `epsTTM`: cita `key_metrics.eps` como otra fuente); NVO; los tres "sin dato"; BCS |
| Inyección: KO con el nivel de precio cambiado a mano, mismo commit, precio y datos | 8ed57a0 → 8ed57a0 | igual | **1** (rotura de fuente) | — · código de salida **1** |

Lectura:
- Entre F0 y hoy cambió el código (fase 1): con el commit, la herramienta lo atribuye a "commit distinto" y no
  alerta; sin él, lo dice y degrada a aviso. Es lo que pide el prompt.
- Los "sin dato" de NVDA, NVO y TSM son el control de identidad del dividendo de la fase 1 (`bfc38e9`): esperados.
  (NVDA es un falso positivo ya registrado por la 2a, mapa de pendientes.)
- `key_metrics.net_interest_income` aparece entre F0 y F1 en JNJ y NVO: campo nuevo de la fase 1, no dato de la
  fuente; la herramienta lo separa como "campos que aparecen o desaparecen".
- El contraste con el replay (efecto frontera) no se disparó en estas comparaciones (todos los cambios tenían otra
  causa); está cubierto por los tests y se probó a mano sobre JNJ (`replay_counterfactual` con la Rf y el precio
  de F1 y de la semana 0: nivel de precio "razonable" en los dos, confianza media → alta).

## Tarea programada (creada el 15-oct-2026 con el permiso del usuario: `finanzer-vigilancia-semanal`)

| | Propuesta |
|---|---|
| Cuándo | **Sábados a las 09:00** (hora del Mac). Mercado cerrado: el precio es el cierre del viernes y la comparación entre semanas es estable; lejos de cualquier ventana de captura |
| Qué ejecuta | Hasta que la rama se fusione: `cd /Users/joseestebanroa/Downloads/finanzer_next-f67prep/backend && /Users/joseestebanroa/Downloads/finanzer_next/.venv313/bin/python tests/vigilancia.py`. Tras la fusión: el mismo comando en un worktree dedicado sobre `main` (no en la carpeta principal, que cambia de rama con cada operador) |
| Dónde deja el resultado | `~/Downloads/finanzer_vigilancia/<AAAA-MM-DD>/alertas.md` (compara sola con la corrida anterior de esa carpeta) |
| Cómo avisa | Tarea programada de Claude (app de escritorio): ejecuta el comando, lee `alertas.md` y envía una notificación con la línea de resumen; si el código de salida es 1, la notificación lista las alertas por ticker. Requiere el Mac encendido y la app abierta a esa hora |
| Coste | ≈ 3 min; 32 análisis + 32 PDF contra producción a concurrencia 3; ≈ 32 consultas a Finnhub desde producción (límite 60/min) |

Texto de la tarea (el que quedó guardado, con dos reglas más: responder en español y no forzar la ventana prohibida):

> Vigilancia semanal del panel de Finanzer (fase 7). Ejecuta en una terminal:
> `cd /Users/joseestebanroa/Downloads/finanzer_next-f67prep/backend && /Users/joseestebanroa/Downloads/finanzer_next/.venv313/bin/python tests/vigilancia.py`
> No cambies código, no hagas commit ni push, no lances otras peticiones a finanzer.app ni a Finnhub, y no imprimas
> secretos. Cuando termine, lee `~/Downloads/finanzer_vigilancia/<fecha de hoy>/alertas.md` y avísame en español con
> la línea de resumen. Si el código de salida es 1, enumera cada alerta con su ticker y su causa. Si el comando
> falla antes de comparar, dime el error tal cual.

## Límites conocidos

- **Sin commit en producción** hasta que se despliegue `356f49c`: hasta entonces todo cambio de nivel sale como aviso
  "no se puede distinguir". Alternativa provisional (no aplicada): declarar `--commit-actual` con `origin/main`, que
  Render despliega automáticamente (supuesto, no prueba).
- El contraste del efecto frontera usa el código y los fixtures del worktree, no los de producción: si el código local
  difiere de producción, el contraste deja de valer (la herramienta no lo comprueba).
- Cuando la 2a añada HSBC, SHEL, UL y TM al panel, la primera semana saldrán como "entra en el panel" (aviso).
- La huella de "estados" es una selección de campos de `key_metrics`, `yearly_financials` y `data_provenance.ttm`;
  un cambio de fuente en un campo fuera de esa lista que mueva el nivel se leería como rotura (falso positivo
  posible, nunca un falso negativo por ese motivo).
