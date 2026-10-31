# Marcas de las escalas en anchos estrechos

Encargo del PM (2026-10-27, tras la pre-pasada): en tableta, las marcas de las tres escalas (calidad, precio y
confianza) se solapaban.

- La tarjeta mide unos 229 px.
- En la v4 actual, calidad se solapaba 6,6 px y precio 15–17 px.
- Con «excelente» desde 85 (F8), la marca de «excelente» se salía de la tarjeta.
- Cuatro marcas a 12 px no caben en 229 px, se pongan como se pongan.

Se pedía un diseño propio para anchos estrechos que valga con cualquier juego de umbrales, con estos criterios: nada
por debajo de 12 px, ningún solape, nada oculto y simetría con el resto de la tarjeta.

## Diseño

- **Mientras quepan, como siempre.** Las marcas van bajo sus tramos, en columnas proporcionales: nombre y, debajo,
  rango. El escritorio a 1440 px queda igual que antes.
- **Si no caben, una leyenda.** Una fila por tramo, en el orden de la barra:
  - una muestra de color (el mismo trazo de 6 px de la barra, encendido en el tramo de la empresa);
  - el nombre del tramo;
  - su rango, alineado a la derecha.
  El tramo en que cae la empresa va resaltado (seminegrita y tinta). Todo a 12 px, nada se recorta.
- **Las tres tarjetas cambian a la vez.** El corte es el de la escala que más ancho pide, así la fila conserva la
  misma forma. La base y el desglose siguen en su fila común (subgrid).
- **Funciona con cualquier umbral.** `frontend/src/v2/lib/scaleFit.ts` calcula el ancho mínimo de la tarjeta para que
  quepan las marcas, a partir de las bandas y los nombres:
  - mide los textos con los anchos de Geist, que coinciden con los del navegador (±0,2 px a 12 px), con un 2 % de
    margen;
  - exige que cada par de marcas vecinas quepa entre sus centros con 4 px de separación;
  - las marcas de los extremos pueden asomar 8 px como mucho hacia el relleno de la tarjeta.
- **Sin medir en el navegador.** El corte va en `data-fit` y lo aplica una consulta de contenedor (v2.css): nada se
  mueve tras pintar, sin salto de maquetación ni JavaScript. El contenedor es `.ticks-wrap` y no la tarjeta, porque la
  contención le quitaría a la tarjeta su subgrid.

Dónde queda cada ancho, con «excelente» desde 80 o desde 85 (el corte es el mismo: mover solo ese umbral no cambia el
par sólida–excelente, que ocupa el 35 % en los dos casos):

| Ancho | Contenido de la tarjeta | Forma |
|---|---|---|
| Escritorio 1440 | 334 px | Proporción, igual que antes |
| Escritorio 1024 | 283 px | Leyenda. Antes, «exigente» y «razonable» se pisaban 4,6 px |
| iPad (768) | 197 px | Leyenda. Antes, solapes de 6,6 a 17,4 px |
| Móvil 375, «La empresa» | 319 px | Leyenda |
| iPhone 15 (393), «La empresa» | 337 px | Proporción, igual que antes |

En la cabecera del móvil las marcas no se muestran, como antes: va la cifra con su banda, y el desglose está en «La
empresa».

## Pruebas

- **`scaleFit.test.ts` (vitest):**
  - la tabla de anchos da lo medido;
  - con 80 y con 85: leyenda en el iPad y a 1024, proporción a 1440;
  - un tramo de extremo más estrecho (90) pide más ancho;
  - con umbrales imposibles (97/95/93), siempre leyenda;
  - las tres tarjetas comparten el corte.
- **`e2e/v2/marcas.spec.ts`:** escritorio, tableta, móvil y móvil WebKit, en claro y oscuro, en la cabecera y en «La
  empresa». Comprueba:
  - ninguna marca pisa a otra, sale de su tarjeta ni baja de 12 px;
  - todas a la vista;
  - las tres tarjetas en la misma forma y la base de las tres a la misma altura;
  - leyenda en tableta y proporción en escritorio;
  - el tramo de la empresa resaltado.
  Da rojo en el build anterior (8 de 8) y verde con el diseño.
- **Barrido con 80 y con 85** (cambio temporal y local de `backendConfig.ts`, ya deshecho): iPad (cabecera y «La
  empresa»), móvil 375, iPhone 15, escritorio 1440 y 1024, en claro y oscuro, para AAPL y PLTR. Sin solapes, sin
  salidas y sin letra por debajo de 12 px.
- **e2e:v2 completo contra el build:** 861 pasadas y 0 fallidas, en los 4 proyectos. Vitest: 139. `npm run check`
  (guardián de literales): en verde.

## Al fusionar F8

La rama `f8-auditoria` añadió en v2.css, solo para tableta, esta regla:

```css
.fz2 .ticks > span:last-child { justify-self: end; }
```

**Hay que quitarla.** Este diseño la sustituye, y en la leyenda empujaría la última fila a la derecha. El corte se
recalcula solo con las bandas de F8: no hay nada que tocar.

## Capturas (`capturas-v4-marcas/`)

1. iPad, claro, «excelente» desde 80: antes y después.
2. iPad, claro, «excelente» desde 85: antes y después.
3. iPad, oscuro: antes y después.
4. Escritorio 1024: antes y después.
5. Escritorio 1440: sin cambios.
6. Móvil 375, «La empresa» (leyenda).
7. iPhone 15, «La empresa», oscuro (proporción).

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
