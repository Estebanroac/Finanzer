# F13 · Paso 5: la referencia sin la empresa, el ROE bajo y el patrimonio ínfimo (5-nov-2026)

Patrón H de la revisión de 110 empresas: lecturas de rentabilidad que no se sostenían. (5a) Comcast, McDonald's y
Starbucks se comparaban con su industria sin ellas, pero lo que quedaba eran restos. (5b) META, WMT, UPS o GS tenían
«ROE bajo» con un ROE que cubre de sobra su coste del capital. (5c) Colgate tenía «ROE excepcional 713 %» con un
patrimonio del 1,7 % de los activos.

## Qué cambia

- **5a · la referencia sin la empresa, acotada** (`lib/self_exclusion.without`): una columna deja de usarse cuando
  ocurre alguna de estas dos cosas:
  - **Salto:** sin la empresa cambia de signo o se mueve más de `self_max_shift` = 3 veces frente al agregado
    publicado.
  - **Resto:** es de beneficio (ROE, ROIC, margen neto u operativo) y sin la empresa queda por debajo de
    `min_profit_ratio` = 2 %, el umbral ya decidido en la revisión de NFLX.

  En los dos casos la columna pasa al respaldo que ya existía, la mediana de los pares del universo. La fuente de la
  fila dice por qué. Si tampoco hay pares suficientes, la columna se queda sin referencia y la nota lo declara
  (`benchmark.self_dropped`, `display`): «Sin la empresa, la industria no sirve de referencia para: …».
- **5b · sin «ROE bajo» si el ROE ≥ Ke** (`alert_interpretations._roe`): aunque el ROE esté por debajo de la
  industria, si cubre el coste del capital propio el accionista está remunerado (`fin_dict.cost_of_equity`).
- **5c · ROE «n.s.» con un patrimonio por debajo del 5 % de los activos**, en las no financieras. Se usa el mismo
  camino que con el patrimonio negativo:
  - En la puntuación, el ROE no puntúa (`score_rentabilidad`, `equity_to_assets`).
  - En las alertas, el ROE no da ni fortaleza ni aviso.
  - En lo que se presenta, `validate_outputs` lo deja «no significativo» con su motivo.

  Quedan fuera las del arquetipo FINANCIAL y las del sector «Financial Services», como gestoras y aseguradoras de vida
  que el arquetipo no recoge (AMP, APO, PFG).
- Reglas de cordura: `referencia_acotada` ya no calcula el factor frente a una publicada casi nula, como el ROE de
  Restaurantes (0,1 %). `roe_patrimonio_infimo` da por resuelto el caso si no hay cifra ni fortaleza.

## Efecto en las 110 congeladas (paso 4 → 5)

- **Bandas de precio:** ninguna cambia. **Confianza:** BRK-B pasa de baja a media. Sin ella, el P/B de Conglomerados
  pasaba de 1,8x a 7,3x, lo que la hacía «muy barata» por múltiplos frente al resto de métodos. Ahora esa columna se
  queda sin referencia y su nota de precio baja de 40 a 35.
- **Reglas de cordura:**

  | Regla | Paso 4 | Paso 5 |
  |---|---|---|
  | `roe_bajo_coherente` | 25 | **0** |
  | `roe_patrimonio_infimo` | 2 (BA, CL) | **0** |
  | `referencia_acotada` | 16 | **11** |

- **Referencias sustituidas** (publicada → sin la empresa → la que se usa):

  | Empresa | Columna | Motivo | Publicada | Sin la empresa | Se usa |
  |---|---|---|---|---|---|
  | CMCSA ★ | margen neto | salto | 5,7 % | −8,1 % | sin referencia (dicho) |
  | CMCSA ★ | ROE | salto | 8,1 % | −13,3 % | sin referencia (dicho) |
  | MCD, SBUX ★ | ROE | salto | 0,1 % | −223 % / −19 % | 49,6 % (3 pares) |
  | MCD, SBUX ★ | D/E | salto | 20,2x | −6,2x / 0,6x | 2,46x (3 pares) |
  | ABBV ★ | margen neto | resto | −5 % | −8,3 % | 23 % (7 pares) |
  | AMGN ★ | margen neto | resto | −5 % | −9,8 % | 9,8 % (7 pares) |
  | MRNA | margen neto | resto | −5 % | −3,6 % | 23 % (7 pares) |
  | DOW | ROE y margen neto | resto | negativas | negativas | sin referencia (1 par) |
  | NFLX | ROE | salto | 6,1 % | 0,6 % | 7,5 % (4 pares) |
  | DIS | ROE | salto | 6,1 % | −1,2 % | 12,4 % (4 pares) |
  | AMZN | D/E | salto | 0,59x | 2,02x | 1,30x (6 pares) |
  | NUE | ROE / margen neto | salto | 3,7 % / 1,9 % | 1,2 % / 0,6 % | sin referencia (dicho) |
  | DIS | cobertura de intereses | salto | 3,7x | 1,0x | sin referencia (dicho) |
  | BRK-B | P/B | salto | 1,8x | 7,3x | sin referencia |

  Con su referencia de pares, DIS gana «ROE bajo 7,8 %» (por debajo de su Ke) y NFLX gana «ROE excepcional 42,6 %».
  Antes ninguna de las dos tenía referencia de ROE.
- **«ROE bajo» retirado** en 25 empresas con el ROE ≥ Ke: AEP, AMZN, BAC, BLK, CRM, CSCO, CVX, DUK, ED, EXC, FCX,
  GOOGL, GS ★, KMI, META, NEM, NKE, OXY, PFE, RTX, SO, T, UPS ★, VZ, WMT ★.
- **ROE «n.s.»:**
  - CL ★: pierde la fortaleza «ROE excepcional 927 %», y la fila dice «no significativo: el patrimonio es solo el
    1,7 % de los activos».
  - BA: pierde «ROE negativo −77,8 %». Las pérdidas ya las señala «Margen neto normalizado negativo −5,0 %».
  - En las dos, la nota ya puntuaba el ROIC en lugar del ROE por el apalancamiento (F8 · E9), así que la puntuación no
    cambia.

Tabla y corridas: `archivo-historico/evidencias-de-pruebas/f13_banco110_2026-11-05/paso5_vs_paso4.md` y `paso5/`.

## Lo que queda (anotado, no es de este paso)

- **`referencia_acotada` sigue en 11** (AMZN, DE, DIS, ECL, HAL, MOS, NFLX, PSX, SHW, TSLA, UNH): referencias de
  beneficio entre el 2 % y el 3 %. Son industrias de margen bajo de verdad (distribución, química de especialidad,
  servicios petroleros, servicios sanitarios), y la mediana de pares también sale baja. La regla de cordura usa el 3 %
  del revisor; la configuración, el 2 % decidido en la revisión de NFLX. Igualarlos es una decisión del usuario.
- **ROE de 49,6 % en Restaurantes:** la mediana de pares incluye empresas con patrimonio casi nulo. No se lee porque
  MCD y SBUX tienen el ROE «n.s.», pero la mediana de pares de ROE debería excluir a las de patrimonio ínfimo.

- **Cambio de signo legítimo (SNOW):** Software (Internet) publica un margen neto de −0,9 % y sin Snowflake queda en
  +3,2 %, porque es ella la que hunde el agregado. La regla del salto lo manda igual a la mediana de pares (19,2 %), y la
  lectura no cambia («muy inferior» frente a las dos). Si en el universo aparecen más casos así, se puede afinar el salto
  para que solo cuente cuando la empresa y el resto tienen el mismo signo.

## Golden

Ningún veredicto de calidad ni banda de precio cambia.

| Golden | Qué cambia |
|---|---|
| local NFLX, panel NFLX | ROE y margen neto con referencia de pares (7,5 % y 2,4 %). Gana «ROE normalizado elevado 37,8 %», y el margen neto pasa a leerse frente a la industria |
| local y panel FCX; panel BAC, DUK, MC.PA | Sin «ROE bajo»: el ROE cubre su Ke |
| panel BRK-B | P/B sin referencia (dicho). Confianza de baja («el P/B justificado y el del sector discrepan») a media («un solo método evaluable»). Nota de precio de 42 a 39 |
| panel DOW | ROE y margen neto sin referencia (resto en pérdidas, un solo par), dicho en la nota |
| panel AMZN | D/E de referencia de 2,02x a 1,30x (pares) |
| SNOW (local, panel, forzados) | ROE y margen neto de referencia, de pares |

El PDF v2 (`panel_pdf_v2`) cambia en las mismas empresas. Además, BAC se queda sin avisos y destapó un texto que ya
existía: el capítulo de riesgos decía «A vigilar: Sin alertas relevantes». Ahora dice «No hay alertas relevantes que
vigilar» (`lib/pdf_v2/chapters.py`; también PGR, PLD y BRK-B).

Tests: `tests/test_f13_paso5.py` (9). Suite: 6649 passed. El guardián del PDF exige el periodo junto a toda cifra de ROE, así que la nota
dice «TTM del conjunto».
