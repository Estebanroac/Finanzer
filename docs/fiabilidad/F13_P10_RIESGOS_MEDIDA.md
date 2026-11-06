# F13 · Paso 10: riesgos del sector, medida antes de aplicar (5-nov-2026)

Decisión del usuario (5-nov): riesgos en dos niveles, siempre aparte y sin puntuar.

1. **De la empresa**, solo con un dato que lo dispare.
2. **Estructural de la industria**: lista cerrada de 1–2 por industria, con la etiqueta «riesgo de la industria, no
   verificado en esta empresa».

Antes de aplicar se mide en las 543. Si un riesgo de nivel 2 sale en más del 80 % de su industria sin aportar, o en
menos del 10 % y es ruido, se revisa la lista.

## Fuentes de la medida

- **Caché del escaneo de las 543 del 5-nov** (`f13_medida_2026-11-05/cache`): industria, país, sede (estado, de las
  submissions de EDGAR), arquetipo, caja y rating sintético de cada empresa. El rating es anterior al paso 2: allí APD y
  KHC salían D; hoy salen AA y A+.
- **Vencimientos de deuda de la SEC** (API «frames» de XBRL, gratuita: un concepto para todas las empresas en una
  llamada): `LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths`, `…InYearTwo`, `CommercialPaper` y
  `ShortTermBorrowings`, del último balance de 2025–2026. Hay dato para **326 de las 543**; los bancos y los emisores
  extranjeros con IFRS no lo presentan así.

## Nivel 1 · De la empresa (con dato que lo dispare)

| Disparador propuesto | Dato | Medida en las 543 |
|---|---|---|
| **Refinanciación:** deuda que vence en 24 meses (vencimientos del año 1 y 2 + papel comercial + préstamos a corto) por encima de la caja | EDGAR (frames) + caja | **49 %** de las 303 no financieras con dato: ruido. Las utilities y los REIT viven así por diseño: poca caja y refinanciación continua (EVRG, SRE, WEC: vencimientos de 100 a 200 veces la caja) |
| … y además **rating sintético especulativo** (BB+ o peor), sin utilities, REIT ni financieras | + rating del motor | **11 de 259 (4 %)**: APD, CARR, CHTR, IP, KHC, MOS, NCLH, NRG, SW, VTRS, WYNN. Con el rating corregido del paso 2 salen APD (AA) y KHC (A+): quedan ~8, empresas apalancadas de verdad (CHTR, NCLH, WYNN, NRG) |
| Utility con litigios o provisiones por incendios | No hay concepto XBRL estándar (PCG usa los suyos). La búsqueda de texto completo de EDGAR (gratuita) lo daría por menciones en el 10-K, sin medir aún | — |
| Inquilino por encima de X % de la renta (REIT) | Solo en la instancia XBRL con dimensiones (ConcentrationRiskPercentage por cliente); companyfacts no trae dimensiones | No medible con datos estructurados gratuitos hoy |
| Ventas concentradas en un producto | Los segmentos de negocio no son productos (LLY: un segmento); el desglose por producto solo está en la instancia (ProductOrServiceAxis) | No medible hoy |

## Nivel 2 · De la industria (lista cerrada)

Lo que hay en los datos para acotar un riesgo dentro de su industria es el estado de la sede (EDGAR). Sin acotar, cada
riesgo sale en el **100 %** de su industria, por encima del 80 % de la regla:

| Riesgo propuesto | Alcance | Cobertura en su industria |
|---|---|---|
| Incendios forestales (responsabilidad por los equipos de la red) | Utilities de EE. UU. con sede en el oeste (CA, OR, WA, NV, ID, UT, AZ, CO, NM, MT, WY, HI) | **4 de 30 (13 %)**: EIX, PCG, PNW, SRE |
| Huracanes (daños a la red y recuperación de costes) | Utilities con sede en el golfo y el atlántico sur (FL, LA, TX, MS, AL, GA, SC, NC) | **8 de 30 (27 %)**: ATO, CNP, DUK, ETR, NEE, NRG, SO, VST |
| Pérdida de patentes de los productos principales | Farmacéuticas y biotecnológicas | 100 % (13 + 2 + 5) |
| Concentración en inmobiliario comercial | Bancos regionales | 100 % (12) |
| Contratos públicos y presupuesto de defensa | Aeroespacial y defensa | 100 % (13) |
| Catástrofes naturales | Seguros de daños | 100 % (8) |
| Política de Medicare | Seguros de salud | 100 % (6) |
| Regulación y litigios | Tabaco | 100 % (3) |
| Precio del combustible | Aerolíneas | 100 % (3) |

**Límite del alcance por la sede.** La sede no es el territorio que se sirve. XEL tiene la sede en Minnesota y
litigios por incendios en Colorado y Texas, y la regla del oeste no la recoge. Acotarlo de verdad necesita el
territorio de servicio, que no está estructurado, o el texto del 10-K (la búsqueda de texto completo).

## Propuesta (para la revisión del usuario)

1. **Nivel 1: aplicar la refinanciación** con las dos condiciones (vencimientos a 24 meses > caja y rating sintético
   especulativo), sin utilities, REIT ni financieras. Unas 8 empresas del universo. Hace falta añadir los cuatro
   conceptos de EDGAR al motor; los fixtures del banco y de los tests se completan con esos conceptos sin tocar el
   resto.
2. **Nivel 2: solo los riesgos que un dato acota** (incendios y huracanes por la sede: 13 % y 27 %). Los que saldrían
   en el 100 % de su industria (patentes, CRE, defensa…) no se aplican, por la regla de los 80 %, salvo que se prefiera
   mostrarlos igualmente con la etiqueta.
3. **Incendios por el 10-K** (XEL y similares): medir con la búsqueda de texto completo de EDGAR antes de decidir.
4. **Inquilinos y productos:** no medibles hoy con datos gratuitos estructurados; se dice, no se estima.

Evidencias: `archivo-historico/evidencias-de-pruebas/f13_riesgos_2026-11-05` (frames de la SEC, filas por empresa y script).
