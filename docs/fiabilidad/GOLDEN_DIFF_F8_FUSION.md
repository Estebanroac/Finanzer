# Golden · fusión de `fiabilidad/f8-auditoria` en `rediseno/v4-f8`

Las ramas que se fusionan:

- **`rediseno/v4-f8`** en 5ef69671: la v4 más `fiabilidad/f8-independientes`, con E3, E6, E10 por SIC, la historia
  de 10 años y el BPA de ciclo medio. Sus cambios están en `GOLDEN_DIFF_F8_independientes.md`.
- **`fiabilidad/f8-auditoria`** en 68785e29: E1, E4+E5, E2, E8, E9, E11 y el peso de Altman. Sus cambios están en
  `GOLDEN_DIFF_F8.md`.
- La base común es a0e824f5.

**Método.** `tools/f8_fusion_check.py a0e824f5 5ef69671 68785e29` compara, campo a campo y en los 43 golden, la base,
las dos ramas y la fusión. Usa los 11 campos del veredicto: calidad, precio, niveles, textos y confianza.

- Un campo que solo cambia en una rama debe quedar como en esa rama.
- Un número que cambia en las dos debe quedar en la suma de los dos cambios.
- Lo demás es una **interacción**.

**Resultado.** 27 campos en 10 golden no son la suma exacta. Todos tienen su causa: la combinación de dos reglas,
cada una ya aprobada en su rama. Ninguno queda sin causa.

## Causa 1 · El peso de Altman se aplica a la zona que decide el SIC

En f8-auditoria el peso cambió dentro de la zona de la variante anterior. En v4-f8, E10 elige la variante por el SIC y
la zona puede ser otra. En la fusión, el peso nuevo se aplica a la zona nueva: el cambio no es la suma de los dos.

| Golden | Base | v4-f8 (SIC) | f8-auditoria (peso) | Fusión |
|---|---|---|---|---|
| **AAPL** (SIC 3571, Z original) | zona gris −2; Solidez 10; calidad 75 sólida | zona segura +6; Solidez 20; 88 → 87 por persistencia, **excelente** (umbral 80) | zona gris −1; Solidez 11; 76 sólida | zona segura **+3**; Solidez 16; 82, **sólida** (umbral 85, E11) |
| **SHEL** | zona gris −2; Solidez 11; 76 sólida | zona segura +6; Solidez 19; 86 **excelente** | zona gris −1; Solidez 12; Rentabilidad 19 → 15 (E9); confianza baja (E11): 72 → 69 | zona segura **+3**; Solidez 16; Rentabilidad 15; cruda 78 → **74** contraída (×0,85), **sólida** |
| **FCX** (panel y local) | zona segura +6; Solidez 20; 72 | zona gris −2; Solidez 17; 69 | zona segura +3; Rentabilidad 19 → 17; confianza baja: 70 → 67 | zona gris **−1**; Solidez 18; Rentabilidad 17; cruda 68 → **65** contraída |

- AAPL y SHEL ya no salen «excelente», como sí ocurría en v4-f8. Hay tres razones: su zona segura suma +3, no +6;
  «excelente» empieza en 85; y SHEL, con confianza baja, se contrae.
- En AAPL la persistencia no se aplica: 82 está por encima del codo de 80, pero no se corrige.
- En SHEL el precio queda como en f8-auditoria, de «atractivo» a «razonable», contraído por la confianza baja de
  E11.

## Causa 2 · Altman referencial por la financiera cautiva: el peso no cuenta

En v4-f8 (E10 bis), CAT (Cat Financial) y TM (Toyota Financial Services) consolidan una financiera cautiva. Su Altman
es referencial y queda fuera del denominador, así que el cambio de peso de f8-auditoria (+6 → +3) no les llega.

| Golden | Base | v4-f8 | f8-auditoria | Fusión |
|---|---|---|---|---|
| **CAT** | Solidez 20, Crecimiento 10; 84 excelente | Altman referencial: Solidez 15; Crecimiento 8 (historia de 10 años); 75 | +3: Solidez 18; confianza baja (estabilidad baja, E11): 81 → 76; precio de «muy exigente» a «exigente» | Solidez 15, Crecimiento 8; cruda 75 → **71** contraída; precio **exigente**, como en f8-auditoria |
| **TM** | Solidez 19, Rentabilidad 10; 70 | Altman referencial: Solidez 13; 62 | +3: Solidez 16; Rentabilidad 10 → 4 (E9); 59 | Solidez 13, Rentabilidad 4: **55**, media |

## Causa 3 · La contracción y la persistencia no son lineales

La contracción ×0,85 con confianza baja (E11) y el tope de persistencia, por encima de 80, se aplican sobre la
puntuación cruda de la fusión. Esa cruda ya lleva los cambios de las dos ramas, así que el resultado no es la suma de
los cambios mostrados en cada una.

| Golden | Base | v4-f8 | f8-auditoria | Fusión | Suma |
|---|---|---|---|---|---|
| **XOM** | 82 | 80 (Crecimiento 10 → 8) | 75 (Rentabilidad 16; contraída de 79) | cruda 76 → **72** | 73 |
| **JNJ** | 86 | 85 (la persistencia corta 86 → 85) | 81 (Altman +3 y E9: Solidez 18, Rentabilidad 18) | **81**: con la cruda en 81 la persistencia no corta | 80 |

- XOM: la contracción de E11 actúa sobre el Crecimiento 8 de v4-f8; la diferencia con la suma es 1 punto de redondeo
  de la contracción.
- JNJ: la persistencia solo cortaba en v4-f8 porque allí la cruda era 86.

## Causa 4 · O (REIT): el FFO de Nareit (E3) frente a la sensibilidad a Ke (E1) y a la regla de la más baja (E11)

- **Panel O.** En v4-f8, el FFO de Nareit (E3) sube el precio a 75, «atractivo», con confianza alta. La comprobación
  de Ke ± 1 pp de E1 (f8-auditoria) no existía en v4-f8. En la fusión, con Ke + 1 pp (9,1 %) el precio cae a
  «razonable»: el veredicto depende de Ke y la confianza baja de alta a **media**. El precio se contrae a **69**, que
  sigue siendo «atractivo». La calidad, 65, es la de v4-f8.
- **Local O.** En v4-f8 la cobertura es baja (FFO sin dato) y la confianza media por la media ponderada. En la fusión,
  la regla de E11 (la más baja manda) la lleva a **baja**. Se contraen la calidad (65 → **63**, de sólida a
  **media**) y el precio (65 → **58**). Es el cruce que pidió el PM: la confianza no supera a la cobertura.

## Cruces revisados sin interacción en los golden

- **E6 (estados desfasados) frente a E11:** ningún golden tiene los estados desfasados. Se verifica en vivo con AMZN,
  en `F8_FUSION_REGISTRO.md`.
- **Ciclo medio (BPA) frente a E2:** el ciclo medio cambia el crecimiento y E2 el P/E que puntúa. En los golden
  ninguna cíclica activa la bandera de pico, así que ningún campo de veredicto se aparta de la suma.
- **Historia de 10 años frente al CV del margen FCF de E8:** E8 toma sus ventanas de `history_10y.build` (5
  ejercicios). Los tests de E8 pasan con la historia nueva y ningún nivel de fiabilidad del DCF se aparta de la suma.

---

# Fusión de `fiabilidad/f8-p3` (presentación) en `rediseno/v4-f8`

Las ramas que se fusionan:

- **`rediseno/v4-f8`** en 5ee2c50e, ya con `fiabilidad/f8-auditoria`.
- **`fiabilidad/f8-p3`** en dcf91024: P3 (1–6) de la auditoría. Sus cambios están en `GOLDEN_DIFF_F8_P3.md` y el
  registro, en `F8_P3_REGISTRO.md`.
- La base común es 1c8a4178.

**Conflictos de código, resueltos uniendo las dos reglas:**
- `business_model.py` / `main.py`: la detección de la financiera cautiva (E10) y la nota del Piotroski condicionada al
  current ratio (P3) conviven. `_bm_ctx` calcula una vez `current_ratio_context` y lo pasa a `piotroski_caveat`.
- `display._kpi`: el porqué de una cifra sin dato toma la lectura, el `kpi_why` de v4-f8 (FFO y payout) y, si no hay
  ninguno, el motivo de `data_validation` de P3 (ROE n.s.).
- Frontend: la v4 ya no tiene visuales de capítulo, así que `ChapterVisual.tsx` sale y en `story.ts` se queda la
  versión de v4-f8. En la cabecera, el total de «Valoración» del desglose del precio usa `score_txt`. Los desgloses
  compactos, que la v4 quitó, no vuelven. La tabla del desglose (`BreakdownTable`) se fusiona sola. La página
  «Conclusión» de la v4 ya decía «No concluyente».

**Método.**
- `tools/f8_fusion_check.py 1c8a4178 5ee2c50e fiabilidad/f8-p3`, sobre los 11 campos del veredicto: **0
  interacciones** en 43 golden.
- Además, una comparación a tres vías hoja a hoja sobre todos los campos de los golden JSON (base, v4-f8, f8-p3 y
  fusión).

**Resultado.** 83 hojas no son la copia de una rama. Todas tienen la misma causa:

## Causa P3 · `score_txt` y el tono neutro se calculan sobre la puntuación de v4-f8

`score_txt` (P3.5) es la puntuación de cada categoría como se muestra. En f8-p3 se calculó con las puntuaciones de la
base; en la fusión sale de las de v4-f8 (E1–E11, peso de Altman, SIC…). Por ejemplo, AAPL Solidez «16 / 20» en lugar
de «10 / 20».
- 82 hojas: `score_txt` de la portada y del desglose en 29 golden.
- 1 hoja: el tono de una categoría en el golden local de O. En v4-f8 su Rentabilidad pasa a no concluyente, y P3 pone
  neutro el tono de toda categoría no concluyente: «warn» → «neu», y su `score_txt` dice «no concluyente».

Comprobado en los 43 golden y las 4 muestras forzadas: en todas las categorías, `score_txt` es «puntos / máximo» o
«no concluyente» según `conclusive`, y toda no concluyente tiene tono neutro.

Fuera de eso, cada campo queda como en la rama que lo cambió. Las fixtures del frontend cambian frente a v4-f8 solo en
los campos de P3 (valor justo y bloque central, fuerza relativa, nota del Piotroski de PLTR, `score_txt` y el anexo de
RIVN).
