# F13 · Paso 4: productores de materias primas, cíclicos por su industria (5-nov-2026)

Patrón 6 de la revisión de 110 empresas: «el ciclo de materias primas no se detecta, y el pico de beneficio tampoco».
Newmont salía «calidad excelente, precio atractivo, confianza alta» con el oro en máximos: el caso más peligroso de la
muestra.

## Qué cambia

- `config/sectors.toml [archetypes] commodity_industries` (decisión del usuario, 5-nov): minería (oro, plata, cobre,
  aluminio, otros metales, carbón, uranio), petróleo y gas (E&P, integradas, refino, perforación), químicos básicos y
  fertilizantes (`chemicals`, `agricultural inputs`) y acero.
- `lib/classify.py`: con historia larga, si la historia de ventas no muestra ciclo pero la industria es de materias
  primas, **CYCLICAL por su industria** (regla `materias_primas`). Antes la lista de industrias era un `elif` que con
  historia larga no se consultaba. Los cíclicos de lista que no son productores (servicios petroleros, aerolíneas,
  coches…) siguen decidiéndose por su historia.
- **Pico de beneficio en cíclicas: sin cambio, a propósito.** La bandera de pico solo cambia cómo puntúa el P/E, y en
  una CYCLICAL el P/E no puntúa: su precio se mide ya sobre el ciclo medio (P/FCF y EV/EBITDA normalizados, DCF con el
  flujo medio). El remedio era clasificarla bien, como muestra NEM. Las 8 cíclicas con el beneficio a más de 1,5× su
  mediana (MU, STX, LRCX, AMD, FSLR, ARM, TPR y NEM) se valoran ya a mitad de ciclo.
- Los años de perímetro que ocultaban las pérdidas de NEM (2014–2018) ya no deciden: la industria basta.

## Efecto

- **110 congeladas:** cambia solo **NEM ★**: «excelente · atractivo (alta)» → **«sólida · exigente (baja)»**. A mitad
  de ciclo cotiza a 37x su caja libre media y a 19,8x EV/EBITDA (industria 12,0x); el DCF también la ve cara; la
  confianza es baja por ser cíclica. Se declara «ciclo incompleto: 4 ejercicios».
- **Universo (regla `ciclica_por_industria` del paso 0):** 4 empresas: NEM, BHP, RIO, TPL.
- Golden: sin cambios de arquetipo (XOM, FCX y DOW ya eran cíclicas por su historia).
- Test: `tests/test_cyclicality.py` (el caso «petrolera integrada sin ciclo → madura» pasa a aerolíneas, porque la
  decisión lo invierte para las materias primas).

## Pendiente, anotado

CYCLICAL por su historia que no lo parecen: dos episodios de caída, uno de ellos un choque general (2009 o 2020). VRTX
(biotecnología: 2009 y 2014), ADSK (2009 y el paso a suscripción de 2017) y TPR. MAR, MGM y WYNN sí son cíclicas en lo
económico (hoteles y casinos). GE y HON son escisiones (paso 7, perímetro). No hay una regla general limpia que separe
VRTX o ADSK de MAR sin criterios por empresa: queda para la revisión del modelo general.
