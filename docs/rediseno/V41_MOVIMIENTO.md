# v4.1 · Movimiento — auditoría y propuesta

Rama `rediseno/v41-movimiento` (desde `820fde39`). El usuario: «la app funciona perfecto, pero es demasiado tosca y
brusca en su navegación interna. Todo se mueve de golpe y el desplazamiento es brusco. Quiero algo suave, sutil, que el
cambio de pestañas y opciones dé una sensación de iPhone».

Criterio: skills improve-animations (catálogo de Emil Kowalski) y apple-design (respuesta inmediata, interrumpible,
resortes sin rebote, entrar y salir por el mismo camino, reducir movimiento ≠ nada).

## 1. Auditoría (estado de `main`)

Hoy /v2 casi no tiene movimiento: tres reglas (el giro del PDF, la pantalla de carga y la cabecera fija), sin tokens de
curvas ni duraciones, y una regla global que, con «reducir movimiento», quita todo, incluidos los fundidos.

| # | Gravedad | Dónde | Qué pasa hoy | Propuesta |
|---|---|---|---|---|
| 1 | Alta | Cambio de capítulo: `StoryPageClient.tsx:251` (`<DepthPage key={section}>`) | la sección vieja desaparece y la nueva aparece en el mismo fotograma | la nueva entra con fundido y 16 px desde el lado del cambio (adelante: desde la derecha; atrás: desde la izquierda), 320 ms |
| 2 | Alta | Salto de scroll: `StoryPageClient.tsx:29-36` (`scrollIntoView()` sin `behavior`) | salto instantáneo al principio de la sección, a la vez que el cambio de contenido; volver a una pestaña la abre siempre arriba; el navegador restaura y el código vuelve a saltar (doble salto) | la posición de lectura se conserva por pestaña (volver la abre donde estaba); `scrollRestoration = "manual"` |
| 3 | Alta | Píldoras: `PillIndex.tsx:35` (`href="#id"` nativo) | teletransporte al apartado, un segundo salto por `popstate` y una entrada de historial por toque | desplazamiento suave al apartado; la píldora queda activa desde el toque, sin parpadear las de en medio; `replaceState` |
| 4 | Alta | Hoja inferior: `Floating.tsx:219, 237-239` | la hoja y el velo aparecen y desaparecen de golpe; el arrastre no sigue al dedo: a 80 px se cierra de golpe | la hoja sube desde abajo (320 ms, curva de hoja de iOS) y el velo se funde; el arrastre la mueve 1:1; al soltar, se cierra si pasó el 25 % de su alto o con un gesto rápido (> 0,11 px/ms), si no vuelve a su sitio |
| 5 | Alta | Ayudas en escritorio: `Floating.tsx:244`, `v2.css:437` | el panel aparece a tamaño completo, sin relación con su «?» | nace de su «?» (escala 0,96 → 1 y fundido, origen en la esquina del ancla), 150–220 ms; al cerrar, el mismo camino de vuelta |
| 6 | Media | Pantalla de carga → contenido: `v2.css:885`, `backendConfig` (`exitHoldMs 320 + exitMs 620`) | ~940 ms de disolución con curva lenta al arrancar, a un fondo vacío, y después la página de golpe | pausa 200 ms y fundido cruzado directo a la página (View Transitions; sin ella, 260 ms con ease-out) |
| 7 | Media | Portada → acción: `TickerStrip.tsx:54`, `SearchBox.tsx:79` | navegación completa: pantalla en blanco y la página nueva de golpe | transición entre documentos (`@view-transition`): fundido cruzado y la barra superior quieta |
| 8 | Media | Marca de la pestaña activa: `v2.css:277` | el subrayado salta de una pestaña a otra | una sola marca que se desliza (transform, 220 ms) |
| 9 | Media | Toques: sin `:active` en todo /v2 | los botones no responden al dedo | ceden a 0,97 al tocar (150 ms), al instante |
| 10 | Media | Modo claro/oscuro: `theme.ts:37` | cambio de color instantáneo a pantalla completa | fundido cruzado de 220 ms (pendiente) |
| 11 | Media | Chips y periodo de la portada: `home.css:15-24`, `TickerStrip.tsx:105-127` | el estado activo salta; al cambiar de periodo el cintillo se vacía un instante; al cargar, el esqueleto mide 112 px menos que el cintillo (CLS 0,031) | indicador del periodo que se desliza; el cintillo conserva sus tarjetas hasta que llegan las nuevas y las cambia con un fundido (pendiente) |
| 12 | Media | Cintillo al tocar: `useCarousel.ts:285-290` | el arrastre ya es bueno (resorte que hereda la velocidad del dedo); el avance solo arranca y para a toda velocidad | rampa de velocidad de 400 ms al reanudar (pendiente) |
| 13 | Media | Gráfica al cambiar de rango: `PriceChartFull.tsx:36-75` | se destruye y se vuelve a crear la gráfica entera | conservar la gráfica y cambiar los datos, con un fundido breve (pendiente) |
| 14 | Alta (CLS) | Gráfica perezosa: `Accion.tsx:17-18` | el hueco es una línea de texto y la gráfica mide 26 rem: todo lo de debajo baja ~400 px | usar el esqueleto del tamaño real (`PriceChartSkeleton`, ya existe sin usar) (pendiente) |
| 15 | Media | Aviso del PDF: `v2.css:105-110`, `PdfButton.tsx` | el aviso aparece y desaparece de golpe | sube 8 px con fundido (220 ms) y sale igual (pendiente) |
| 16 | Media | Reducir movimiento: `v2.css:114` | quita todo, también los fundidos; la carga espera ~1 s quieta y luego corta | sin desplazamientos ni escalas; fundidos breves o nada; la carga no espera su disolución |

## 2. Lenguaje de movimiento (tokens en `v2.css`, `:root`)

```css
--ease-out:   cubic-bezier(0.23, 1, 0.32, 1);   /* resorte sin rebote: arranca rápido y se posa */
--ease-sheet: cubic-bezier(0.32, 0.72, 0, 1);   /* hojas: la curva de las de iOS */
--dur-1: 150ms;  /* lo pequeño: toques, ayudas, salidas */
--dur-2: 220ms;  /* lo que cambia en su sitio: indicadores, chips */
--dur-3: 320ms;  /* lo que entra desde fuera: secciones, hojas, páginas */
--shift: 16px;   /* desplazamiento de una sección que entra */
```

Reglas: solo `transform` y `opacity`; nada interrumpe ni retrasa la lectura (toda entrada es interrumpible: un toque
nuevo manda); el mismo camino de vuelta al cerrar; con «reducir movimiento», fundidos de 150 ms o nada; el zoom no se
toca (el viewport no lo bloquea).

Pestañas: se probó primero la View Transitions API (el contenido viejo sale y el nuevo entra), pero retiene el
siguiente fotograma para capturar la vista y subía la respuesta del toque (INP) de 48 a 72 ms en escritorio. Se queda
para lo que no es un toque (carga → página, portada → acción) y el cambio de pestaña lo hace el CSS al montarse la
sección: mismo efecto de entrada, sin coste.

## 3. Implementado (aprobado por el usuario: «me gusta, aplícalo»)

Los 16 puntos. Además de lo del prototipo:
- modo claro/oscuro: fundido cruzado de 220 ms, solo color (View Transitions; sin la API o con «reducir movimiento»,
  inmediato);
- portada: el fondo del periodo activo se desliza (una capa recortada a la forma del botón: escalar deformaba la
  píldora); el cintillo conserva sus tarjetas hasta que llegan las del periodo nuevo y las cambia con un fundido de
  220 ms; el avance automático arranca con una rampa de 400 ms (se para al instante al tocarlo);
- gráfica de La acción: se crea una vez y al cambiar de rango solo cambian sus datos, con un fundido breve; mientras
  llega su fragmento, un esqueleto del mismo alto (26 rem; 20 en el móvil);
- aviso del PDF: sube 8 px con un fundido y se va igual, con lo que decía;
- volver a una pestaña: si su detalle aún no ha llegado, la vuelta a donde se leía se reintenta mientras la página
  crece (hasta 1,5 s o hasta que el lector se mueva); mientras se coloca la vista, los desplazamientos no se anotan como
  «dónde se leía».

Ayuda de «Precio» (§4): corregida en origen. La ficha del precio se llama `share_price` (antes `price`, la misma clave
que la ayuda de la puntuación «Atractivo del precio»). Goldens del panel y locales regenerados: el único cambio es esa
clave.

Pruebas: `e2e/v2/movimiento.spec.ts` (entrada desde el lado del cambio, foco al título de la sección, la marca activa
llega a su pestaña, posición conservada por pestaña también con atrás/adelante, píldoras con anclaje bajo las barras y
sin añadir historia, «reducir movimiento» sin entrada ni suavizado ni escala, la hoja inferior sale por el mismo camino
y devuelve el foco, el cintillo nunca se vacía al cambiar de periodo y la ayuda de «Precio»); `carga.spec.ts` (con
«reducir movimiento», sin giro y fundidos ≤ 150 ms) y `ayudas.spec.ts` (el panel se mide al terminar su entrada, de
forma determinista). Los selectores de panel abierto pasan a `.tip-box:not([data-state=closed])` (el que se cierra
sigue un instante en el DOM, inerte, mientras sale).

## 4. Medidas

INP y CLS de laboratorio (`frontend/scripts/vitales-movimiento.mjs`; escritorio 1280 y móvil 390 con la CPU ×4;
recorridos: portada → lista, periodo, sector, cintillo; acción → 3 capítulos, 2 píldoras, una ayuda, modo oscuro y
vuelta). Antes: `main` (820fde39), mediana de 3; después: la rama, mediana de 5.

| Recorrido | INP antes | INP después | CLS antes | CLS después |
|---|---|---|---|---|
| Escritorio · portada | 40 ms | 32 ms | 0,031 | 0 |
| Escritorio · acción | 48 ms | 48 ms | 0,001 | 0,001 |
| Móvil · portada | 64 ms | 48 ms | 0 | 0 |
| Móvil · acción | 56 ms | 48 ms | 0 | 0 |

El 0,031 de la portada no venía del cambio de periodo (como suponía la auditoría) sino de la carga: el esqueleto del
cintillo medía 112 px menos que el de verdad (sin la fila de sectores, sin el pie y con tarjetas más bajas). Ahora el
esqueleto tiene la misma retícula, la fila de sectores y el pie: mide lo mismo en escritorio y en el móvil.

## 5. Hallazgo aparte (corregido)

La ayuda «?» de la ficha «Precio» en Cifras clave abre el texto de «Atractivo del precio» (rangos de 0 a 100) con «Tu
valor $221.30»: la clave de la ayuda no es la del precio.

## 6. Latigazo al cambiar de pestaña (corregido)

El usuario, en su iPhone con NVDA: «doy clic en Cómo gana dinero, La acción… me salta un latigazo y todo como que se
tira de golpe». En Safari de iOS (simulador, fotograma a fotograma) y en WebKit: la sección nueva se montaba y empezaba
a entrar a la vista, y uno o dos fotogramas después la página saltaba al principio de la sección. Desde arriba, la
barra de capítulos subía de golpe de media pantalla (521 px) a pegarse arriba (93 px), con el contenido al 63 % de
opacidad. A media página, la sección nueva se pintaba al scroll viejo y saltaba 1.372 px.

Ahora, como en iOS, la vista se coloca siempre invisible (`motion.switchSection`):
1. al tocar, la marca de la pestaña se desliza ya a la tocada y lo que se va a mover se funde en 100 ms: solo la
   sección si la barra ya está pegada arriba (barra y cabecera no se mueven); la página bajo la barra superior si la
   barra aún va a subir;
2. con eso invisible, cambia el contenido y la vista se coloca sin animar: al principio de la sección, o donde se leía
   (esperando a que crezca, como antes). El alto de `main` queda fijado mientras tanto para que el documento no encoja;
3. vuelve a verse: la sección entra con su fundido y sus 16 px desde el lado del cambio.

Nunca queda oculta más de 400 ms. Si llega otro toque antes de que vuelva a verse, manda el último. Atrás y adelante
del navegador siguen el mismo camino, pero sin el fundido de salida (el contenido ya cambió): se oculta en el acto. Con
«reducir movimiento», cambio y colocación inmediatos, como antes.

Prueba: `movimiento.spec.ts` · «cambiar de pestaña desde arriba / a media página no da un latigazo». Muestrea cada
fotograma (rAF) la posición de la barra, el scroll y las opacidades. Exige que, entre dos fotogramas con la página a la
vista, la barra no se mueva más de 2 px, y que el scroll solo cambie con la sección invisible (≤ 0,1). Se mide en
coordenadas de la página: Playwright WebKit retrasa 17 px su viewport visual al bajar, y no es la página la que se
mueve (antes y después del arreglo, igual; en el iPhone no pasa). Con la traza de antes del arreglo, las dos fallan.

Medida (mismo script; A/B con el mismo equipo, mediana de 5, antes y después compilados en la misma sesión): acción
escritorio INP 56 → 56 ms; acción móvil, 56 → 40 ms; portada sin cambios; CLS igual (0,001 y 0). Las cifras absolutas
de hoy van 8 ms por encima de las del §4 en ambos lados (el equipo, no el código).
