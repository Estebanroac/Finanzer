# Ensayo de la fusión de `rediseno/e4-portada` en la v4

Encargo del PM (2026-10-18): ensayar la fusión mientras E4 termina M5–M7 y P8, para que la fusión real sea rápida.

## Cómo se hizo

- Rama desechable `ensayo/fusion-e4` creada desde `rediseno/v4` (3e91dea).
- `git merge --no-commit rediseno/e4-portada` con la rama en **0b83184** (M4). Son 25 commits de E4: V6 seguridad, V4
  memoria, moneda, GZip, V2 fuentes reales y M1–M4.
- Después se deshizo y se borró la rama. `rediseno/v4` no se tocó, salvo el commit de este documento.
- Durante el ensayo E4 publicó **M5** (e8fa669, 94 archivos). `git merge-tree` contra e8fa669, sin tocar el árbol,
  da los **mismos 8 conflictos de código y tests**. M5 añade solo fusiones automáticas en `analysis_queue.py`,
  `pdf_v2/cover.py` y `scenario.py`, y conflictos en los golden de `panel_pdf_v2`, que se regeneran.

## Conflictos y resolución (40 archivos)

| Archivo | Conflicto | Resolución |
|---|---|---|
| `backend/config/market.toml` | `[peers]`: `pe_meaningful_max` (V7 · P5) frente a `fail_ttl_s`, los topes de caché, `max_substitutions` y `no_data_markers` (E4: V6 B3/B10 y V2) | Las dos cosas |
| `backend/config/schema.toml` | Los mismos campos en el esquema | Las dos cosas |
| `backend/lib/display.py` | `band_labels`: `sensitivity_band_labels()` (V6, F17) frente a la lista escrita a mano de E4; en la nota, `numfmt.price` y «Tabla asimétrica» (M4) | `sensitivity_band_labels()` y la nota de E4 (precio en su moneda, sin «grid») |
| `backend/lib/peers.py` | `cached_for` (rivales del PDF, V6) frente a `_gone`/`_substitute` y la firma `peers_for(..., client)` (E4) | Las dos cosas, con la firma de E4. **Además, un conflicto que git no ve** (abajo) |
| `backend/tests/test_config_literals.py` | Excepciones de `sensitivity_band` (V6) frente a `build_display` y `_compute_analysis_body` (E4 renombró la función) | `sensitivity_band` y `_compute_analysis_body` |
| `backend/tests/test_pdf_v2_endpoint.py` | Tests nuevos en los dos lados: ETF y rivales (míos); segmentos solo de caché (E4, B9) | Los dos |
| `backend/tests/test_peers.py` | `cached_for` y el «n. s.» del P/E (míos) frente a los tests de V6 B3/B10/B11 (E4) | Los dos |
| `backend/tests/test_segments.py` | Los tests de `summary`, `product_view` y el capítulo 2 del PDF (míos) frente a los de E4 | Los dos |
| `backend/tests/golden/panel_pdf_v2/*.pdf.txt` (32) | Texto del informe cambiado en los dos lados | Se regeneran (`pdf_v2_golden.py --regenerate`) |

- **`frontend/src/v2/pages/Valor.tsx` (M4) se fusiona sin conflicto:** las chips de los múltiplos con su espacio y el
  texto de «Escenarios» sin «endpoint». No choca con nada mío.
- Tampoco chocan `api.ts`, `playwright.config.ts`, los specs nuevos de E4 (`fuentes-reales`, `legado/csp`),
  `main.py`, `segments.py`, `analysis_queue.py` ni `pdf_v2/cover.py`.

### Conflicto que git no ve: `peers.cached_for`

E4 cambió dos cosas de los rivales:
- **Plazo de cada ranking:** las entradas de `_rankings` pasan a `(t, res, ttl)`, porque un fallo se recuerda
  `fail_ttl_s` y no 7 días.
- **Sustituciones:** un rival que la fuente ya no tiene se cambia por el siguiente del ranking.

Mi `cached_for`, que lee los rivales para el PDF, seguía con el plazo fijo `caps_ttl_s` y sin sustituciones. En la
resolución usa `hit[2]` y `_substitute`: así el PDF enseña los mismos rivales y la misma nota que la web.

## Comprobaciones en el ensayo (con 0b83184)

- **Backend**:
  - 5163 pasadas y 1 fallo, en `test_no_page_starts_with_a_value_without_its_label[JPM]`.
  - Tras el arreglo de la comprobación (abajo), los tests de PDF, glosario, segmentos, rivales, literales y contrato
    dan 907 pasadas y 0 fallos.
- **Frontend**: `npm run check` en verde (contrato: 46 salidas), Vitest 113, `tsc` limpio, lint 0 errores.
- **Golden `panel_pdf_v2` regenerado** (36 archivos). Los cambios son del texto del motor:
  - M1: «el valor está un X % por debajo del precio»;
  - M2: periodos (TTM, FY2015–FY2025…);
  - M3: etiquetas;
  - M4: «$» en los precios, sin «^TNX», «config», «grid» ni «factor 1.0», y la fórmula del bloque en el anexo.

  Lo mío sigue en pie:
  - **glosario:** 36 de 36 en la última página, en una página;
  - **geometría:** sin huecos, con la regla general de página nueva;
  - **«(sigue)»:** las etiquetas se mueven con el reflujo (5 nuevas y 3 que desaparecen);
  - **sin «…» fuera del motor.**
- **e2e** (`desktop`) contra el replay con el código fusionado:
  - `nada-se-pierde` en el panel (36), `v7`, `depth` y `symmetry`: 135 pasadas y 1 fallo, MC.PA en «nada se
    pierde»;
  - tras el ajuste del spec (abajo), MC.PA pasa, y AAPL y BCS también.

## Lo que la fusión rompe de lo mío, y el arreglo

1. **La comprobación de «(sigue)» daba un falso positivo en JPM.** Con el texto de M3, el valor de la fila
   «P/TBV frente a ROTE» ocupa 5 líneas («132 % del P/TBV justificado…»). Su etiqueta va centrada en la fila, más abajo
   que la primera línea del valor, y la comprobación solo miraba esa primera línea.
   - Arreglo en `pdf_geometry.headless_page_starts`: busca la etiqueta dentro del alto del primer bloque del valor
     (líneas que se solapan en horizontal, así que vale para columnas alineadas a la derecha), sin contar la cabecera
     repetida.
   - Con el texto fusionado, señala 0 páginas con `LabeledTable` y 9 sin él: todas las filas partidas de verdad.
2. **«Nada se pierde» en MC.PA.** E4 da los importes de los estados en su moneda («EUR 10.60B»). La web actual les
   pone «$» a todos («$10.60B»). La cifra no se pierde: está con su moneda.
   - Arreglo en `nada-se-pierde.spec.ts`: un «$X» de la web actual cuenta como presente si /v2 enseña la misma cifra
     con otro código de moneda (solo importes con B, M o T).
3. Nada más. Los dos arreglos son míos, valen también antes de la fusión y van en el parche que aplicaré en la fusión
   real.

## Pasos de la fusión real (cuando avise el PM)

1. En `rediseno/v4`, `git merge rediseno/e4-portada`, con E4 cerrada: M5–M7 y P8.
2. Resolver los 8 archivos como en la tabla. Para el código y los tests, el guion del ensayo; para los golden,
   cualquier lado y después regenerar.
3. `cached_for` con `hit[2]` y `_substitute`.
4. Los dos arreglos de arriba: comprobación de «(sigue)» y spec de «nada se pierde».
5. Revisar lo que traigan M6, M7 y P8. Hoy no están en la rama.
6. Regenerar `panel_pdf_v2` y pasar `diff_golden` (panel y local) con el golden de E4.
7. Después, P1 (la línea de la confianza, ya con los nombres de M5) y la pasada final del cierre.
