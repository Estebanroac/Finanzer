# F14 · Segunda revisión externa: pasos 1 a 11 (6-nov-2026)

Revisión: `informes-pdf/Revision_Finanzer_v2_2026-11-06.pdf`, nota 69. Se constató contra los 110 análisis de producción
(`archivo-historico/evidencias-de-pruebas/revision_v2_2026-11-06/`) y se incorporaron los tres ajustes de la respuesta
del evaluador. El usuario pidió terminarlo todo y consultar al final; el push espera su visto bueno.

Banco congelado: `archivo-historico/evidencias-de-pruebas/f14_banco110_2026-11-06/`. La base es igual byte a byte al
paso 12 de F13. Hay una tabla por paso (`pasoN_vs_…md`).

## Pasos

| Paso | Qué | Efecto medido en las 110 |
|---|---|---|
| 1 | **Rf de 4,94 %**, leído de la hoja mensual de Damodaran (su portada repetía el 5,29 % de octubre). `tools/damodaran_erp.py`, test del par, aviso de deriva de 0,3 pp y aviso si el Rf repite el del mes anterior. Detalle: `F14_P1_RF.md` | 24 cambian; KMI, MRK y T hacia barata |
| 2 | **Tasa base**: peso según la evidencia propia (0,5 con 3 años y 0,25 con 10) y sin cambiar nunca el signo | 4 cambian; 12 que decrecían ya no se proyectan creciendo (KHC, NKE, PSA, TGT…) |
| 3 | **Confianza**: techo «baja» con EBIT normalizado ≤ 0, con Altman en peligro + rating especulativo o con un DCF que puntúa a más de ±150 %. El EBIT es el normalizado, como pidió el evaluador | CMCSA de alta a baja; KHC sigue en media (sus deterioros no cuentan) |
| 4 | **Etiqueta**: si la contracción cambia la banda, el veredicto da las dos («precio entre razonable y atractivo»; `verdict.price_level_raw`). Nombrarlas también en la tarjeta se midió y se descartó: alargaba la portada del PDF (ASML a 0,847, por debajo de 0,85) sin añadir nada | 29 empresas |
| 5 | **Espectro de AT&T**: EDGAR no lo separa de sus adquisiciones (Time Warner, DirecTV). No se estima: el DCF pasa a fiabilidad baja | T de atractivo a razonable |
| 6 | **Representatividad**: con menos de 10 empresas, el grupo más amplio. Ver el detalle debajo | 10 cambian |
| 7 | **REIT**: la cobertura puntuada y la de la alerta son la del rating (EBITDA) | WELL: sin la alerta falsa de 0,8x; calidad de débil a media |
| 8 | **ROIC**: con el EBIT normalizado; sin ROIC si la deuda de la cautiva no se separa | GM de 2,8 % a 12,1 %, sin «destruye valor»; DE sin ROIC comparable, con el motivo |
| 9 | **Calidad del beneficio**: un flujo operativo por debajo del beneficio no suma. **PEG**: el BPA se acota a las ventas + 10 pp | NFLX, NVDA, HON y BLK; PEG de NFLX, LIN, DIS… |
| 10 | **Ventas y BPA a más de 20 pp**: el DCF de las ventas no puntúa | LIN, GOOGL |
| 11 | **Referencias**: la nota dice qué columnas son mediana de pares o industria global, y por qué vale una entre el 2 % y el 3 % | AMZN y DE: «margen fino por naturaleza» |

### Detalle del paso 6

- **Betas:** se usa la tabla global de Damodaran (`betaGlobal.xls`). Las integradas pasan de 4 empresas de EE. UU.
  (βU 0,28) a 34 globales (0,63). Afecta a XOM, CVX, PSX, MOS y UNP.
- **Referencias:** se prefiere la industria global sin la empresa a los pocos pares. NFLX y DIS ya no usan 4 pares en
  margen y ROE. AAPL usa la global sin Apple.
- **Pares mínimos:** exigir 10 se midió y se descartó. Dejaba sin referencia 101 columnas de 44 empresas (PEP, SPOT,
  EA y WBD se quedaban sin ninguna; ASML acababa comparada con el mercado europeo entero). Los pares quedan como último
  recurso, con su número dicho.
- **Resultado:** 117 columnas sin referencia, frente a 126 antes.

## Lo que no se cambió, y por qué

- **Patentes y materias primas** (punto 10 de la revisión): se mantiene la decisión del paso 10 de F13, y el evaluador
  está de acuerdo.
- **3M:** su caída de ventas ya excluye a Solventum, porque EDGAR la reexpresa. Su DCF bajo viene de los pagos por
  litigios (PFAS y tapones), que son caja real.
- **Coste de capital de las telecos:** son los datos de Damodaran. Con el Rf corregido baja algo más.
- **Ford:** su «destruye valor» viene de un resultado operativo negativo también normalizado, no de Ford Credit.
- **Las 22 cíclicas:** siguen en «baja» con el motivo del ciclo (decisión 3c de F13).

## Balance F14 (base → final, 110 congeladas)

- Cambian 57 empresas. Las bandas de precio se mueven en 3: 2 hacia barata y 1 hacia cara.
- 29 veredictos dicen ahora el rango cuando la confianza baja cambia la banda.
- Confianza:
  - baja: 69 → 67;
  - media: 34 → 38;
  - alta: 7 → 5. Salen CMCSA, por su DCF fuera de escala, y PG.
- Reglas de cordura:
  - `beta_en_rango`: 4 → 1;
  - `calidad_sin_saturar`: 6 → 3;
  - `crecimiento_dcf_representativo`: 12 → 10;
  - ninguna empeora.

Tests: `tests/test_damodaran_erp.py` y `tests/test_f14.py`. Los golden se regeneran: panel, local, forzados y PDF v2.
