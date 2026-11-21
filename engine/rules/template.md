# Template del CV: lo que necesita quien escribe

La geometria, tipografia y reglas ATS se movieron a `build/layout.md` y
`build/ats-checks.md`. No se cargan al redactar.

**FIJA** = igual en todas las postulaciones. **TAILOR** = se reescribe por rol.

## Mapa de placeholders

```
{{identity_line}}          TAILOR  linea 2 de cabecera y pie de pagina 2.
                                   Rama liderada por credencial o por capacidad,
                                   segun la clasificacion de rules/cv.md.
{{capability_nouns}}       TAILOR  linea 3 de cabecera. Dos a cuatro sustantivos
                                   de capacidad, separados por " | ".
{{location_line}}          TAILOR  "<ciudad>, <estado>" mas
                                   "(willing to relocate to {{city}})" solo
                                   cuando sea relevante para el rol.
{{professional_summary}}   TAILOR  maximo 55 palabras (regla de los 7 segundos). El empleador se nombra
                                   una vez como mucho, en la frase de cierre.
{{skills[3]}}              TAILOR  SOLO NOMBRES. Tres grupos {label, terms}.
                                   Maximo 4 terminos por grupo, separados por " | ".
                                   Sin frases de evidencia: esa vive en Experience.
{{experience[]}}           hechos FIJA, seleccion y enfasis TAILOR. Ordenado por
                                   bloque: Chile, Australia, resto internacional
                                   (experience_order en facts/roles.yaml).
  {{role_title_line}}              "**{{Titulo}} |** {{Organizacion, Ciudad, Pais}} {{Fechas}}"
  {{context_line?}}                cursiva, sin vineta, opcional. Nunca autodisminuyente.
  {{concurrent[]?}}                roles part time concurrentes, anidados bajo el
                                   rol principal: {label, title, org, bullets[]}.
                                   Sin fechas propias.
  {{bullets[]}}                    titular de valor + cadena verbo/resultado/metodo/evidencia,
                                   15 a 25 palabras por vineta
                                   `evidence`: ids de selection.json que la respaldan
{{education[]}}            FIJA
{{certifications[]}}       FIJA, filtradas por rol
{{referees[]}}             FIJA
{{statement?}}             TAILOR  opcional. Selection criteria statement, solo si el
                                   portal lo pide. Ver rules/cover-letter.md.
```

## Orden de secciones (fijo)

Pagina 1: cabecera, franja de contacto, PROFESSIONAL SUMMARY, SKILLS,
PROFESSIONAL EXPERIENCE (empieza aqui).

Pagina 2: continuacion de PROFESSIONAL EXPERIENCE, EDUCATION, CERTIFICATION.

Con el orden Chile primero, lo normal es que el bloque de Chile llene la pagina 1
y que el primer rol australiano abra la pagina 2 (`page_break_before` en ese rol).
Si el bloque de Chile no llena la pagina 1, el corte va en el rol siguiente que
deje la pagina 1 llena sin partir un bloque.
REFEREES solo si el aviso los pide.

Las paginas son CAJAS EXPLICITAS de altura A4 exacta, no flujo continuo. El
rol marcado con `page_break_before: true` en content.json abre la pagina 2. Asi
la banda navy de pie queda anclada al borde inferior real de la ultima pagina.

Por que: con flujo continuo la banda queda flotando justo despues del ultimo
texto, a media pagina, y la hoja se lee como cortada. `margin-top:auto` en flex
y `position:absolute` NO funcionan en impresion paginada de Chrome: el primero
no ancla y el segundo hace desaparecer la banda. Probado 2026-10-17.

Las cajas no llevan `overflow:hidden` a proposito: si algo se desborda tiene que
verse, no perderse en silencio. El conteo de paginas del PDF lo confirma.
El rol mas relevante para el aviso va en la pagina 1 o abriendo la pagina 2.

**Limite duro: 2 paginas.** Si falta espacio se cortan vinetas de Experience o
Certifications. Nunca la estructura de Summary ni de Skills.

La linea de identidad del pie de la pagina 2 debe coincidir con la linea 2 de la
cabecera. Un pie que dice "Industrial Engineer" bajo una cabecera liderada por
capacidad contradice la regla de calibracion por sobrecualificacion.

## Advertencia de contenido

El PDF de origen del que se extrajo este layout contiene texto de ejemplo que
**nunca se copia**: es anterior al banco de hechos y viola reglas vigentes
(de-inflacion, cifras superadas, roles no verificados). El detalle, con los
hechos del candidato, esta en `private/rules-notes.md`.

El motor rellena este template exclusivamente desde `facts/`.
