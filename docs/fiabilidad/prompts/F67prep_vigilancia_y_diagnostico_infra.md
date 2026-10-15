# Prompt del operador — F67prep: vigilancia semanal (fase 7) y diagnóstico de infraestructura (fase 6)

> Copia todo lo que hay debajo de la línea en un chat nuevo de Claude Code abierto en
> `/Users/joseestebanroa/Downloads/finanzer_next`. **Trabaja en un worktree aparte**: en paralelo hay otros operadores
> en las ramas `fiabilidad/f2a-medir` (carpeta principal), `fiabilidad/f3-prep` y `fiabilidad/f5-prep` (worktrees
> `../finanzer_next-f3prep` y `../finanzer_next-f5prep`). No toques sus archivos ni sus worktrees.
>
> Borrador redactado por el operador de la 2a a petición del usuario (2026-10-15), para avanzar lo que no depende de
> la captura del cierre de Nueva York. El planificador puede revisarlo.

---

Eres el **operador de F67prep** del plan de fiabilidad de Finanzer. Haces dos trabajos **que solo miden y vigilan**:

1. **Vigilancia semanal (fase 7, parte 1):** una herramienta que corre el panel contra producción, lo compara con la
   corrida anterior y avisa de lo que no debería cambiar.
2. **Diagnóstico de infraestructura (fase 6, solo diagnóstico):** dónde se va el tiempo de un análisis y del PDF, y
   por qué producción atiende en serie.

**No cambias el motor ni la app.** No tocas `backend/main.py`, `backend/lib/`, el PDF, la web, `render.yaml`,
`build.sh`, `tests/fixtures/panel/` ni `tests/golden/`. Tus herramientas viven en `backend/tests/` o `backend/tools/`.
Ninguna salida de la app cambia.

## 1. Contexto (lee antes de tocar nada)

**Los documentos de planificación están sin commitear en la carpeta principal** y no aparecerán en tu worktree. Léelos
por su ruta absoluta en `/Users/joseestebanroa/Downloads/finanzer_next/docs/`:

1. `PLAN_FIABILIDAD.md`:
   - §4, fase 6: objetivo p95 < 6 s en frío y < 1 s en caliente; 12 peticiones sin cola;
   - §4, fase 7: vigilancia semanal; rotura de fuente = cambio de veredicto sin cambio de precio ni de datos;
   - §5: protocolo de revisión;
   - §6: D6.
2. `fiabilidad/BITACORA.md`: estado, decisiones (**D6 decidida:** servicio siempre encendido en Render, pendiente de
   que lo contrate el usuario) y el registro.
3. `fiabilidad/F0_LINEA_BASE.md`: latencias de partida.
   - `/api/analysis`: p50 6.7 s, p95 45.9 s, máximo 52.5 s.
   - `/api/pdf`: p50 7.9 s.
   - JPM en frío: 46.1 s.
   - "Producción atiende en serie."
4. `RECON.md` §7 (historia técnica) y `backend/tests/README.md`.
5. **En el código (tu worktree):**
   - `backend/tests/panel_run.py`: modo `live`, `--compare` y la sección "Live frente a replay", que separa la Rf,
     el precio intradía y las diferencias reales;
   - `backend/tests/fixture_backend.py`: el replay sin red;
   - `backend/main.py` (solo lectura): los endpoints y si son `async def` con código bloqueante dentro;
   - `backend/lib/data_fetcher.py`: `SimpleCache` en memoria y sus TTL;
   - `render.yaml` / `build.sh` / el comando de arranque (solo lectura).

Hechos:
- Producción y `main` = `8ed57a0`.
- Render **se apaga sin tráfico**: despiértalo antes de medir y no cuentes la primera petición como fallo.
- `/api/health` aún no devuelve el commit desplegado: está hecho en la 2a, sin desplegar. Tu herramienta debe
  aceptar `commit: null` o que falte la clave.
- Suite: `cd backend && /Users/joseestebanroa/Downloads/finanzer_next/.venv313/bin/python -m pytest tests -q`.

## 2. Reglas que no se rompen

- **finanzer.app: concurrencia ≤ 3, siempre.** La prueba de "12 peticiones simultáneas" del plan **no se hace contra
  producción**. Se estima con medidas en serie y a concurrencia 3 (§T5), y se deja diseñada para cuando haya un
  entorno de pruebas o tras D6.
- **Ventana prohibida: de 15:55 a 16:45 (hora de Nueva York)** no lances nada en vivo contra finanzer.app ni contra
  Finnhub.
  - **Por qué:** a las 16:15 la 2a captura con Finnhub y la F5prep descarga series de Yahoo.
  - **Finnhub:** la clave de producción y la local son la misma, con un límite de 60 por minuto.
  - **Antes de cada corrida en vivo,** mira la hora con `TZ=America/New_York date`.
- **Ningún secreto en el repo, en las salidas ni en el chat.** La clave de Finnhub vive en el Llavero
  (`finanzer-finnhub`); solo se exporta en línea si hace falta, y no debería hacer falta: medir producción no la
  necesita.
- **No crees ninguna tarea programada sin el permiso explícito del usuario**: es configuración persistente. La dejas
  diseñada y lista, y preguntas en el punto de parada.
- **No pushees sin un "ok, pushea" explícito.** Un commit por causa, con prefijo `F67prep:`.
- Toda afirmación de "hecho" o "pasa" va con el comando y su salida.
- Al cerrar la sesión, aunque quede a medias, deja tu entrada en la bitácora: es el archivo de la carpeta principal,
  así que añade **solo tu entrada al final**, sin tocar el resto.

## 3. Tareas

### T0. Worktree
`git worktree add ../finanzer_next-f67prep -b fiabilidad/f67-prep main`.

### T1. `backend/tests/vigilancia.py` (fase 7)

1. **Corrida:** reutiliza `panel_run` en modo `live` (no lo dupliques): todos los tickers del panel contra
   `https://finanzer.app`, concurrencia 3.
   - Despertar primero (una petición a `/api/health`, descartada).
   - Guarda en `~/Downloads/finanzer_vigilancia/<AAAA-MM-DD>/`, con `resumen.csv`, JSON y PDF por ticker, más un
     `meta.json` con la hora, el commit de `/api/health` (o `null`) y el sello de build (`/build-stamp.json`).
2. **Comparación** con la corrida anterior (la carpeta más reciente, o la que se pase con `--prev`). Clasifica cada
   cambio con tres severidades:
   - **Alerta, rotura de fuente:** cambia el arquetipo, el nivel de calidad, el nivel de precio o la confianza
     **sin** que cambien ni el commit ni el precio (±0.5%) ni los datos de los estados. Usa la separación de
     `panel_run` entre Rf, precio y diferencias reales.
   - **Alerta, error:** HTTP distinto de 200 (salvo SPY, que espera un 422), un análisis con `errors`, o un PDF que
     no se genera.
   - **Aviso:** p95 de `/api/analysis` o de `/api/pdf` más de un 50% peor que la corrida anterior; un campo que pasa
     de dato a "sin dato"; un nivel que cambia con el precio o con datos nuevos, explicado.
3. **Salida:** `alertas.md` legible (lo primero que lee el usuario), con:
   - el resumen arriba;
   - las alertas por ticker con su causa;
   - las latencias p50, p95 y máxima frente a la corrida anterior.

   Código de salida distinto de 0 si hay alguna alerta.
4. **Tests sin red** (`tests/test_vigilancia.py`): la lógica de comparación sobre resúmenes sintéticos. Que **detecta**
   una rotura de fuente, un error y una regresión de latencia, y que **no alerta** por un cambio de precio o de Rf.

### T2. Primera corrida (semana 0) y validación
- Antes de las 15:55 de Nueva York (si no llegas, después de las 16:45): primera corrida real. Es la **semana 0**.
- **Valida la comparación** contra las dos corridas en vivo que ya existen:
  - `~/Downloads/finanzer_f0_panel_2026-10-14/live` (fase 0, antes del deploy de la fase 1);
  - `~/Downloads/finanzer_f1_panel_2026-10-15` (si contiene una corrida en vivo; míralo).
- Entre F0 y hoy cambió el código (deploy de la fase 1), así que la herramienta **debe** atribuir los cambios a
  "commit distinto" y no a rotura de fuente. Si no tiene el commit, debe decir que no puede distinguirlo y degradar a
  aviso.

### T3. Diseño de la tarea programada (sin crearla)
- **Propuesta:** semanal, el **sábado por la mañana** (mercado cerrado: el precio es el cierre del viernes y la
  comparación entre semanas es estable).
- Fija la hora, qué ejecuta (el comando exacto), dónde deja `alertas.md` y cómo avisa al usuario.
- Deja preparado el texto de la tarea, pero **pregunta al usuario antes de crearla**.

### T4. Diagnóstico local del tiempo (fase 6, sin red)
- **Perfilado:** `cProfile` del análisis completo (`fixture_backend.run_analysis`) y del PDF (`build_pdf_bytes`) en
  replay, para los 6 de `local` y 6 del panel de arquetipos distintos. Tiempo de CPU por módulo y por función
  (top 15).
- **Llamadas externas** por análisis, desde los fixtures: cuántas peticiones a Yahoo HTTP, cuántos accesos de
  yfinance, a Finnhub y a tipos de cambio.
  - Con la latencia típica de cada fuente, estima el **tiempo de red** de un análisis en frío.
- **Qué se cachea hoy** (`SimpleCache` y sus TTL) y qué se pierde cuando Render se apaga.

### T5. Diagnóstico en producción (fase 6, solo medir)
- **Lectura del código:** por qué producción atiende en serie.
  - Hipótesis a verificar: endpoints `async def` que ejecutan código bloqueante (yfinance, requests, reportlab)
    dentro del bucle de eventos, con un solo worker de uvicorn.
  - Comprueba también el comando de arranque y el número de workers.
- **Medida con el servidor despierto:**
  - 6 tickers en serie (concurrencia 1) y los mismos 6 a concurrencia 3, en `/api/analysis` y `/api/pdf`;
  - primera petición (caché fría del proceso) frente a la segunda del mismo ticker (caché caliente).
  - Si la latencia a concurrencia 3 ≈ 3 × la de concurrencia 1, se confirma la cola en serie.
- **Estimación de 12 simultáneas** con lo medido (modelo de cola en serie frente a N workers). **No la ejecutes.**

### T6. Informe → **PUNTO DE PARADA**
- `docs/fiabilidad/F6_DIAGNOSTICO.md` (en tu worktree), con:
  - el desglose del tiempo (CPU local, red estimada, cola);
  - la causa de la atención en serie, con la prueba en el código y la medida;
  - qué resuelve cada opción y cuánto (D6 siempre encendido, más workers, ejecución fuera del bucle de eventos,
    caché persistente de estados), **con la medida que lo respalda**;
  - qué depende de D2 (no cachear la fuente equivocada).
- `docs/fiabilidad/F7_VIGILANCIA.md`: cómo se usa la herramienta, la semana 0 y la validación con F0/F1.
- **Detente y presenta** las dos cosas. Pide:
  1. **permiso para crear la tarea programada semanal** (T3);
  2. **el "ok, pushea"** para la rama, si el usuario quiere subirla. Son solo herramientas de test y documentos; aun
     así, el push redespliega.

## 4. Definición de terminado

- [ ] `vigilancia.py` con tests sin red que prueban que detecta (rotura de fuente, error, latencia) y que no alerta
  por precio o Rf.
- [ ] Semana 0 corrida y validada contra F0/F1, con `alertas.md`.
- [ ] Tarea programada diseñada y **pendiente del permiso del usuario**.
- [ ] `F6_DIAGNOSTICO.md` con el desglose, la causa de la cola y las opciones medidas; sin ninguna prueba de 12
  simultáneas contra producción.
- [ ] Bitácora: tu entrada al final del registro.
