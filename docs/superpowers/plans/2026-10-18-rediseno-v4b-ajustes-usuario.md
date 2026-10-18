# Rediseño · V4b: ajustes del usuario tras probar la demo — Plan

> Literal del usuario (2026-10-18, tras probar el build de la v4): *"mucho lag cuando entro a una sección y trato de que
> aparezcan las subsecciones… no quiero subsecciones ocultas, las quiero fijas y sin lag. No puede ser que exista una
> pestaña donde salga todo. quiero mi análisis seccionado y el detalle dentro de la sección. Veo mucho lag en varios
> sitios. revisa bien. Muchos cuadros sin colores o bien indicados. muchos fallos de información faltante. lo de que la
> animación de la página principal tarde 1.5s en arrancar luego de quitar el mouse es terrible. que arranque apenas
> quito el mouse… me gusta lo que veo pero hay que ir ajustando mejor"*.

**Cambio de la spec.** La página-historia única (todos los capítulos en una página con índice, spec §3) se sustituye por
un **análisis seccionado**: cada capítulo es su propia sección (pestaña con ruta) y lleva dentro su lectura y todo su
detalle. Ya no hay una página que lo muestre todo. El PDF no cambia (ya va por capítulos).

## Decisiones del PM

- **Estructura.** `/v2/{T}` abre la sección «La empresa». Las 9 secciones son pestañas reales con ruta propia
  (`/v2/{T}/empresa`, `/negocio`, `/accion`, `/calidad`, `/valor`, `/rivales`, `/riesgos`, `/actualidad`,
  `/conclusion`); se mantienen las rutas de las páginas de profundidad actuales que ya existen (redirigen a la sección
  equivalente si cambian de nombre). La cabecera (identidad, precio, conclusión y las tres puntuaciones) queda fija
  arriba en todas las secciones (compacta al hacer scroll, como ahora) y la barra de secciones debajo. Cada sección =
  la lectura del capítulo (lo que hoy es el bloque de la página-historia) + todo el detalle de su página de
  profundidad, sin repetir. «Siguiente sección →» al final de cada una.
- **Nada oculto.** El desglose de las tres puntuaciones va siempre visible (no al pasar el ratón ni tras «Ver
  detalle»); nada de acordeones, «Ver más» ni hojas para contenido. Los «?» se quedan (son ayuda, no contenido) y deben
  abrir al instante.
- **Sin lag** (medido, no a ojo): build de producción, Chromium con CPU ×4 más lenta (perfil de portátil modesto) y
  WebKit. Objetivos: cambio de sección con el análisis en caché ≤ 150 ms hasta el contenido pintado; INP p75 ≤ 200 ms en
  todas las interacciones (pestañas, «?», periodo de gráficas, escenario, carrusel); ninguna tarea larga > 100 ms
  durante una interacción; scroll a 60 fps (sin tareas largas). Sospechosos a medir antes de tocar: listeners de
  `pointermove` en `document` por tarjeta (V6b E10), `autoUpdate` de floating-ui, gráficas de Lightweight Charts
  recreadas en cada render, observadores de la barra, el `requestAnimationFrame` del cintillo fuera de la portada, DOM
  enorme de la página-historia (desaparece con las secciones). Informe con trazas antes/después.
- **Colores.** Auditoría de todos los cuadros, tablas y tarjetas de las 9 secciones en AAPL, JPM, PLTR, O y BCS: todo
  valor con lectura lleva su tono (verde, ámbar, teja o gris neutro explícito) y una pastilla o texto que lo diga; si el
  tono falta en `display`, se añade en el motor (sin cambiar veredictos). Cero valores con lectura y sin color.
- **Información faltante.** Auditoría de cada «Sin dato», «—» o hueco en el panel completo (37 + MC.PA) por sección:
  clasificar (a) la fuente no lo publica / no aplica → motivo claro en su sitio, sin cuadro vacío; (b) el dato existe en
  el análisis o en otra fuente y no se cablea → arreglarlo; (c) falta en los fixtures del replay → recapturar. Informe
  con el recuento antes y después.
- **Cintillo.** Arranca **en cuanto** sale el ratón (0 ms). Tras arrastrar o desplazar con el ratón fuera, arranca al
  terminar la inercia. Con el ratón encima, parado.

## Reparto

- **E3 (sesión E2b, rama `rediseno/v4`):** estructura seccionada, nada oculto, lag y colores. Se detiene la pasada final
  en curso: se repite completa después.
- **E4 (sesión E2a, rama nueva `rediseno/v4b-datos` desde la punta de la v4):** cintillo a 0 ms y la auditoría de
  información faltante (arreglos del motor y de datos en su rama; lo que sea de presentación, a E3 vía el PM).
- Después: fusión, pasada final completa (V1–V5), `V4_CIERRE.md` y aviso al usuario.
