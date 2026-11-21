---
asset: cv-layout-geometry
provenance: extraido programaticamente (pdfplumber, pdffonts, pdfinfo) del export de Canva "Black_and_White_Professional_Corporate_Resume.pdf" (A4, 2 paginas)
consumidor: el script que construye el DOCX. NUNCA se carga al redactar.
---

# Geometria y tipografia del CV

Este archivo lo lee el pipeline de construccion, no el modelo que escribe. Antes
vivia dentro del template y se pagaba en tokens en cada generacion sin aportar
nada al texto.

## Colores

| Token | Hex | RGB | Uso |
|---|---|---|---|
| `navy` | `#163853` | 22, 56, 83 | Banda de cabecera, banda de pie, titulos de seccion |
| `grey-band` | `#D9D9D9` | 217, 217, 217 | Franja de contacto bajo la cabecera |
| `body-text` | `#313131` | 49, 49, 49 | Todo el texto de cuerpo |
| `contact-text` | `#1E1E1E` | 30, 30, 30 | Texto de la franja de contacto |
| `white` | `#FFFFFF` | 255, 255, 255 | Texto sobre bandas navy |
| `rule` | `#000000` | 0, 0, 0 | Filete bajo los titulos de seccion |

## Tipografia

El original de Canva usa Garet (Book/Bold), Be Vietnam Medium y Arial Nova, que no
estan disponibles de forma fiable para LibreOffice headless. Los sustitutos son
visualmente cercanos e instalables.

| Elemento | Fuente original | Tamano (pt) | Color | Sustituto |
|---|---|---|---|---|
| Nombre (cabecera y pie) | Garet Book, tracking amplio | ~35 | white | Montserrat Light o Poppins Light, tracking aprox. 6 a 8 pt |
| Linea de titulo | Garet Bold, con tracking | ~17.5 (cabecera) / 15 (pie) | white | Montserrat SemiBold o Poppins SemiBold, tracking aprox. 3 a 4 pt |
| Linea de capacidades | Arial Nova Regular | 12 | white | Lato o Liberation Sans |
| Franja de contacto | Arial Nova Regular | ~10.5 | `contact-text` | Lato o Liberation Sans |
| Titulos de seccion | Be Vietnam Medium, MAYUSCULAS | 13 | `navy` | Be Vietnam Pro Medium (Google Fonts) |
| Texto de cuerpo | Arial Nova Regular | 10.3 a 10.6 | `body-text` | Lato o Liberation Sans |
| Negritas (titulares, titulos de rol) | Arial Nova Bold | igual que cuerpo | `body-text` | peso Bold correspondiente |
| Linea de contexto bajo el titulo de rol | Arial Nova Italic | igual que cuerpo | `body-text` | Italic correspondiente |

## Espaciado y geometria (A4, 595.5 x 842.25 pt)

- Margen izquierdo: 30 pt. Ancho de contenido: aprox. 535 pt.
- Interlineado de cuerpo: 14 pt (aprox. 1.35 x el tamano de fuente).
- Pagina 1, banda navy de cabecera: a sangre, desde el borde superior hasta
  y = 109 pt (aprox. 38 mm de alto).
- Franja gris de contacto: a sangre, y = 108 a 151 pt (aprox. 43 pt de alto),
  texto centrado, dos lineas.
- Bloque de titulo de seccion: titulo en navy, luego un filete negro de 0.5 a
  0.75 pt aprox. 24 pt bajo la linea base del titulo, a todo el ancho de
  contenido. Aprox. 14 pt de espacio tras el filete antes del cuerpo.
- Espacio entre secciones: aprox. 28 a 34 pt.
- Espacio entre roles en Experience: aprox. 14 pt (una linea en blanco).
- Vinetas: punto redondo pequeno, sangria francesa; vineta en x = 32 pt aprox.,
  texto en x = 42 a 44 pt aprox., las lineas envueltas alinean con la sangria.
- Pagina 2: **sin banda de cabecera**. El cuerpo empieza en el margen superior
  (aprox. 30 pt). Banda navy de pie: a sangre, de y = 731 pt al borde inferior
  (aprox. 111 pt de alto), con nombre y titulo alineados a la derecha, aprox.
  24 pt desde el margen derecho.

## Notas de implementacion (Node.js `docx` + LibreOffice)

- Bandas navy y gris: celdas de tabla a todo el ancho o sombreado de seccion con
  los hex exactos. Verificar que los bordes de banda llegan a sangre en el PDF.
- Tracking del nombre: `characterSpacing` en twips sobre el run (aprox. 120 a 160
  twips; ajustar visualmente contra el render original).
- Titulo de seccion mas filete: parrafo de titulo (Be Vietnam Pro Medium 13 pt,
  navy, mayusculas) seguido de un parrafo con borde inferior (borde negro simple
  de 4 octavos de punto) a todo el ancho de contenido.
- Vinetas: config `numbering` con `LevelFormat.BULLET`, nunca caracteres
  literales. Verificar que `word/numbering.xml` muestra `numFmt="bullet"` para
  cada nivel usado.
- Parrafos separados, nunca `\n`. Fechas alineadas a la derecha con tab stops.
  Helper para vinetas con titular (run en negrita mas run normal).
- Las fuentes deben estar instaladas en el contenedor antes de convertir con
  LibreOffice (Be Vietnam Pro y Montserrat desde Google Fonts; Lato suele estar).
  Ejecutar `fc-list` para confirmar: un fallback silencioso a Liberation Serif
  destroza el layout y puede empujar contenido a una tercera pagina.
- Bandas de cabecera y franja de contacto: implementar como **parrafos de cuerpo
  con sombreado** (o tabla de una celda sin bordes en el cuerpo), nunca dentro
  del objeto header de Word. Ver regla A1 en `build/ats-checks.md`. La pagina 2
  no lleva banda porque estos parrafos existen una sola vez al inicio del cuerpo.
  La banda decorativa de pie de la pagina 2 si puede vivir en un footer real de
  Word (different-first-page), porque no contiene contenido parseable unico.
- Conversion a PDF: `soffice --headless --convert-to pdf`.
- Render a imagenes con `pdftoppm` e **inspeccion visual de cada pagina** antes de
  entregar: layout intacto, sin titulos huerfanos, numero de paginas correcto.
