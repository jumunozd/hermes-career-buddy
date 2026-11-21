---
asset: ats-hardening
consumidor: los generadores de build/ y build/ats_check.py. NUNCA se carga al redactar.
---

# Endurecimiento ATS

Ningun template es "a prueba de ATS" en absoluto; sistemas concretos (PageUp,
Workday, SEEK, Springboard y otros) se comportan distinto y cambian con el tiempo.
Estas reglas minimizan el riesgo de parseo estructural y son requisitos de
aprobado/suspenso, no sugerencias.

## A. Reglas de construccion (como se construye el DOCX)

**A1. Identidad y contacto en el cuerpo, nunca en el header/footer de Word.**
Nombre, titulo profesional, linea de capacidades, ubicacion, telefono, email,
derechos de trabajo y licencia deben ser parrafos de cuerpo (con sombreado para
las bandas). Muchos ATS ignoran por completo las regiones de header y footer: un
nombre o telefono ahi puede no parsearse nunca. El unico footer permitido es la
banda navy decorativa de la pagina 2, que no duplica informacion unica.

**A2. Sin cuadros de texto, formas ni marcos flotantes.** Todo el texto vive en el
flujo normal de parrafos (o, como mucho, una tabla de una celda sin bordes para
las bandas). El texto dentro de objetos de dibujo se descarta rutinariamente.

**A3. Una sola columna, orden de lectura lineal.** Sin layouts en paralelo, sin
secciones multicolumna. El orden visual debe ser igual al orden del XML.

**A4. Tracking via `characterSpacing`, nunca con espacios literales.** El nombre
debe extraerse como `JUAN MUNOZ`, no como `J U A N  M U N O Z`. Igual para el
titulo. En el PDF (CSS `letter-spacing`) el limite es 4pt en el nombre y 1pt en
el titulo: con 7pt el extractor ya separaba las letras (medido 2026-10-25).

**A5. Vinetas reales via `numbering.xml`** (`numFmt="bullet"`), nunca caracteres
pegados ni sangrias manuales.

**A6. Solo titulos de seccion estandar**: PROFESSIONAL SUMMARY, SKILLS,
PROFESSIONAL EXPERIENCE, EDUCATION, CERTIFICATION, REFEREES. Sin renombres
creativos: los parsers mapean secciones por estas etiquetas.

**A7. Fechas en texto plano en la linea de titulo del rol**, formato
`Mon YYYY - Present` o `YYYY - YYYY`, en el mismo parrafo que titulo y
organizacion. Sin trucos de tab stop que separen la fecha en otra linea del XML.
Con el orden Chile primero (no cronologico inverso), esta regla es la que permite
al parser reconstruir la linea temporal: cada rol lleva su fecha explicita. Los
roles concurrentes anidados no llevan fecha propia y no cuentan como entrada.

**A8. Sin texto invisible ni fuera de lienzo.** El texto blanco sobre blanco (como
el que traia el PDF de Canva original) contamina el parseo y puede leerse como
relleno de keywords. Tolerancia cero.

**A9. Fuentes embebidas o sustituidas deliberadamente.** Un fallback silencioso
cambia las metricas y puede empujar contenido a una tercera pagina. Confirmar con
`fc-list` antes de convertir.

## B. Chequeos programaticos (cada generacion, DOCX y PDF)

Los implementa `build/ats_check.py` sobre TODOS los archivos que se suben al
portal (CV, carta y selection criteria, en PDF y DOCX). `build/fit.py` lo corre
al terminar y no entrega si falla. `bash build/selftest.sh` demuestra que
detecta cada fallo. Codigo de fallo entre corchetes.

En el Mac no hay `pdftotext`: el script usa PDFKit (`build/pdftext.swift`). Si no
hay ningun extractor, falla. Nunca se aprueba un archivo sin haberlo leido.

**B1. Extraccion de contacto.** [CONTACT] La salida de `pdftotext` de la pagina 1 debe
contener, literalmente: el `name_on_documents` (sin distinguir mayusculas), el `phone`,
el `email` de `facts/identity.yaml`. Ejecutar el equivalente sobre el XML del DOCX
(`word/document.xml`), porque algunos portales parsean el DOCX directamente.

**B2. Orden de lectura.** [ORDER] En el texto extraido, el orden debe ser nombre, titulo,
contacto, PROFESSIONAL SUMMARY, SKILLS, PROFESSIONAL EXPERIENCE, y despues las
secciones de la pagina 2. Cualquier desviacion suspende.

**B3. Texto corrupto.** [CHARS, SPACED, EMPTY] La extraccion no debe contener runs entrelazados ni
corruptos (el artefacto de texto blanco de la pagina 2 del PDF original producia
`JHoUspitalitAy...`). Cualquier galimatias de ese tipo suspende.

**B4. Contenido en header/footer.** [HEADER] Descomprimir el DOCX: `word/header*.xml` y
`word/footer*.xml` no deben contener telefono, email ni texto unico mas alla de la
banda decorativa de la pagina 2.

**B5. Etiquetas de seccion.** [SECTIONS] Las seis cabeceras estandar presentes, en
mayusculas, escritas exactamente como en A6.

**B6. Ambos formatos listos para enviar.** DOCX y PDF deben pasar B1 a B3. Donde
el portal acepte ambos, preferir DOCX salvo que su renderizado rompa las vinetas;
donde solo se acepte uno, ese debe haber pasado.

**B7. Sin ligaduras ni caracteres especiales.** [CHARS] Las fuentes unen "ff",
"fi" y "ffi" en un solo caracter (U+FB00 a U+FB06). En el texto extraido eso
rompe palabras ("staﬀ") y, peor, emails ("daniel.guiloﬀ@ses.cl"). El HTML
desactiva las ligaduras (`font-variant-ligatures:none`). Detectado 2026-10-25 en
la postulacion TasWater.

**B8. Etiqueta de Skills pegada a sus terminos.** [SKILLS] Con flex o con una
columna de ancho fijo, el PDF entregaba "Analysis: Delivery: Change:" y despues
los terminos: una maquina no puede saber que termino va con que etiqueta.

**B9. Fecha junto al cargo tambien en el PDF.** [ROLES] Es la regla A7 vista
desde el texto extraido: la fecha sale en la misma linea que el cargo o en la
siguiente. Con `float:right`, un empleador largo empujaba la fecha debajo de la
linea de contexto (Utility Worker, 2026-10-25).

**B10. Emails de referees literales.** [EMAILS] Un email mal extraido es un
referee que nadie puede contactar.

## Nota sobre vinetas

El render de PDF puede enmascarar como muestran las listas otros visores. Ademas
de la inspeccion visual, descomprimir el DOCX y verificar que `word/numbering.xml`
muestra `numFmt="bullet"` en cada nivel usado. Si un visor sigue mostrando
numeros (algunas previsualizaciones web ignoran las definiciones de numbering),
el PDF es el formato autoritativo de envio.
