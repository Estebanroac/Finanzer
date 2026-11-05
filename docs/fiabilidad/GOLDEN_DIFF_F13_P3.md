# F13 · Paso 3: la confianza no cuenta dos veces y mira la base (5-nov-2026)

Patrón 1 de la revisión de 110 empresas: la etiqueta «alta» aparecía donde no se merecía (ORCL, XEL, PSA, CRM, JNJ,
ABBV), porque (1a) el DCF inverso se contaba dos veces y (1b–1c) la confianza no miraba la fragilidad de la base.

## Qué cambia (`lib/valuation_confidence.py`)

- **3a · los múltiplos por tipo de fila:** la señal de «múltiplos frente al sector» excluye las filas por **prefijo**
  («DCF», «Regla de 40»), no por nombre exacto. Antes, con el DCF directo no significativo o en un REIT, la fila se
  llamaba «DCF inverso (…)», entraba en la media de los múltiplos y además era un método propio.
- **3b · dimensión «base del veredicto»** (`fragility_dimension`): techo «media» (no pondera) si se da alguna de estas:
  - caja libre negativa con flujo operativo positivo (invierte más de lo que genera; no en FINANCIAL);
  - Altman Z en zona de peligro;
  - P/E normalizado y forward separados más del 40 % (`thresholds.confidence.fragile_pe_gap`): la normalización y el
    consenso no cuadran (XEL 28,5x frente a 17,8x).
  Los estados desfasados ya ponían el techo por la cobertura (F8 · E6): no se cuentan dos veces. Un Altman solo
  referencial (empresa con financiera cautiva: `business_model.altman_referential`, TM) no es señal: lo pidió el
  guardián del PDF, que exige que toda zona de Altman citada tenga su respaldo (`display`: la zona se declara también en
  los textos de confianza, en lenguaje llano y de la portada).
- 3c, la estabilidad medida de las cíclicas, se mide aparte y **no** se aplica hasta que el usuario revise la lista.

## Efecto en las 110 congeladas (paso 2b → 3)

- Confianza **alta: 13 → 7**; media 38 → 39; baja 59 → 64. Una banda de precio cambia (XEL).
- **De alta a media:** ORCL ★ (caja −28,7 B$ y Altman 0,83), CRM, JNJ, ABBV (normalizado frente a forward), PLD
  (doble conteo del inverso).
- **XEL ★:** «débil · muy exigente (alta)» → «débil · exigente (baja)»: base frágil (caja libre −7,6 B$ y normalizado
  frente a forward) y, además, el limitador de Ke que ya existía. Con confianza baja, el precio se contrae hacia 50.
- **De media a baja:** AMT (sin el inverso contado dos veces, sus múltiplos dicen «barata» y el inverso «cara»: una
  discrepancia real que el doble conteo escondía); MMM, SBUX y TSLA (base frágil y después el escalón de las tasas base,
  que ya existía).
- Siguen en «alta»: VICI y las demás que el revisor daba por buenas.

Tabla: `archivo-historico/evidencias-de-pruebas/f13_banco110_2026-11-05/paso3_vs_paso2b.md`.

## Golden

Cambia la confianza de PLD (alta → media: su cobertura de portada dice ahora «DCF inverso la ve en precio y los
múltiplos cara», la lectura sin el doble conteo; `tests/test_pdf_v2_report.py` actualizado) y AMT (media → baja); ningún
veredicto de precio o calidad. Tests: `tests/test_f13_paso3.py`.

## 3c · Estabilidad medida de las cíclicas: medida, NO aplicada (decisión pendiente)

Regla probada con las tres condiciones del usuario sobre las 60 CYCLICAL de las 543 (`f13_medida_2026-11-05/cache`):
ventana válida si en los 10 años de EDGAR hay al menos una caída real del beneficio neto (≥ 20 % o pérdidas);
«media» si la peor caída anual no pasa del 50 %, nunca hay pérdidas y el margen operativo oscila ≤ 10 pp; materias
primas siempre «baja».

| Grupo | Empresas |
|---|---|
| Materias primas (siguen baja, condición 3) | 23 |
| Sin caída real de beneficio en la ventana (siguen baja, condición 1) | 3: AMAT, ASML, LRCX |
| Suben a «media» | **0** |
| Siguen baja por inestables | 34 |

Las más cercanas: DE (peor caída −30 %, margen ±11,4 pp), PCAR (−46 %) y ADM (−48 %) sin serie de margen, SWKS (−39 %,
±22 pp). La medida muestra además CYCLICAL mal clasificadas por su historia, que son del paso 4: VRTX (biotecnología),
ADSK (software), GE y HON (escisiones), MAR, RL.
