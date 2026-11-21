# Reglas de la carta de presentacion

Sustituye a Cover_Letter_Writing_Guide.md y Cover_Letter_Generation_Rules.md.
El material anti-plantilla se movio a `voice/anti-slop.md` y aplica tambien al CV.

## Que hace la carta

El CV prueba capacidad. La carta prueba **encaje y comprension**. Responde otra
pregunta: *entiende esta persona nuestro mundo, nuestro rol y nuestros riesgos, y
sabe mostrar por que su evidencia encaja?*

Cada parrafo demuestra encaje con un hecho verificable o demuestra comprension del
contexto del empleador. Lo demas es relleno.

Hereda del CV: el mismo `voice/sector-<x>.md`, la misma clasificacion de
empleador, el mismo Match Depth. La carta comprime la verdad, nunca la estira.

## Arquitectura de cinco capas

1. **Tesis.** Primera frase: identidad corta (que es, no donde trabajo). Anclas
   de credibilidad. Frase de cierre: tesis de encaje especifico con ESTE rol.
   Nunca una afirmacion generica de confianza, porque le sirve a cualquiera.

2. **Comprension del rol.** Un parrafo corto que demuestra que entiende para que
   se usa el output del rol y que esta en juego: quien consume el trabajo, que
   decisiones dependen de el, cual es el entorno de riesgo.
   Cuidado: es sobre el mundo del empleador, no sobre la carta. "por eso he
   enfocado mi postulacion en..." es meta-comentario; mejor conectar lo que esta
   en juego con el estandar de trabajo propio.

3. **Cuerpo en espejo con los criterios.** 3 a 4 titulares tomados del aviso, un
   parrafo cada uno. Los evaluadores puntuan contra una grilla: si los titulares
   son sus criterios, la carta les entrega el mapa hecho.
   Los titulares no se copian literales de la Position Description si suenan
   burocraticos. Se convierten en temas de trabajo naturales, preservando el
   vocabulario nuclear del empleador.
   Mal: "Communication and interpersonal skills, with clear, accurate and concise reports"
   Bien: "Clear communication, reports and user support"

4. **Evidencia cuantificada.** Magnitudes en vez de adjetivos. Toda cifra
   aproximada lleva "approximately" o "around". Todo porcentaje lleva su base.
   Nunca se inventa un numero: se pregunta.

5. **Cierre no replicable.** Un elemento que solo el usuario puede decir: residencia
   local, compromiso con el estado, situacion vital, disponibilidad. Para roles
   tasmanos, la presencia local es el diferenciador. Ver la regla de ancla
   personal en `voice/anti-slop.md`. Gracias breves y disponibilidad. Sin ruegos,
   sin repetir.

## Keywords del aviso

Mismas reglas que el CV ("Keywords del aviso y sinonimos" en `rules/cv.md`): la
carta usa las palabras del aviso, y un sinonimo de un hecho se permite si nombra
lo mismo que ocurrio. Las keywords que solo van en la carta se marcan `letter` en
`targets.yaml` y `build/keyword_check.py` comprueba que aparezcan.

## Afirmacion explicita del criterio

Agregada 2026-10-21, a partir de la postulacion TasWater Business Analyst.

Los evaluadores son humanos y leen rapido. Si la carta muestra los hechos pero no
dice que cumplen el criterio, el evaluador tiene que hacer la conexion solo, y un
evaluador apurado no la hace. La carta no es literal en el sentido de esperar que
el panel deduzca: afirma.

Regla: en cada criterio esencial donde the user tenga evidencia Direct o Transferable,
el parrafo **nombra el criterio con las palabras del aviso y afirma que el usuario tiene
esa experiencia**, y en la frase siguiente la respalda con hechos.

Forma recomendada para Transferable: "My <criterio> experience comes from <roles>."
Dice de donde viene la experiencia sin fingir un cargo que no tuvo.

- Bien: "My business analysis experience comes from two roles. As Project Manager..."
- Mal (demasiado timido): un parrafo de hechos titulado "Analysing processes" que
  nunca dice "business analysis".
- Mal (inflado): "I am an experienced Business Analyst." Cargo nunca ocupado.

Lo que no cambia: un Transferable sigue sin escribirse como Direct, nunca se
afirma un cargo no ocupado, y cada afirmacion se respalda con un hecho de
`facts/` en el mismo parrafo. El objetivo es generar confianza en que el usuario puede
hacer el trabajo, y la confianza viene de afirmar con claridad Y probar en la
frase siguiente.

## Gaps honestos

Cuando el aviso invita a postular sin cumplir el 100 por ciento, la carta nombra
el gap directamente, en una frase, sin disculparse.

La declaracion del gap solo funciona seguida de **evidencia de cierre de gap**:
un caso real y verificable donde el usuario entro en frio a un dominio y se volvio
fiable en el. Los casos en curso pesan mas que los pasados, porque prueban que la
conducta es actual.

Nunca simular conocimiento de dominio para suavizar un gap. Un gap nombrado mas
prueba de aprendizaje le gana siempre a un gap difuminado.

El parrafo de gap incluye TODOS los dominios criticos que faltan. Dejar uno fuera
en silencio viola la regla de gap de keywords criticos, que aplica igual a la
carta que al CV (ver `rules/cv.md`).

**Posicion y tamano del gap** (agregado 2026-10-25, "venderse"):

- Se declara **una sola vez**. Prohibido nombrarlo en la tesis y repetirlo al final.
- Va **despues del cuerpo**, antes del cierre. Nunca en el primer parrafo: la
  tesis es la posicion de mas atencion de la carta y se usa para la fortaleza.
- **Maximo dos frases**: una que nombra el gap, otra con la prueba de cierre.
- Sin encabezado propio. Los encabezados son para los criterios del empleador.

## Orden de la evidencia en la carta

Mismo criterio que el CV (ver "Orden de la experiencia" y "Venderse" en
`rules/cv.md`):

- La tesis y el cuerpo **abren con la experiencia profesional en Chile**. Es la
  base de la candidatura, no un antecedente.
- La evidencia australiana entra como **prueba de que esas habilidades se
  transfieren** y de adaptacion al entorno local. Forma recomendada: "Since
  moving to Australia I have applied the same <habilidad> to <hecho>."
- Cada criterio esencial del aviso tiene su parrafo. Si un criterio queda sin
  tocar (por ejemplo "commercial focus balanced by a customer centric approach"),
  se busca la evidencia en Chile antes de darlo por gap.

## Encaje cultural: demostrado, no declarado

Por defecto, los valores del empleador se demuestran con hechos, nunca se declaran
como etiquetas. "Su valor de X describe como trabajo" es una declaracion; la frase
de evidencia anterior es la demostracion. Las declaraciones suenan a cliche y no
suman puntos.

Excepcion documentada: se permite un eco literal de UN solo valor del empleador,
si esta anclado a un hecho concreto en la misma frase o en la anterior. Un valor
por carta como maximo. Es una decision consciente que se registra en las notas de
generacion, no un comportamiento por defecto.

## Forma

- Maximo una pagina. La carta es un mapa, no un ensayo.
- Primera frase corta. Ninguna frase por encima de unas 35 palabras.
- Dirigida a un nombre o a un equipo si se conoce ("Dear Hiring Panel", "Dear
  [Company] Recruitment Team"). Nunca "To Whom It May Concern".
- Tono australiano regional, directo y factual: sin disculpas, sin rodeos, sin
  lenguaje de venta.
- Honestidad en tono llano ("I am upfront about that") antes que honestidad
  teatral ("I will not pretend otherwise").
- Sin comparaciones no verificables ("un entorno mas duro que el suyo"); usar
  encuadre factual ("a demanding operational environment").
- La carta y el CV no se contradicen en ningun hecho, cifra ni sintagma. La carta
  puede comprimir, nunca inflar.
- Primera persona: normal aqui, a diferencia de las vinetas del CV.
- La fecha es la de generacion y se actualiza en cada regeneracion. Una fecha
  vieja es un fallo de verificacion.

## Antes de entregar

Pasa `voice/anti-slop.md` completo: AI Smell Check, regla de ritmo de frase,
capa de voz humana, regla de ancla personal.

Despues:

- Cada criterio del aviso tiene su parrafo?
- Cada parrafo tiene al menos un hecho verificable con magnitud?
- Se demuestra que entiende lo que esta en juego?
- El gap, si existe, esta nombrado una vez, honestamente, y respondido con
  evidencia de cierre?
- El cierre dice algo que solo el usuario podria decir?
- Cada frase sobrevive ser leida en voz alta en la entrevista?

## Selection criteria statement

Agregado 2026-10-25, a partir de la postulacion TasWater Business Analyst. Solo
cuando el portal lo pide. Se escribe en el bloque `statement` de content.json y
lo generan los mismos scripts que el CV y la carta (`selection-criteria.md`,
`.html`, `.docx`, `.pdf`):

```
"statement": {
  "date": "25 October 2026",
  "title": ["Selection Criteria Statement", "<cargo>, <equipo>, <empleador>"],
  "criteria": [{"heading": "<criterio literal del aviso>", "text": "..."}]
}
```

- **Si el portal no da formato**: documento aparte, maximo 2 paginas (lo hace
  cumplir `build/fit.py`), un titulo por criterio con las palabras LITERALES del
  aviso, 120 a 180 palabras por criterio, y un bloque final corto para los
  "highly regarded".
- **Cada criterio, un caso concreto con resultado** (situacion, accion,
  resultado), en primera persona. Mismas reglas de hechos que la carta: todo de
  `facts/`, sin contradecir ninguna cifra del CV ni de la carta.
- **Chile primero**, Australia como prueba de que se transfirio. Igual que el CV.
- **Usar la evidencia que el CV dejo fuera** por la regla de los 7 segundos: el
  statement tiene espacio y el panel ya leyo el CV.
- **Proyectos de la carrera**: el criterio de titulacion se respalda con un
  proyecto presentado al skills assessment de Engineers Australia
  (`ea_skills_assessment` en evidence.yaml), siempre como trabajo en equipo.
- **Gaps**: una sola vez, en el bloque de deseables, en una frase y sin disculpa.
- **Maquetacion**: margen de 16 mm en CADA pagina y cada titulo pegado a su
  parrafo. La carta solo tiene margen al inicio y al final: con ese estilo el
  statement se veia cortado en el salto de pagina.
- Pasa `verify.py` (agregar `selection-criteria.md`) y `ats_check.py`.

## Regla final

La carta comprime la verdad; nunca la estira. Si una frase suena mas fuerte que
el hecho que hay detras, se reescribe la frase, no el hecho.
