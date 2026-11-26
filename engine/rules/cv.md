# Reglas del CV

Sustituye a CV_Writing_Guide.md y CV_Generation_Rules.md (40.340 caracteres).
Se borro todo lo que un modelo competente ya sabe. Queda solo lo contraintuitivo
y lo especifico del caso del usuario.

## Que se carga

1. `facts/identity.yaml`, `facts/roles.yaml`, `facts/prohibitions.yaml`
2. `voice/precedence.md`, y el `voice/sector-<x>.md` que corresponda
3. `voice/samples.md`, `voice/approved-bullets.md`, `voice/anti-slop.md`
4. `facts/evidence.yaml`, SOLO los items cuyas `capabilities` coinciden con el aviso
5. El aviso y la Position Description

NO se carga: `build/`, `archive/`, `logros-working-doc.md`, `Credentials/`,
`experiencias-vault/`.

---

## Proceso: tres pasadas

### Pasada 1, analisis y seleccion (un solo mensaje)

1. Clasificar empleador y elegir el `voice/sector-<x>.md`.
2. Tabla de keywords: 15 a 25 filas, **palabras textuales del aviso**, nunca
   parafraseadas ("continuous improvement" no se convierte en "process
   optimisation"). Columnas: keyword, peso de fuente, cluster, match depth,
   destino planificado.
   Peso de fuente, de mayor a menor: titulo del cargo y criterios de seleccion;
   deberes de la Position Description; terminos repetidos 3+ veces; deseables.
   Clusters: dominio, proceso, riesgo/fiabilidad, stakeholder, conductual.
   La tabla vive en el bloque `keywords` de `out/<carpeta>/targets.yaml`, con
   estado, evidencia y, si hace falta, el sinonimo (ver "Keywords del aviso y
   sinonimos"). `build/keyword_check.py` la verifica y escribe `keyword-log.md`.
3. Match Depth por keyword.
4. **Seleccionar los logros de cada cargo segun el aviso, con script.**
   a. Escribir `out/<carpeta>/targets.yaml`: lo que pide el aviso traducido a
      `capabilities` del banco, con peso 1 a 3 (3 = criterio central). Ver el
      vocabulario con `python3 build/select_evidence.py --tags`.
   b. Correr `python3 build/select_evidence.py out/<carpeta>/targets.yaml`.
      Rankea TODO el banco, cargo por cargo, y escribe `evidence-log.md` (cada
      logro IN u OUT, con su motivo) y `selection.json`.
   c. Si el log marca un **EMPATE**, decidirlo con `prefer` o `exclude` en
      `targets.yaml`, con el motivo escrito al lado. Nunca dejarlo al azar.
   d. Solo se redacta desde las unidades IN. Para meter un logro que quedo
      fuera, se agrega a `prefer` con su motivo, no se escribe directo.
5. **Tesis de venta** (ver "Venderse" y "Orden de la experiencia"). Es el paso
   que hace que el CV piense desde Chile, no desde el empleo mas reciente:
   a. **Chile primero.** Para cada criterio esencial del aviso, buscar la
      evidencia PRIMERO en los roles con `block: origin`. Anotar en la tabla que
      rol chileno respalda cada criterio. Solo si Chile no lo cubre, se busca en
      Australia.
   b. **Mapa de transferibles.** Para cada rol con `block: australia`, una linea:
      que habilidad del aviso demuestra, con las palabras del aviso. Esa
      habilidad pasa a ser el titular de sus vinetas.
   c. **La tesis en una frase**, con esta forma: "<cargo y alcance en Chile> mas
      <habilidades transferibles probadas en Australia> encajan con <cargo del
      aviso> porque <criterio principal>." El Summary y la tesis de la carta se
      escriben desde esta frase.
   d. **Gaps.** Criterio sin evidencia en ningun bloque: gap. Va una sola vez, al
      final de la carta, en dos frases como maximo.
6. Rama del Professional Title y por que.
7. Todas las preguntas al candidato, juntas, en este mismo mensaje.

Nada se redacta hasta que esto existe.

### Pasada 2, borrador

Cada vineta lleva en `evidence` los ids del banco que la respaldan, solo de
`selection.json`. Sin eso `build/fit.py` no genera el CV.

Se redacta desde la tesis del paso 5: el Summary sigue su formula, los roles de
Chile llevan el peso de la evidencia y los australianos se titulan por su
habilidad transferible. El orden de los roles no depende del redactor:
`build/order.js` lo impone por bloque al generar.

CV completo mas el keyword log final (la tabla con una columna de estado:
aterrizo como estaba planeado / anadido en verificacion / learning target /
excluido a proposito, con el motivo de cada exclusion).

### Pasada 3, verificacion

1. `python3 build/fit.py out/<carpeta>/content.json`. Valida que cada vineta
   cite logros elegidos para el aviso, mide cada pagina en Chrome y, si el CV se
   pasa de 2 paginas, saca la vineta de menor relevancia para el aviso hasta que
   entre. Regenera md, html, docx y pdf, y deja los recortes en `fit_log`.
2. `python3 build/verify.py` sobre el CV y la carta.
3. `python3 build/ats_check.py out/<carpeta>`: todo archivo que se sube (PDF y
   DOCX de CV, carta y selection criteria) tiene que leerlo un ATS o una IA.
   `fit.py` ya lo corre; se repite si se genera otro documento despues.
4. Los cinco chequeos de juicio.

---

## Match Depth: define cuanto espacio recibe cada cosa

Esta es la regla que evita que el motor use siempre los mismos roles con el mismo
peso. Antes el Match Depth se calculaba y despues no se usaba para nada.

| Match Depth | Definicion | Como se usa |
|---|---|---|
| Direct | ha hecho el mismo trabajo o uno muy parecido | puede abrir el CV; se redacta como experiencia directa |
| Transferable | trabajo similar en otro contexto | siempre con su contexto; nunca redactado como Direct |
| Adjacent | exposicion, coursework, certificacion, relevancia parcial | 1 linea, en Skills o Certifications |
| Gap | sin evidencia defendible | fuera del CV. Solo carta, si acaso |

Un Transferable Match nunca se escribe como Direct Match.

El orden de los roles lo fija "Orden de la experiencia: Chile primero".

**Cuantas vinetas recibe cada cargo** lo decide `build/select_evidence.py`, no la
antiguedad: entran los logros que mas responden al aviso, con cupos por bloque
(por defecto Chile 4, Australia 2, resto internacional 1, rol concurrente 0;
ajustables en `targets.yaml`). Ver "Regla de los 7 segundos". Si el CV pasa de
12 vinetas o no entra en 2 paginas, `build/fit.py` recorta empezando por el
logro de menor relevancia.

---

## Professional Title

Antes de escribir la linea, clasificar el aviso: **pide titulacion de ingenieria,
trabajo de ingenieria o analisis tecnico como requisito?**

**Si** (Engineer, Analyst, Project Engineer, roles que exigen titulo o evaluacion
tecnica): titulo liderado por la credencial. Identidad defendible mas dos a cuatro
sustantivos de capacidad en el vocabulario del sector.
Ejemplo: `Industrial Engineer | Data Reliability, Reporting and Process Documentation`

**No** (Officer, Coordinator, Administrator, Technician y similares): titulo
liderado por capacidad, segun la regla de abajo.

### Regla de calibracion por sobrecualificacion

Cuando el rol no exige titulacion de ingenieria, el titulo abre con sustantivos
de capacidad en el vocabulario del propio rol. La credencial se mueve a Education
y a una clausula de apoyo del Professional Summary.

Ejemplo: `Operations and Reporting | Process Documentation and System Administration`

Razon: un panel que lee a un candidato obviamente sobrecualificado infiere riesgo
de fuga y riesgo de aburrimiento, y ninguno de los dos motivos aparece jamas en el
rechazo. Abrir con una credencial que el rol no pidio no compra nada y cuesta la
lectura.

La credencial nunca se oculta ni se niega. Se reposiciona.

**Estado de esta regla:** viene de feedback de un reclutador, julio 2026, fuente
unica. Es una hipotesis de trabajo, no un principio establecido. Registrar cada
postulacion donde se aplique y revisarla contra resultados reales.

Nunca un titulo de cargo que el usuario no haya ocupado.

---

## Orden de la experiencia: Chile primero

Decision del usuario, 2026-10-25, a partir de lo que le dijeron personas que si
encontraron trabajo. Fija para todas las postulaciones. Definida en
`experience_order` de `facts/roles.yaml`.

**Un solo encabezado PROFESSIONAL EXPERIENCE.** Sin sub-encabezados por pais. El
pais va en la linea de cada rol, con el mismo formato para todos
("Santiago, Chile", "Hobart, Tasmania, Australia"). No se complica.

Orden de bloques, segun el campo `block` de cada rol:

1. **Chile** (`origin`): la experiencia profesional. Siempre primero.
2. **Australia** (`australia`): prueba de habilidades transferibles y de
   adaptacion al entorno local.
3. **Resto internacional** (`international`): Irlanda y Alemania, una linea
   compacta al final.

Dentro de cada bloque: primero el rol mas relevante para el aviso segun Match
Depth. A igualdad, cronologico inverso.

Por que funciona: el primer titulo de cargo es lo que mas mira el reclutador en
el triaje (ver "Diseno para un escaneo de 7 segundos"). Con Chile primero ese
titulo es "Project Manager", y el reclutador encuadra el resto del CV, y la
entrevista, desde ahi.

Lo que NO se hace: esconder fechas ni el trabajo actual. Las fechas siguen en
cada linea de rol (regla ATS A7) y el Summary nombra el trabajo actual en
Australia. El orden cambia el encuadre, no oculta nada.

**Roles concurrentes.** Un rol part time que solapa con otro (un emprendimiento
paralelo a un empleo) va ANIDADO bajo el rol principal, con la etiqueta "Concurrent, part time".
Nunca como entrada propia en la linea temporal, nunca sumando su duracion.

Nota ATS: algunos portales autocompletan el "cargo actual" con la primera entrada
del CV. Antes de enviar por SEEK o similar, revisar ese campo del formulario.

## Venderse: encuadre, no afirmaciones nuevas

El CV sostiene una sola tesis: **la experiencia profesional acumulada en Chile,
mas las habilidades transferibles probadas en Australia, son adecuadas para este
cargo.** Cada seccion empuja en esa direccion.

- **Summary**: base profesional en Chile (cargo, alcance, anos) -> habilidades
  transferibles probadas en Australia -> encaje con el rol. Ver item 3 abajo.
- **Roles australianos**: se encuadran por la habilidad transferible que
  demuestran, con el vocabulario del aviso en los titulares de vineta.
- **Lineas de contexto**: nunca autodisminuyentes. Prohibido anunciar una bajada
  ("currently working operationally on days off", "management responsibilities
  held in the period before that"). La `tense_rule` de Panorama se cumple con los
  logros de gestion en pasado, no con una linea que lo explique.
- **Anos de experiencia**: Chile 2019 a 2022 son "around three years". Un rol
  concurrente no suma anos. Nunca redondear hacia arriba.

Lo que vender NO es: un Transferable escrito como Direct, un sustantivo inflado,
un cargo no ocupado, una cifra redondeada. Vender opera sobre el orden, el
encuadre y la redaccion. Las afirmaciones siguen saliendo de `facts/`.

`build/verify.py` avisa (UNDERSELL) cuando detecta frases que restan, y falla
(ORDER) si un rol aparece fuera de su bloque.

## Keywords del aviso y sinonimos

Decision del usuario, 2026-10-26: **es de vital importancia usar las keywords del
aviso.** Un reclutador y un ATS buscan las palabras del aviso, no las de `facts/`.

**El sistema puede usar sinonimos de los hechos para que coincidan con las
keywords del aviso.** Si `facts/` dice "signed daily traceability log" y el aviso
dice "audit", el CV puede decir "audit trail". Si `facts/` dice "dashboard of
monthly sales, average margin" y el aviso dice "KPIs", el CV puede decir "KPI
dashboard". No hace falta preguntarle al usuario por cada sinonimo.

Un sinonimo es valido si:
1. **Nombra lo mismo que ocurrio**, con el mismo alcance. Responde a "what exactly
   was it?" con el hecho de `facts/` sin estirarlo.
2. **No sube** cargo, seniority, propiedad del trabajo (initiated -> built),
   frecuencia (on request -> monthly), escala ni formalidad (log firmado -> audit
   programme).
3. **No es una herramienta.** Power BI, SQL, Jira, SAP: solo si estan literales en
   `facts/`. Una herramienta nunca se cubre por sinonimo (`kind: tool`).
4. **No toca un cargo.** Los titulos salen de `facts/roles.yaml`, sin sinonimos.
5. **No esta en `facts/prohibitions.yaml`** ni choca con un `never_with`.

Como se registra, en el bloque `keywords` de `targets.yaml`:

```
keywords:
  - keyword: "KPIs"                      # textual del aviso
    weight: 3
    status: cv                           # cv | letter | demonstrated | gap | excluded
    match: ["KPI"]                       # formas que cuentan como aparicion literal
    evidence: [ecyt_database_dashboards]
    synonym_of: "dashboard of monthly sales, average margin"   # literal en facts/
```

Lo que impone `build/keyword_check.py` (lo corre `fit.py`; sin esto no se entrega):
- Toda keyword `cv` aparece literal en el CV; toda `letter`, en la carta.
- Toda keyword cubierta cita evidencia verificada; en el CV, elegida para el aviso.
- Si la keyword no esta en el hecho citado, `synonym_of` es obligatorio y tiene que
  existir literal en ese hecho. Asi cada sinonimo se rastrea hasta `facts/`.
- Herramientas y cargos no pasan por sinonimo.
- `gap` y `excluded` llevan motivo. Nada se omite en silencio.

Prioridad: una keyword con evidencia va al CV con la palabra del aviso, en una
vineta, el Summary o Skills. Las de peso 3 que quedan solo en la carta generan
aviso. Las habilidades blandas (communication, attention to detail) van como
`demonstrated`: se prueban con hechos, no se escriben como etiqueta.

## Estructura y limites

1. **Header** (fijo): nombre, ubicacion y disposicion a reubicarse si aplica,
   telefono, email, derechos de trabajo, licencia de conducir si el rol implica
   terreno o desplazamientos.
2. **Professional Title** (a medida): ver arriba.
3. **Professional Summary** (a medida): **maximo 55 palabras**, 3 lineas. Formula
   fija: (1) base profesional en Chile, con cargo, alcance y anos; (2) habilidades
   transferibles probadas en Australia, nombrando el trabajo actual; (3) encaje
   con el rol. Abre con lo que hizo, no con una etiqueta. Se permite nombrar al empleador una sola vez,
   en la frase de cierre. Maximo una frase de learning target. Sin cliches, sin
   etiquetas de soft skills, sin biografia.
4. **Skills** (a medida): **SOLO NOMBRES. Tres lineas agrupadas, sin frases de
   evidencia.** Cada linea lleva una etiqueta corta en el margen izquierdo y como
   maximo 4 terminos separados por " | ", tomados del aviso y de la PD.
   - **Prohibido repetir aqui la evidencia que ya esta en Experience.** Ese
     solapamiento era la principal fuente de sobrecarga del CV: el reclutador leia
     lo mismo dos veces y el documento se sentia denso sin aportar nada nuevo.
   - La condicion no cambia: **todo termino listado tiene su vineta en Experience
     que lo respalda.** Skills nombra la promesa, Experience la cumple. Un termino
     sin respaldo es keyword stuffing y se borra.
   - Nunca learning targets (ver Learning Alignment Rule).
5. **Professional Experience**: un solo encabezado, ordenado por bloques (ver
   "Orden de la experiencia: Chile primero"). Por rol: linea de titulo (titulo,
   organizacion, ciudad, pais, fechas), linea de contexto opcional en cursiva y
   sin vineta, vinetas de logro, y roles concurrentes anidados si los hay.
   - **Vinetas de 15 a 25 palabras**, una o dos lineas. Por encima de 25 el
     escaneo no las alcanza y algunos ATS las truncan.
   - El resultado va en las primeras palabras de la vineta.
   - La evidencia cierra la misma vineta que su metodo.
   - Los periodos de baja relevancia se comprimen a una linea.
6. **Education** (fijo), **Certifications** (fijo, **solo las del rol**, agrupadas
   con " | " en 2 lineas como maximo).
7. **Referees**: **fuera del CV por defecto.** Solo se incluyen si el aviso o el
   portal los piden. No se leen en el filtro inicial y cuestan cuatro lineas.
   Viven en `facts/roles.yaml` y se entregan cuando los piden.

**Maximo 2 paginas, garantizado por `build/fit.py`.** Si falta espacio se cortan
vinetas de Experience por orden de relevancia para el aviso, nunca la estructura
de Summary o Skills.

## Regla de los 7 segundos: el CV se arma para el escaneo, no para la lectura

Decision del usuario, 2026-10-25, a partir de la postulacion TasWater Business
Analyst: la version con 17 vinetas estaba "muy sobrecargada". La de 11 vinetas
es la referencia.

**Principio:** el CV se ARMA desde el principio para que un reclutador entienda
en 7 segundos quien es el usuario y por que encaja. No se escribe completo y despues se
recorta: cada seccion nace con su presupuesto. Si algo no cabe en el
presupuesto, se queda en el banco o pasa a la carta, que es donde hay espacio
para contar mas.

Presupuestos (los hace cumplir el codigo, no el ojo):

| Elemento | Presupuesto | Quien lo impone |
|---|---|---|
| Professional Summary | maximo 55 palabras | `build/fit.py` (falla) |
| Skills | 3 lineas de maximo 4 terminos | `build/fit.py` (falla) |
| Vinetas por vineta | 15 a 25 palabras | `build/fit.py` (falla si pasa de 25, avisa bajo 15) |
| Vinetas en total | maximo 12 en todo el CV | `build/fit.py` (recorta por relevancia y lo registra) |
| Vinetas por cargo | Chile 4, Australia 2, resto internacional 1, concurrente 0 | `build/select_evidence.py` (cupos por defecto) |

Como se aplica:

- **Un logro por idea.** Si dos vinetas prueban lo mismo (dos automatizaciones
  de pedidos), entra la mas fuerte y la otra se queda en el banco.
- **Menos cargos con mas aire, no mas cargos apretados.** Un rol concurrente
  (por ejemplo, un emprendimiento paralelo) no entra por defecto; se pide en `targets.yaml` solo si el aviso
  lo necesita.
- **El espacio en blanco es parte del diseno.** Una pagina 2 a medio llenar no es
  un problema; una pagina 1 densa si lo es.
- **La pagina 1 lleva Chile y el rol australiano mas relevante.** Lo que el
  reclutador ve en el primer barrido tiene que contar la tesis completa.
- **Lo que sale del CV no se pierde:** la carta puede contar los logros que el
  CV no muestra, siempre desde `facts/`.

Los cupos y el total se pueden subir en `targets.yaml` (`max_per_role`,
`bullet_budget`) solo con un motivo escrito al lado.

## Diseno para un escaneo de 7 segundos

El triaje inicial de un reclutador dura alrededor de 7,4 segundos (estudio de
eye-tracking de Ladders, 2018), en patron F: borde superior, despues margen
izquierdo. Cerca del 80% de esa atencion va a nombre, cargo actual, empleador
actual, cargo anterior, empleador anterior, fechas y educacion. **Los titulos de
cargo reciben la mayor atencion de todos.**

Consecuencias operativas, no decorativas:

- **Revisar que titulo de cargo ve primero el reclutador.** Si el cargo mas
  reciente no se parece al aviso, el posicionamiento tiene que hacerlo el
  Professional Title de la cabecera y la primera frase del Summary, que estan
  por encima.
- **El rol mas relevante tiene que quedar en la pagina 1, o abriendo la pagina 2.**
  Enterrado a media pagina 2 no existe para un triaje de 7 segundos.
- **Ningun bloque de rol se parte en el corte de pagina** (`break-inside: avoid`).
  Un encabezado huerfano al pie de la pagina 1 desperdicia la posicion.
- **El margen izquierdo carga el escaneo**: etiquetas de Skills y titulares de
  vineta en negrita, alineados a la izquierda.
- **Las keywords del aviso van resaltadas** (El usuario, 2026-10-26). En una vineta o en
  el Summary se marca `**keyword**` en content.json y sale en negrita en HTML, PDF
  y DOCX. Solo keywords con estado `cv` en `targets.yaml` (`keyword_check.py`
  falla con HIGHLIGHT si no) y maximo 2 resaltados por vineta contando el titular
  (`fit.py` falla si se pasa). Si todo esta en negrita, nada resalta.
- **Nada de parrafos largos.** El Summary son 3 lineas, no un bloque.

---

## Reglas duras

- Nombre: **"The user"**, nunca con acento.
- **Cero em dashes**. Verificar por script, nunca a ojo.
- **Ingles australiano**: organise, standardised, recognised, licence (sustantivo),
  programme, centre.
- **Maximo 2 paginas**, garantizado por `build/fit.py` y contado por `verify.py`.
- Toda cifra aproximada lleva "approximately" o "around". Las exactas solo si
  estan verificadas.
- **Todo porcentaje lleva su cifra base en la misma frase.** Un porcentaje sin
  base es un patron de inflacion.
- Sin pronombres en primera persona en las vinetas del CV (en la carta si).
- Sin adjetivos vacios ni etiquetas autoevaluativas: las magnitudes hacen el
  trabajo persuasivo.
- Nunca sumar grupos que se solapan.

### Principio de de-inflacion

La verdad no se viola solo con afirmaciones falsas, tambien con sintagmas
nominales que exageran lo que algo era.

Todo sintagma nominal debe sobrevivir la pregunta de entrevista:
**"what exactly was it?"**

Ejemplo canonico: "sole administrator of a live operational database" exagera lo
que era un sistema de gestion hotelera. "sole administrator of a live operational
management system and product database" sobrevive la pregunta. La version
de-inflada no es mas debil: es mas creible, y la credibilidad siempre gana.

Al revisar un borrador, caza sustantivos inflados igual que cazas metricas
inventadas.

### Regla de alineamiento de aprendizaje

Los learning targets no son skills.

Una linea como "motivated to develop capability in X, Y and Z" no pertenece nunca
a Key Skills, por muchas keywords del aviso que capture. A un revisor humano le
suena a relleno de keywords y rompe la estructura de promesa de la seccion.

Los learning targets tienen exactamente dos casas: una frase como maximo en el
Professional Summary, y la carta, donde el gap se nombra honestamente.

Los keywords tecnicos sin evidencia se declaran como gap en la carta o se excluyen
a proposito. La exclusion se registra en el keyword log, nunca es silenciosa.

---

## Verificacion

### Nivel 1: automatico

`python3 build/verify.py <archivo>`

Cubre: em dashes, nombre con acento, prohibiciones, fechas contra `roles.yaml`,
titulos prohibidos, porcentajes sin base, cifras sin "approximately", ingles
australiano, extraccion de contacto, conteo de paginas.

Si devuelve fallos, se corrigen ANTES de pasar al nivel 2.

`python3 build/ats_check.py out/<carpeta>` cubre lo que verify.py no puede ver,
porque verify.py lee el .md y el portal recibe PDF y DOCX: extrae el texto de
cada archivo y comprueba que una maquina lo lea entero, en orden y sin
caracteres rotos (ver `build/ats-checks.md`, seccion B). Un documento que se ve
perfecto puede leerse mal: ligaduras que rompen emails, un nombre con letras
espaciadas, etiquetas separadas de sus terminos. Sin ats_check.py en verde no
se entrega.

### Nivel 2: requiere juicio (solo estos cinco)

1. Cada termino de Skills tiene su vineta en Experience que lo respalda, y
   ninguna frase de evidencia esta duplicada entre Skills y Experience.
2. Cada vineta de logro tiene su cadena completa, con la evidencia cerrando la
   misma vineta.
3. De-inflacion: cada sintagma nominal sobrevive "what exactly was it?".
4. Ningun Transferable Match esta escrito como Direct Match.
5. Nada del documento fallaria la prueba de defensibilidad en entrevista.

---

## Entrega

DOCX mas PDF. El keyword log con su columna de estado. La lista de lo que queda
del lado del usuario: envio por el portal, fecha limite, decisiones pendientes, y
cualquier supuesto que el sistema haya hecho y que el usuario deba confirmar antes de
enviar.

---

## Regla final

Ante la duda entre una afirmacion mas fuerte y una mas verdadera, gana la mas
verdadera. Un CV mas debil que sobrevive la entrevista le gana a un CV mas fuerte
que se derrumba en ella.

Ante la duda entre lenguaje generico de logro y lenguaje de valor especifico del
sector, gana el especifico, mientras siga siendo verdad.

## Reglas v2 (P-9, aprobadas por el usuario 2026-11-20)

Se activan por CV con `"rules_version": "v2"` en `content.json` (las reglas v1 de arriba siguen para los CV
anteriores). Donde chocan, v2 gana para los CV v2.

1. **El Summary es el gancho; el resto lo corrobora.** Se escribe para ESTA oferta y ESTE lector: la primera
   frase nombra lo que el rol necesita, con palabras del aviso, y lo responde con la prueba mas fuerte
   (credencial + el resultado mas cercano al rol). Hasta **90 palabras**: credencial, capacidades, **2-3
   resultados medidos** y **una linea de objetivo** ("Targeting opportunities in X, Y within <empleador>").
   Se redacta AL FINAL, cuando las vinetas ya estan fijas. Cada afirmacion va en `summary_claims`
   (`[{text, proves_with: [ids de evidencia o credencial]}]`) y cada cifra se repite mas abajo con su base;
   `fit.py` falla si una afirmacion o cifra no tiene prueba.
2. **Seccion PROJECTS** para evidencia sin empleador (`role: null`): `projects: [{name, tag, line, dates,
   evidence}]`, `projects_heading`, `projects_position: before_experience | after_experience`. Respeta el
   `attribution_rule` de cada item (por ejemplo nunca "coded" si el codigo lo escribio una IA).
3. **Encabezados por tema** opcionales: `experience_headings: {origin: ..., australia: ..., international: ...}`.
   El orden de bloques (origen primero) no cambia. Cada encabezado contiene la palabra EXPERIENCE (ATS).
4. **Porcentajes derivados**: de un antes/despues verificado, siempre con su base en la misma frase y con
   "approximately". `fit.py` recalcula cuando la base es numerica. Los items con "nunca solo" lo mantienen.
5. **Skills**: hasta **8 terminos** por linea (solo nombres; herramientas literales en `facts/`).
6. **Credencial profesional** en su propia linea de EDUCATION; pie con nombre, identidad y "Page n of N".
7. **Registro de industria pesada** (mineria, procesos, plantas): controls, handover, pre-use testing,
   safety-critical, site requirements. Nunca cambia un hecho.
8. **Controles que se mantienen** (fallan en `fit.py`): una capacidad que es solo objetivo (gap) no va en la
   linea de capacidades sino en la linea de objetivo; herramienta no literal en `facts/` bloquea; un rol
   terminado va en pasado; la linea de disponibilidad se mantiene si `available_from_display` existe.
9. **Diseno compacto** (`"layout": "compact"`, usuario 2026-11-20): cuerpo 9,8 pt, interlineado y espacios
   apretados, texto alineado a la izquierda, cabecera baja, contacto en 2 lineas y pie fino con nombre,
   identidad y "Page n of N" en todas las paginas. La fecha va a continuacion de la empresa, en letra normal:
   una fecha muy a la derecha o en negrita se lee separada del cargo en el PDF (ATS ROLES). La empresa debe
   caber en una linea. `"bullet_headlines": false` quita el titulo en negrita de las vinetas (la keyword sigue
   en Skills).

