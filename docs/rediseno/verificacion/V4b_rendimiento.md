# V4b · 3 — Sin lag, medido

Literal del usuario (2026-10-18): *«mucho lag cuando entro a una sección y trato de que aparezcan las subsecciones… las
quiero fijas y sin lag… Veo mucho lag en varios sitios. revisa bien»*.

## Cómo se mide

- **Prueba:** `frontend/e2e/perf/rendimiento.spec.ts`, con `playwright.perf.config.ts`.
- **Contra qué:** el build de producción (`frontend/out`) servido por el replay del panel, como en producción, con AAPL.
- **Umbrales (en la config):** `backend/config/data.toml [web] perf_*`, generados a `WEB.perf`:

| Medida | Objetivo |
|---|---|
| Cambio de sección con el análisis ya cargado, hasta el contenido pintado | ≤ 150 ms |
| INP p75 de las interacciones | ≤ 200 ms |
| Tarea larga durante una interacción | ≤ 100 ms |
| Tarea larga al desplazar | ≤ 50 ms (definición del navegador) |

- **Navegadores:**
  - `chromium-x4`: escritorio a 1440 px, con la CPU 4 veces más lenta (CDP `Emulation.setCPUThrottlingRate`).
  - `chromium-movil-x4`: Pixel 7 a 375 px, CPU ×4.
  - `webkit`: Safari de escritorio. WebKit no admite ralentizar la CPU.
- **Qué se mide en cada interacción:** el tiempo desde la entrada (`pointerdown`, la tecla o `pointerup` en el carrusel) hasta que el contenido esperado está en el DOM y se pinta el fotograma siguiente.
  - En Chromium, además: las tareas largas (`longtask`) y el INP de Event Timing.
  - WebKit no tiene esas dos APIs. Allí el INP es esa misma medida, de la entrada al pintado, y la «tarea larga» es un hueco entre fotogramas.
- **Interacciones:**
  - las 8 pestañas, más la vuelta a una sección ya visitada;
  - dos «?» y su cierre;
  - el periodo de la gráfica (5A, 1M, 1A);
  - los tres escenarios de «Cuánto vale»;
  - el carrusel de la portada (arrastrar y soltar).
- **Desplazamiento:** con la rueda, 30 × 300 px, en «Calidad», «Cuánto vale» y «Cómo gana dinero».
- **Reposo:** 2 s quieto en una sección.

Para reproducirlo:

```bash
cd frontend && npm run build && npm run e2e:perf
```

Después hay que restaurar `frontend/out`, que está versionado:

```bash
git checkout -- frontend/out && git clean -fdq frontend/out
```

## Resultado

Las cifras en ms. «Antes» es la v4 con los bloques 1 y 2; «después», con el arreglo de este bloque. Informes completos en `docs/rediseno/verificacion/V4b_rendimiento/{antes,despues}-<proyecto>.json`.

| | Chromium ×4 escritorio | Chromium ×4 móvil | WebKit |
|---|---|---|---|
| **Cambio de sección (8 pestañas), antes** | **332–359** | **331–356** | **330–336** |
| **Cambio de sección, después** | **28–89** | **36–105** | **17–34** |
| Vuelta a una sección ya vista, antes → después | 47 → 48 | 48 → 62 | 30 → 32 |
| «?» abrir / cerrar, después | 26–31 / 14–16 | 29–35 / 18–22 | 33–54 / 17–19 |
| Periodo de la gráfica, después | 36–87 | 44–102 | 16–19 |
| Escenario, después | 15–25 | 16–23 | 14–17 |
| Carrusel (soltar), después | 32 | 17 | 14 |
| **INP p75, antes** | 32 (Event Timing) | **331** | **332** |
| **INP p75, después** | 32 (Event Timing) | 57 | 31 |
| Tareas largas en interacciones, antes y después | ninguna | ninguna | ningún hueco > 100 ms |
| Desplazar (tareas > 50 ms), antes y después | ninguna | ninguna | ningún hueco |
| Reposo (2 s) | sin tareas largas | sin tareas largas | — |
| **Umbrales incumplidos, antes → después** | **8 → 0** | **9 → 0** | **9 → 0** |

En Chromium de escritorio, Event Timing solo registra las interacciones de más de 16 ms. Registró una, de 32 ms; las demás quedaron por debajo de 16 ms.

## La causa del lag al entrar en una sección

El cambio de sección tardaba unos 330 ms en los tres navegadores, también en WebKit, que va sin ralentizar. En cambio, volver a una sección ya vista tardaba 30–48 ms. Una cifra fija, que solo aparece la primera vez, no es cálculo. Es una espera.

1. Cada sección es su propio fragmento: `React.lazy` + `Suspense`, en `src/v2/lib/lazy.tsx`.
2. La primera vez, la sección suspende y enseña su esqueleto.
3. React 19 retiene el contenido unos 300 ms tras enseñar un esqueleto (su *throttle* de fallbacks). Lo hace aunque el fragmento llegue en 1 ms: el replay lo sirve en ~1 ms.

Lo confirma la traza de Chromium: entre los clics de las pestañas pasaban unos 370 ms, y el hilo principal estaba casi parado. En la ventana de las 8 pestañas, 668 ms de CPU repartidos en 3,2 s.

**El arreglo, en origen (`lazy.tsx` y `StoryPageClient.tsx`):**

- Un fragmento ya descargado se pinta directo, sin Suspense.
- Con el detalle de la sección abierta ya pintado, las demás y sus gráficas se descargan en un momento libre: `requestIdleCallback`, o 500 ms en Safari, que no lo tiene. Así el fragmento de la sección abierta va primero, sin competir.

Ahora cambiar de pestaña no espera ni a la red ni a Suspense. En la traza de después, las 8 pestañas caben en 1 s.

## Los sospechosos del PM, uno a uno

- **Escuchas de `pointermove` en `document` por tarjeta (V6b E10):** ya no existen. Las quitó el bloque 2, junto con el panel del desglose.
- **`autoUpdate` de floating-ui:** solo mientras un «?» está abierto. Abrir y cerrar un «?» tarda 14–54 ms.
- **Lightweight Charts recreada en cada render:** no se recrea por render. Solo al cambiar el periodo, los datos o el tema, que son sus dependencias. El periodo cuesta 36–102 ms con CPU ×4, sin tareas largas. Queda por debajo del umbral, así que no se toca.
- **Observadores de la barra:** el scroll-spy de la historia desapareció con el bloque 1. Quedan:
  - un IntersectionObserver y un ResizeObserver para la cabecera fija; cambian un atributo, sin repintar React;
  - el índice de píldoras, una lectura por fotograma al desplazar.
  
  Desplazar no da ninguna tarea larga.
- **El `requestAnimationFrame` del cintillo fuera de la portada:** se cancela al desmontar el cintillo (`useCarousel.ts`). En reposo en una sección no hay tareas largas.
- **DOM enorme de la página-historia:** desapareció con el bloque 1.

## Trazas

- **Qué son:** trazas de Chromium (`browser.startTracing`) de las 8 pestañas, antes y después, en escritorio y en móvil.
- **Dónde están:** en la carpeta de notas compartida del PM, `trazas-v4b-rendimiento/*.json.gz` (≈ 0,4–0,7 MB cada una), porque pesan ~9 MB sin comprimir. Se abren en `chrome://tracing` o en Perfetto.
- **Tarea larga que no es de la web:** la de más de 100 ms en ellas (126 ms antes, 149 ms después) es el arranque de la propia traza: interrupciones de V8 en el milisegundo 2, antes del primer clic.
- **La interacción más pesada después del arreglo:** pintar «Calidad», la sección con más DOM. Es una tarea de 53 ms con la CPU ×4: 46 ms de React dentro del propio clic y 18 ms de maquetación. Queda por debajo del umbral de 100 ms, y la sección llega pintada a los 80 ms.
