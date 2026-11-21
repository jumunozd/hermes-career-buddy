# Career Development OS Master Specification

## Especificación funcional y técnica para Claude Code y Hermes Agent

**Estado:** Línea base de requisitos 1.0  
**Fecha:** 7 de noviembre de 2026  
**Destinatario:** Claude Code como constructor de la infraestructura  
**Plataforma operativa:** Hermes Agent  
**Propietario y aprobador:** Usuario director del sistema  

---

## 1 Propósito y mandato de construcción

Este documento define el comportamiento obligatorio de Career Development OS. Claude Code debe utilizarlo como contrato de construcción para producir una infraestructura que Hermes Agent pueda ejecutar, supervisar y mantener. Claude Code construye y prueba; Hermes opera. El usuario conserva la autoridad sobre postulaciones, comunicaciones externas, cambios estructurales y gastos.

Career Development OS debe apoyar dos objetivos simultáneos:

1. Ingresar al mercado profesional australiano utilizando experiencia verificable en Ingeniería Industrial, operaciones, mejora continua, gestión de activos, automatización y áreas relacionadas.
2. Priorizar oportunidades que contribuyan al plan profesional de diez años, incluso cuando la vía de entrada sea Graduate, Junior, Trainee o una función de transición.

El sistema no es una máquina de postulaciones masivas. Debe buscar ampliamente, evaluar con evidencia, preparar documentos de calidad, simular una revisión de contratación y detenerse ante cualquier acción externa que no haya sido autorizada.

### 1.1 Resultado que debe producir Claude Code

Claude Code debe entregar una implementación mínima, comprensible, versionada y comprobable que:

- reutilice el Job Application Engine, el evaluador A–H y la integración existente con Baserow cuando la inspección confirme que funcionan;
- permita que un Project Manager coordine cuatro especialistas: Job Hunter, Writer, Research Agent y Recruiter;
- ejecute el ciclo semanal descrito en esta especificación;
- conserve trazabilidad de entradas, decisiones, versiones, estados, errores y aprobaciones;
- funcione primero en el Mac del usuario y solo después de superar las pruebas pueda trasladarse al VPS;
- no dependa de Claude Code para la operación diaria una vez aceptada la implementación.

### 1.2 Lenguaje normativo

En este documento, **DEBE** indica una condición obligatoria; **NO DEBE**, una prohibición; **DEBERÍA**, una recomendación que requiere justificación si se omite; y **PUEDE**, una opción permitida. Las etiquetas **Confirmado** y **Por verificar** separan las decisiones funcionales ya aprobadas de las decisiones técnicas que Claude Code debe resolver mediante inspección y pruebas.

### 1.3 Regla contra suposiciones

Claude Code NO DEBE inventar rutas, nombres de campos, identificadores, endpoints, tokens, APIs, plugins, horarios, cuentas, versiones instaladas ni estado de servicios. Antes de escribir configuración debe inspeccionar el entorno real y documentar la evidencia. Cuando falte información, debe dejar una decisión visible en el registro de verificación y construir una interfaz o adaptador que permita completar la configuración sin rehacer la lógica de negocio.

---

## 2 Autoridades de información y precedencia

### 2.1 Fuentes oficiales del sistema

| Fuente | Autoridad confirmada | Política de uso |
|---|---|---|
| Job Application Engine | Antecedentes profesionales, logros, evidencias, metodologías de CV, cover letter, Selection Criteria y evaluación A–H | Es la única fuente autorizada para afirmar experiencia o capacidad del usuario. Debe inspeccionarse y reutilizarse. No debe reconstruirse sin necesidad ni modificarse automáticamente. |
| Baserow | Ofertas, postulaciones, contactos, documentos asociados, estados y seguimiento | Es la fuente operativa de verdad. Los agentes pueden crear y actualizar registros dentro de sus responsabilidades. Los cambios deben ser trazables. |
| Fuentes públicas verificables | Ofertas, empresas, mercado laboral y contexto sectorial | Cada afirmación externa relevante debe conservar fuente, fecha de acceso y, cuando sea posible, URL o identificador. |
| Sistema de archivos del proyecto | Documentos generados, versiones y evidencias técnicas | Los archivos deben conservarse en una estructura organizada y Baserow debe guardar sus referencias. La ruta concreta se define después de inspeccionar el entorno. |
| Telegram | Instrucciones, selecciones, aprobaciones, alertas y entrega de resultados | Es el canal de coordinación con el usuario. No sustituye la trazabilidad operativa de Baserow. |
| Gmail | Informe consolidado del sábado | El envío semanal al propio usuario es una excepción externa previamente autorizada. La cuenta emisora y el mecanismo técnico se deben verificar. |

### 2.2 Precedencia cuando las fuentes discrepan

1. Para hechos sobre la trayectoria del usuario, prevalece el Job Application Engine.
2. Para el estado operativo de una oportunidad o postulación, prevalece Baserow, sujeto a una actualización trazable respaldada por evidencia.
3. Para requisitos de una vacante, prevalece el anuncio original o una fuente oficial del empleador.
4. Para reglas de operación, prevalece esta especificación y las aprobaciones posteriores registradas del usuario.
5. Ningún agente puede resolver una contradicción inventando datos. Debe marcarla, conservar la evidencia y solicitar únicamente la aclaración necesaria.

### 2.3 Estado actual conocido

**Confirmado por la conversación:** existe un Job Application Engine; existe un evaluador A–H probado previamente con una oferta de Glenorchy City Council; existe una integración inicial entre Hermes y Baserow; Hermes se ha considerado para uso local en Mac y posterior migración a un VPS de Hostinger.

**No verificado directamente:** ubicación y estructura del Job Application Engine; contrato real del evaluador A–H; esquema, campos y permisos de Baserow; alcance y salud de la integración existente; versión instalada de Hermes; disponibilidad del VPS; plugins, perfiles, credenciales, modelos, proveedores, gateways, cron jobs y copias de seguridad. Claude Code debe tratar estos elementos como hipótesis hasta reunir evidencia.

---

## 3 Requisitos funcionales confirmados

### 3.1 Equipo y separación de responsabilidades

Career Development OS tiene cinco perfiles funcionales:

- **Project Manager:** recibe objetivos, planifica, delega, controla dependencias, consolida resultados, gestiona excepciones y aplica las puertas de aprobación.
- **Job Hunter:** descubre, verifica inicialmente, deduplica, evalúa y registra oportunidades.
- **Writer:** investiga la empresa y prepara únicamente los documentos solicitados, utilizando hechos verificados.
- **Research Agent:** analiza el mercado los viernes, propone mejoras de búsqueda y prepara investigación específica después de una entrevista confirmada.
- **Recruiter:** simula la evaluación del empleador, devuelve un veredicto con razones y guía hasta tres ciclos de mejora con Writer.

La existencia de cinco funciones no obliga a crear cinco procesos permanentes ni cinco perfiles técnicos de Hermes. Claude Code debe elegir la forma de ejecución después de verificar la versión, la delegación disponible y las necesidades de aislamiento. La identidad funcional y los contratos de cada rol sí son obligatorios.

### 3.2 Filosofía de búsqueda

El Job Hunter DEBE buscar de forma amplia y no literal. Debe distinguir:

- oportunidades de alto ajuste, relacionadas directamente con la experiencia verificable del usuario;
- oportunidades adyacentes o de transición que aprovechen habilidades transferibles;
- oportunidades exploratorias con valor estratégico para el plan de diez años.

El sistema no debe descartar automáticamente un puesto por el título. Debe evaluar responsabilidades, requisitos, contexto, habilidades transferibles y trayectoria profesional posible. No puede ignorar licencias, habilitaciones legales ni requisitos obligatorios.

### 3.3 Umbral, ranking y selección semanal

- Todas las ofertas con fit **estrictamente superior al 50 %** según la metodología A–H deben registrarse en Baserow y ordenarse de mayor a menor.
- Una oferta con fit exactamente igual al 50 % NO entra al ranking principal. Puede considerarse exploratoria si tiene valor estratégico.
- El informe debe destacar un Top 5 de oportunidades elegibles. Si existen menos de cinco ofertas que superen el umbral, el sistema no debe completar el Top 5 con ofertas que incumplan la regla.
- El informe debe incluir tres oportunidades exploratorias, separadas del ranking principal y acompañadas por una justificación breve de una línea.
- Las exploratorias deben registrarse en Baserow con la clasificación confirmada **Exploratoria** o con el valor equivalente ya existente que Claude Code mapee sin duplicarlo.
- El Top 5 es una prioridad propuesta, no una restricción. El usuario puede seleccionar cualquier oportunidad del ranking completo.

### 3.4 Fuentes de búsqueda

La selección definitiva de portales, empleadores, organismos públicos, fuentes sectoriales, términos y frecuencias depende de un Deep Research independiente del mercado laboral australiano con foco en Tasmania. El resultado de esa investigación debe ser revisado y aprobado por el usuario antes de convertirse en reglas del Job Hunter.

Hasta recibir ese insumo, Claude Code debe construir una configuración de fuentes modificable y documentada, sin inventar un inventario definitivo ni asumir que el scraping está permitido. Se deben priorizar fuentes oficiales, mecanismos autorizados, feeds, APIs o alertas cuando existan y sean verificables.

### 3.5 Duplicados y republicaciones

Antes de registrar una oferta, el Job Hunter debe consultar Baserow para evitar duplicados. Debe considerar, cuando estén disponibles, empresa, título, ubicación, identificador del anuncio, URL, fecha y contenido relevante.

- Si dos fuentes representan la misma vacante, debe mantenerse un solo registro y conservarse la procedencia adicional.
- Si una publicación reaparece y corresponde a la misma vacante, debe actualizarse el registro existente y conservar su historial.
- Si hay evidencia de un proceso de contratación nuevo, debe crearse un registro nuevo vinculado al anterior.
- Si la identidad de la vacante es incierta, el sistema no debe fusionar ni eliminar automáticamente. Debe marcar un posible duplicado para revisión.

### 3.6 Información incompleta

Cuando una oferta no contenga datos suficientes para ejecutar A–H:

1. Job Hunter intenta completar los datos mediante fuentes verificables.
2. Reintenta la evaluación.
3. Si la información continúa siendo insuficiente, registra o actualiza la oportunidad como **Pendiente de revisión**.
4. No asigna un fit injustificado ni inventa valores.

### 3.7 Mantenimiento semanal

Job Hunter se concentra en descubrir oportunidades. Project Manager coordina una revisión semanal de las ofertas registradas antes del informe del sábado. Las ofertas vencidas deben conservarse y cambiar al estado confirmado **Cerrada**. No deben eliminarse porque forman parte del historial.

Antes de iniciar la preparación de una postulación, el sistema debe volver a verificar que la oferta continúe vigente.

### 3.8 Alertas

No se deben enviar alertas normales durante la semana. Telegram se usa para alertas excepcionales cuando:

- aparece una oportunidad de ajuste extraordinariamente alto cuyo cierre no permite esperar al sábado;
- una oportunidad ya seleccionada está próxima a cerrar y sus documentos siguen en preparación;
- un error no puede resolverse de forma segura y requiere intervención del usuario.

La alerta de error debe ser breve e indicar proceso afectado, problema, intentos realizados y acción requerida. Los detalles técnicos extensos se entregan solo si el usuario los solicita.

### 3.9 Preparación de postulaciones

El comando de Telegram **Prepara las ofertas [números]** autoriza al Project Manager a iniciar la preparación de los documentos de las oportunidades seleccionadas en un informe específico. No autoriza el envío de ninguna postulación.

Writer debe:

- verificar la vigencia y los requisitos documentales de la oferta;
- investigar la empresa, su misión, valores, cultura, operaciones y contexto relevante mediante fuentes verificables;
- preparar únicamente los documentos solicitados por el anuncio;
- usar exclusivamente experiencia y evidencias autorizadas por el Job Application Engine;
- solicitar el dato faltante a Project Manager cuando una afirmación profesional necesaria no exista;
- producir DOCX editable y PDF listo para enviar cuando ambos formatos sean apropiados para la oferta; si el empleador exige otro formato, respetar el requisito;
- conservar versiones anteriores e identificar de forma inequívoca la última versión aprobada;
- guardar los archivos en la estructura organizada del proyecto y actualizar sus referencias en Baserow.

### 3.10 Revisión de Recruiter

Recruiter debe actuar como responsable de contratación de la empresa y emitir un veredicto **Pasa a entrevista** o **No pasa a entrevista**, acompañado por las razones principales. No debe asignar probabilidades artificiales ni presentar el resultado como garantía.

El ciclo admite hasta tres rondas:

1. **Ronda 1:** evaluación estricta contra los requisitos del anuncio, reconociendo habilidades transferibles respaldadas por evidencia.
2. **Ronda 2:** reevaluación estricta de los documentos mejorados con el mismo criterio.
3. **Ronda 3:** evaluación estratégica que también considera potencial de desarrollo y aprendizaje, sin ignorar requisitos obligatorios, licencias ni condiciones legales.

Recruiter entrega feedback accionable a Writer. Si el resultado sigue siendo negativo después de la tercera ronda, Project Manager entrega igualmente los documentos y las razones al usuario. No se permiten ciclos indefinidos.

Cuando el usuario solicita una modificación, Project Manager transmite el cambio a Writer, Writer modifica solo los documentos o secciones afectados, Recruiter vuelve a evaluar la nueva versión y Project Manager entrega el paquete con un resumen breve de cambios.

### 3.11 Entrega de documentos

Cada paquete de postulación debe entregarse por Telegram apenas esté terminado y haya pasado la revisión de Recruiter. No debe esperar a que terminen otras postulaciones ni a una entrega agrupada del lunes. El usuario revisará durante el fin de semana. El objetivo es que las versiones aprobadas queden listas para envío el lunes por la mañana.

Una tarea fallida no debe bloquear los trabajos terminados. Project Manager entrega los resultados completos y reporta por separado el trabajo fallido.

### 3.12 Informe del sábado

Project Manager debe enviar cada sábado por la mañana un informe consolidado a Gmail. El informe:

- tiene un máximo de tres páginas, incluido el resumen ejecutivo;
- utiliza estilo ejecutivo, sencillo y directo;
- presenta el Top 5 en orden descendente de fit;
- presenta tres oportunidades exploratorias en una sección separada con una justificación breve cada una;
- incorpora las conclusiones relevantes del Research Agent;
- resume el estado de postulaciones anteriores, seguimientos y asuntos pendientes;
- recomienda las próximas acciones y qué oportunidades conviene preparar durante el fin de semana;
- no contiene informes independientes de cada agente;
- no necesita detallar todas las ofertas superiores al 50 %, porque el ranking completo permanece en Baserow.

El mecanismo de correo, la cuenta emisora y la representación exacta de las tres páginas —cuerpo, HTML, PDF adjunto u otra forma— permanecen por verificar. Claude Code debe demostrar que la solución elegida conserva el límite y es cómoda de revisar desde Gmail.

### 3.13 Si el usuario no selecciona oportunidades

Project Manager no debe asumir aprobación. Las oportunidades permanecen pendientes y pasan al siguiente ciclo según su vigencia. Solo debe alertar si una oportunidad de ajuste extraordinariamente alto está por vencer. Los objetivos semanales son propuestas flexibles, no cuotas obligatorias.

### 3.14 Seguimiento de postulaciones

El usuario informará por Telegram respuestas, rechazos, invitaciones y otros cambios. No se requiere lectura automática de su correo personal para detectar respuestas.

Cuando una postulación lleve diez días sin respuesta, Project Manager debe recomendar un follow-up. El contacto con la empresa requiere aprobación humana.

### 3.15 Preparación de entrevistas

Cuando el usuario confirme por Telegram que obtuvo una entrevista, Project Manager activa Research Agent y Recruiter.

- Research Agent investiga empresa, operaciones, puesto, sector y contexto relevante.
- Recruiter analiza la vacante desde la perspectiva de contratación, enriquece la preparación y adapta la simulación al perfil verificado.
El sistema entrega dos documentos separados:

1. **Interview Preparation Brief:** empresa, cargo, requisitos, preguntas probables y preparación de respuestas basadas en experiencia verificada.
2. **Voice Interview Simulation:** prompt detallado para practicar una entrevista realista por voz en ChatGPT o Claude.

La investigación profunda de entrevista solo se activa después de la confirmación. Esto no limita la investigación más acotada que Writer necesita para adaptar una postulación.

### 3.16 Investigación semanal y mejora continua

Research Agent realiza cada viernes una revisión del mercado laboral de Tasmania para identificar tendencias, sectores, familias de cargos, cambios de contratación y oportunidades estratégicas. Entrega conclusiones a Project Manager para el informe del sábado. Si no hay novedades relevantes, lo indica brevemente.

Research Agent puede proponer nuevas fuentes, sectores o reglas de búsqueda. El usuario debe aprobar los cambios importantes antes de aplicarlos.

Project Manager debe recopilar resultados, feedback real de empleadores, entrevistas y observaciones de los agentes; detectar patrones; proponer aprendizajes; explicar el cambio y su fundamento; y aplicar el cambio solo después de la aprobación del usuario. Toda modificación de metodología o instrucciones debe quedar versionada para poder evaluar su efecto y revertirla.

---

## 4 Arquitectura funcional

### 4.1 Vista lógica

```text
Usuario director
  |  Telegram: objetivos, selección, aprobación, feedback y entrevistas
  v
Project Manager
  |-- Job Hunter ------> fuentes aprobadas y evaluador A-H
  |-- Writer ----------> Job Application Engine y fuentes de empresa
  |-- Research Agent --> fuentes de mercado y empresa
  |-- Recruiter -------> oferta, documentos y evidencia profesional
  |
  |-- Baserow: estado operativo, referencias y trazabilidad
  |-- Sistema de archivos: documentos y versiones
  |-- Gmail: informe consolidado del sábado
  `-- Telegram: entregas y alertas
```

### 4.2 Capas obligatorias

| Capa | Responsabilidad | Restricción |
|---|---|---|
| Interacción humana | Recibir instrucciones y aprobaciones por Telegram; entregar informe por Gmail y paquetes por Telegram | Una confirmación de preparación nunca equivale a autorización de envío. |
| Orquestación | Planificación, delegación, dependencias, prioridades, reintentos, entregas parciales y escalamiento | Project Manager puede reorganizar prioridades por cierre, fit y valor estratégico. |
| Dominio | Reglas de fit, ranking, exploración, documentos, revisión, entrevista y seguimiento | Debe implementarse de forma independiente del proveedor de modelo. |
| Integraciones | Baserow, Job Application Engine, fuentes web, Gmail y Telegram | Reutilizar conexiones existentes; no duplicar ni reemplazar sin auditoría. |
| Persistencia | Registros de Baserow, documentos versionados, historial de tareas y aprobaciones | Credenciales fuera del repositorio y de los archivos de instrucciones. |
| Observabilidad | Eventos, errores, intentos, resultados, entregas y salud | Alertas al usuario solo cuando sean accionables. |

### 4.3 Coordinación y paralelismo

Job Hunter, Research Agent y Writer pueden trabajar en paralelo cuando sus tareas sean independientes. Las dependencias deben quedar explícitas. Por ejemplo, Recruiter no evalúa una versión que Writer aún no ha publicado, y Writer no debe preparar una oferta que ya no esté vigente.

Project Manager debe impedir que un mismo encargo se ejecute dos veces. Cada ejecución necesita una identidad estable y una clave de idempotencia. Claude Code debe diseñar esas claves a partir de identificadores reales, no de rutas o campos supuestos.

---

## 5 Especificación de roles

### 5.1 Project Manager

**Misión:** convertir objetivos del usuario y eventos programados en trabajo coordinado, entregar resultados verificables y detener acciones externas no autorizadas.

**Entradas:** mensajes de Telegram; calendario semanal; registros y estados de Baserow; resultados de especialistas; fechas de cierre; errores; feedback del usuario.

**Salidas:** planes y tareas; informe del sábado; paquetes listos para revisión; alertas accionables; recomendaciones de follow-up; actualizaciones de Baserow; propuestas de mejora.

**Debe:**

- delegar según rol y controlar dependencias;
- priorizar por fecha de cierre, fit y valor estratégico sin solicitar autorización para cada cambio de orden;
- aplicar puertas de aprobación;
- entregar trabajos completos aunque otro falle;
- conservar la relación entre informe, número de oportunidad, registro de Baserow y paquete generado;
- coordinar mantenimiento semanal y seguimiento de diez días;
- evitar reportes rutinarios de progreso; informar resultados, bloqueos y acciones requeridas.

**No debe:** enviar postulaciones, contactar empleadores, alterar instrucciones, modificar código o cambiar la arquitectura sin autorización.

### 5.2 Job Hunter

**Misión:** descubrir y evaluar oportunidades que faciliten la entrada al mercado australiano y el desarrollo profesional a largo plazo.

**Entradas:** fuentes aprobadas; taxonomía de búsqueda aprobada; restricciones profesionales; Job Application Engine; evaluador A–H; registros existentes de Baserow.

**Salidas:** oportunidades verificadas; evidencia; resultado A–H; clasificación principal o exploratoria; duplicados resueltos o marcados; registros creados o actualizados.

**Debe:** buscar de lunes a viernes; deduplicar antes de escribir; conservar procedencia; manejar información incompleta; registrar todas las ofertas con fit mayor al 50 %; separar exploratorias; no ocuparse del mantenimiento posterior salvo la verificación previa a una preparación.

**No debe:** inventar datos, forzar un fit, eliminar registros históricos, presentar una exploratoria como parte del ranking principal ni asumir permisos de scraping.

### 5.3 Writer

**Misión:** producir documentos exactos, específicos para la empresa y alineados con el anuncio.

**Entradas:** oferta vigente; lista de documentos solicitados; información profesional del Job Application Engine; investigación verificable de la empresa; feedback de Recruiter y usuario.

**Salidas:** documentos solicitados; fuentes de investigación; versiones DOCX y PDF cuando correspondan; resumen de cambios; referencias de archivos actualizadas en Baserow.

**Debe:** usar hechos verificados; investigar la empresa; respetar el formato solicitado; cambiar solo las secciones afectadas; conservar versiones; identificar la versión final aprobada.

**No debe:** crear documentos no solicitados, inventar logros, inferir credenciales, modificar el Job Application Engine ni enviar la postulación.

### 5.4 Research Agent

**Misión:** mantener una lectura actualizada del mercado de Tasmania y proporcionar investigación específica para entrevistas confirmadas.

**Entradas:** fuentes aprobadas; investigación previa; tendencias; contexto de oportunidades; aviso de entrevista.

**Salidas:** resumen de mercado del viernes; propuestas de fuentes o sectores; evidencia y limitaciones; dossier de investigación para entrevista.

**Debe:** distinguir hechos, inferencias y recomendaciones; citar fuentes; declarar cuando no existan novedades; proponer cambios sin aplicarlos.

**No debe:** investigar profundamente cada oportunidad antes de que sea necesario, modificar reglas sin aprobación ni presentar hipótesis como hechos.

### 5.5 Recruiter

**Misión:** evaluar la postulación como un responsable de contratación, identificar debilidades y orientar mejoras sin distorsionar la experiencia del usuario.

**Entradas:** anuncio; criterios obligatorios y deseables; documentos de Writer; evidencia del Job Application Engine; investigación de empresa; número de ronda.

**Salidas:** veredicto binario; razones; requisitos cumplidos y no cumplidos; feedback accionable; materiales de entrevista.

**Debe:** aplicar las tres rondas definidas; reconocer habilidades transferibles verificadas; mantener criterios legales; detenerse después de tres ciclos; fundamentar el veredicto.

**No debe:** inventar experiencia, garantizar resultados, producir una probabilidad ficticia ni suavizar un requisito obligatorio para mejorar el veredicto.

---

## 6 Contratos de entrada y salida

Los nombres siguientes describen contratos lógicos. Claude Code debe mapearlos a las estructuras reales del proyecto y Baserow después de la inspección. No constituyen nombres obligatorios de tablas, campos, clases ni archivos.

### 6.1 Task Envelope

Todo trabajo delegable debe incluir como mínimo:

| Dato lógico | Propósito |
|---|---|
| Identidad de tarea | Evitar ejecuciones duplicadas y correlacionar eventos. |
| Tipo de acción | Buscar, evaluar, investigar, redactar, revisar, mantener, informar o preparar entrevista. |
| Rol responsable | Determinar instrucciones y permisos. |
| Referencias de entrada | IDs reales de Baserow, oferta, versión de informe, archivos o fuentes. |
| Dependencias | Resultados que deben existir antes de ejecutar. |
| Fecha límite | Priorizar y alertar cuando corresponda. |
| Alcance de aprobación | Qué está autorizado y qué continúa bloqueado. |
| Clave de idempotencia | Impedir la repetición de efectos ante reintentos o reinicios. |
| Estado y resultado | Permitir observación, recuperación y entrega parcial. |

### 6.2 Opportunity Record

El adaptador de Baserow debe poder representar, usando el esquema existente o una migración aprobada:

- referencia estable de la oportunidad;
- fuente y URL o identificador original cuando exista;
- empresa, cargo, ubicación y fecha de cierre según la evidencia disponible;
- fecha de descubrimiento y fecha de última verificación;
- referencia o instantánea del anuncio necesaria para reproducir la evaluación;
- resultado A–H, versión de la metodología y evidencia de entrada;
- fit total sin recalcular ni redefinir ponderaciones;
- categoría principal o exploratoria;
- estado operativo, incluyendo las semánticas confirmadas Cerrada y Pendiente de revisión;
- relación con registros anteriores cuando exista una republicación o un nuevo proceso;
- procedencia y registro de cambios.

### 6.3 A–H Evaluation Result

Claude Code debe descubrir el contrato real del evaluador. El adaptador debe conservar, como mínimo, referencia de la oferta evaluada, versión o hash de la metodología, entradas utilizadas, resultado de A a H cuando el motor lo produzca, fit total, razonamiento o evidencia, datos ausentes, fecha y estado de ejecución.

La lógica, las ponderaciones y los límites internos de A–H NO deben reimplementarse desde esta especificación. Si el motor no expone alguno de estos datos, Claude Code debe documentar la brecha y mantener la mayor trazabilidad que permita el componente real.

### 6.4 Weekly Report

El contrato del informe debe contener:

- identidad y fecha del ciclo;
- resumen ejecutivo;
- Top 5 con número estable dentro de ese informe, referencia de Baserow, fit, cierre y razón de prioridad;
- tres exploratorias con referencia y justificación de una línea;
- síntesis de mercado;
- estado de postulaciones, follow-ups y riesgos;
- acciones propuestas para el fin de semana;
- decisiones requeridas del usuario;
- evidencia de generación y entrega por Gmail.

Los números utilizados en **Prepara las ofertas [números]** deben resolverse contra una versión concreta del informe. Si el comando es ambiguo o se refiere a un informe antiguo, Project Manager debe pedir una aclaración breve y no preparar la oportunidad equivocada.

### 6.5 Preparation Request

Debe incluir la versión del informe, números seleccionados, referencias resueltas, usuario aprobador, fecha de autorización, alcance exacto —preparar, no enviar— y estado de vigencia comprobado de cada oferta.

### 6.6 Application Package

Debe incluir:

- referencia de oportunidad y de solicitud de preparación;
- lista de documentos exigidos por la oferta;
- fuentes de empresa utilizadas;
- archivos generados con versión, formato, hash o identificador equivalente y ruta real;
- veredicto y razones de Recruiter por ronda;
- feedback aplicado y resumen de cambios;
- indicador inequívoco de última versión aprobada;
- referencias actualizadas en Baserow;
- estado de aprobación humana y prohibición de envío mientras no exista autorización separada.

### 6.7 Interview Package

Debe relacionarse con la postulación y contener dos artefactos distintos: Interview Preparation Brief y Voice Interview Simulation. Ambos deben indicar fuentes, fecha, versión y límites de la información.

### 6.8 Error Event

Todo error operativo significativo debe registrar proceso, tarea, rol, hora, categoría, mensaje saneado, intentos, efecto, trabajos no afectados, estado de recuperación y acción requerida. No se deben registrar secretos ni contenido sensible innecesario.

---

## 7 Workflows obligatorios

### 7.1 Búsqueda de lunes a viernes

1. El programador inicia un ciclo del Job Hunter en la zona horaria aprobada.
2. Job Hunter consulta únicamente fuentes aprobadas y respeta sus condiciones de acceso.
3. Normaliza la oportunidad y consulta Baserow para detectar duplicados.
4. Reúne la información necesaria para A–H.
5. Si faltan datos, busca evidencia complementaria y aplica la regla de Pendiente de revisión.
6. Ejecuta el evaluador A–H existente.
7. Registra o actualiza la oportunidad con procedencia e historial.
8. Clasifica el resultado: ranking principal solo si fit > 50 %; Exploratoria si corresponde; fuera de alcance en los demás casos según la política que Claude Code documente sin contaminar el ranking.
9. Solo genera alerta si se cumple una excepción confirmada.

La frecuencia y hora exacta dentro de lunes a viernes están por verificar. No deben fijarse por intuición.

### 7.2 Revisión del viernes y mantenimiento previo al informe

1. Research Agent revisa el mercado de Tasmania y produce una síntesis con fuentes.
2. Project Manager coordina la verificación semanal de vigencia.
3. Las ofertas vencidas pasan a Cerrada sin borrarse.
4. Se verifican fechas, posibles duplicados, oportunidades urgentes y postulaciones con diez días sin respuesta.
5. Project Manager consolida resultados para el informe.

### 7.3 Informe del sábado

1. Project Manager congela una versión del ranking elegible para el ciclo.
2. Selecciona el Top 5 sin violar fit > 50 %.
3. Selecciona tres exploratorias separadas.
4. Integra investigación, seguimiento y acciones.
5. Valida extensión máxima, referencias y ausencia de datos inventados.
6. Envía el informe a la dirección Gmail autorizada y conserva evidencia de entrega.
7. Si el envío falla, registra un fallo de entrega distinto del fallo de generación y alerta por Telegram cuando no pueda recuperarlo.

### 7.4 Selección y preparación durante el fin de semana

1. El usuario envía **Prepara las ofertas [números]** por Telegram.
2. Project Manager resuelve los números contra el informe correspondiente.
3. Verifica vigencia y documentos solicitados.
4. Crea tareas independientes para cada oportunidad.
5. Writer investiga la empresa y genera la primera versión.
6. Recruiter evalúa y devuelve veredicto y razones.
7. Writer y Recruiter iteran hasta aprobar o completar tres rondas.
8. Project Manager entrega cada paquete por Telegram tan pronto esté listo.
9. El usuario aprueba o solicita cambios. Los cambios vuelven a Writer y después a Recruiter.
10. Una aprobación de documentos deja el paquete listo; no autoriza el envío a la empresa.

### 7.5 Follow-up

1. Project Manager identifica postulaciones con diez días sin respuesta a partir de Baserow.
2. Verifica que el estado y la fecha sean confiables.
3. Recomienda follow-up al usuario.
4. No contacta a la empresa sin una aprobación específica.
5. Registra la decisión y cualquier acción informada por el usuario.

### 7.6 Entrevista

1. El usuario informa por Telegram que obtuvo una entrevista.
2. Project Manager actualiza Baserow y activa Research Agent y Recruiter.
3. Research Agent prepara evidencia de empresa, cargo y sector.
4. Recruiter integra el análisis con la oferta y el perfil verificado.
5. Se generan dos documentos separados.
6. Project Manager los entrega y registra sus referencias.

### 7.7 Mejora del sistema

1. Project Manager reúne feedback y resultados observables.
2. Formula una propuesta con problema, evidencia, cambio, riesgo y criterio de éxito.
3. El usuario aprueba o rechaza.
4. Un cambio de instrucciones o metodología se versiona; un cambio de código o arquitectura se ejecuta mediante Claude Code.
5. Se prueba antes de activar y se conserva una vía de reversión.

---

## 8 Estados y transiciones

### 8.1 Principio de mapeo

Los estados siguientes son semánticas que la implementación debe representar. Claude Code debe reutilizar los valores reales de Baserow y documentar el mapeo. Solo los nombres **Exploratoria**, **Pendiente de revisión** y **Cerrada** fueron confirmados expresamente. Cualquier otro nombre es una descripción lógica, no autorización para alterar el esquema.

### 8.2 Ciclo lógico de una oportunidad

```text
Descubierta
  -> posible duplicado -> revisión
  -> información insuficiente -> Pendiente de revisión
  -> evaluada con fit > 50 -> elegible y rankeada
  -> valor estratégico fuera del ranking -> Exploratoria
  -> seleccionada por el usuario -> preparación autorizada
  -> vence o es retirada -> Cerrada
```

Una oportunidad puede ser cerrada desde cualquier estado cuando la evidencia demuestre que ya no está vigente. Cerrar no equivale a borrar.

### 8.3 Ciclo lógico de una postulación

```text
Preparación autorizada
  -> documentos en preparación
  -> revisión de Recruiter 1
  -> revisión de Recruiter 2 si requiere cambios
  -> revisión de Recruiter 3 si requiere cambios
  -> lista para revisión humana
  -> cambios solicitados o documentos aprobados
  -> lista para envío
  -> enviada solo después de autorización separada
  -> en espera de respuesta
  -> entrevista, rechazo, retirada u otro resultado informado
```

La implementación debe impedir la transición a enviada cuando solo exista autorización para preparar.

### 8.4 Estados técnicos de tareas

Claude Code debe representar tareas pendientes, en ejecución, completadas, fallidas, bloqueadas, canceladas y con resultado parcialmente entregado, o mapear esas semánticas a capacidades nativas de Hermes. Debe definir qué transiciones son reintentables y cómo se verifica un efecto incierto antes de repetir una escritura externa.

---

## 9 Permisos y puertas de aprobación

### 9.1 Matriz funcional

| Acción | Autorización |
|---|---|
| Leer fuentes públicas aprobadas | Permitida dentro de las condiciones de acceso. |
| Leer Job Application Engine | Permitida para los roles que necesiten hechos o metodología. |
| Crear y actualizar registros operativos en Baserow | Permitida dentro de la responsabilidad de cada agente, con trazabilidad. |
| Generar, revisar, versionar y almacenar documentos | Permitida después de la autorización de preparación. |
| Reorganizar prioridades por cierre, fit y valor | Permitida al Project Manager. |
| Reintentar fallos operativos seguros | Permitida, con límites y registro. |
| Enviar el informe semanal al Gmail del usuario | Preautorizada para el destinatario y propósito definidos. |
| Entregar documentos y alertas por Telegram al usuario | Preautorizada. |
| Enviar una postulación | Requiere aprobación humana específica. |
| Enviar correo o mensaje a un empleador | Requiere aprobación humana específica. |
| Contactar por LinkedIn u otra red | Requiere aprobación humana específica. |
| Realizar follow-up | Requiere aprobación humana específica. |
| Cambiar reglas de búsqueda o metodologías | Research o Project Manager proponen; el usuario aprueba. |
| Modificar código, configuración estructural, instrucciones o arquitectura | Requiere autorización del usuario y ejecución controlada, normalmente mediante Claude Code. |
| Alterar estructura de Baserow | Requiere inspección, plan de migración, copia y aprobación del usuario. |
| Instalar una integración, plugin o dependencia | Requiere justificación, revisión de seguridad y aprobación cuando cambie el entorno o los permisos. |
| Iniciar un gasto adicional o cambiar proveedor/modelo | Requiere aprobación del usuario. |

### 9.2 Alcance de una aprobación

Cada aprobación debe registrar actor, acción, objetos afectados, canal, fecha, alcance y expiración si corresponde. Una aprobación no se extiende a otras acciones por similitud. En particular:

- preparar documentos no autoriza enviarlos;
- aprobar una versión de CV no autoriza contactar a la empresa;
- autorizar el informe semanal no autoriza otros correos;
- permitir actualizaciones de Baserow no autoriza cambios de esquema;
- autorizar una reparación operativa no autoriza modificar arquitectura.

### 9.3 Secretos y datos sensibles

Las credenciales no deben almacenarse en instrucciones, repositorio, documentación, logs ni Baserow salvo que exista un mecanismo de secretos expresamente diseñado para ello. Claude Code debe usar los mecanismos admitidos por la instalación real de Hermes, aplicar privilegio mínimo y entregar plantillas sin valores secretos.

---

## 10 Manejo de errores y continuidad

### 10.1 Clasificación

| Clase | Ejemplos | Respuesta requerida |
|---|---|---|
| Transitorio | Red, timeout, rate limit recuperable, servicio momentáneamente no disponible | Reintentar con límites; no duplicar efectos; continuar trabajos independientes. |
| Datos incompletos | Oferta sin requisitos suficientes, fecha dudosa, fuente contradictoria | Buscar evidencia; marcar Pendiente de revisión; no inventar. |
| Duplicado o efecto incierto | Escritura posiblemente aplicada antes de perder conexión | Leer el estado real antes de repetir; usar idempotencia; escalar si no puede probarse. |
| Entrega fallida | Informe generado pero Gmail no confirma entrega; archivo listo pero Telegram falla | Mantener el artefacto, registrar la entrega por separado y reintentar de forma segura. |
| Autorización ausente | Solicitud de envío, contacto, cambio estructural o gasto sin aprobación | Bloquear la acción y solicitar aprobación. |
| Estructural | Código, configuración, esquema o arquitectura requiere modificación | Detener la reparación automática, informar y solicitar autorización para Claude Code. |
| Irrecuperable | Intentos seguros agotados o componente crítico no disponible | Entregar resultados no afectados y alertar por Telegram con acción requerida. |

### 10.2 Política de recuperación

Hermes debe intentar resolver problemas operativos seguros mediante documentación y diagnósticos disponibles. La conversación mencionó informalmente un posible nombre parecido a “DocHermes”, pero ese nombre NO está confirmado y no debe convertirse en dependencia. Claude Code debe utilizar solo capacidades verificadas de la versión instalada.

Los reintentos deben tener límite, espera progresiva cuando corresponda y verificación de efectos. No se debe repetir ciegamente una acción de escritura. El sistema debe conservar evidencia de cada intento.

### 10.3 Entrega parcial

Cada postulación constituye una unidad de trabajo independiente. Si cuatro paquetes terminan y uno falla, se entregan los cuatro. El informe de error del quinto no debe impedir ni retrasar los demás.

### 10.4 Observabilidad

La implementación debe permitir responder, sin leer razonamiento privado del modelo:

- qué tarea se inició y por qué;
- qué entradas y versiones usó;
- qué rol y herramientas actuaron;
- qué registros o archivos se crearon o cambiaron;
- qué aprobación habilitó la acción;
- qué resultado y veredicto se produjeron;
- qué errores e intentos ocurrieron;
- si Gmail o Telegram confirmaron la entrega.

No se requieren reportes rutinarios de progreso al usuario. Los logs y estados internos deben ser suficientes para diagnóstico y auditoría.

---

## 11 Línea base técnica de Hermes y verificaciones obligatorias

### 11.1 Documentación oficial comprobada

Al 7 de noviembre de 2026, el repositorio oficial de Nous Research publica **Hermes Agent v0.23.0**, con fecha de lanzamiento 5 de noviembre de 2026. Esta es la versión estable más reciente observada durante la preparación del documento. No demuestra la versión instalada del usuario.

La documentación oficial vigente confirma:

- los perfiles son hogares persistentes separados con configuración, identidad, memoria, sesiones, habilidades, cron y estado propios;
- un perfil no es un sandbox y `SOUL.md` no impone por sí solo límites de sistema de archivos;
- `SOUL.md` define identidad; el contexto del proyecto se carga desde un único archivo según la precedencia documentada, donde `.hermes.md` tiene prioridad sobre `AGENTS.md`, que a su vez precede a `CLAUDE.md`;
- `delegate_task` crea subagentes con conversación nueva; el trabajo en segundo plano de un subagente no es durable si el proceso termina;
- cron es el mecanismo durable para tareas programadas y permite fijar zona horaria por trabajo;
- MCP está incluido en la instalación estándar y puede exponer solo un subconjunto de herramientas;
- Telegram admite conversación, archivos y resultados programados;
- Hermes ofrece mecanismos de email mediante IMAP/SMTP y otras opciones de integración, pero la solución adecuada para este proyecto debe evaluarse;
- el plugin oficial `advanced-delegation` agrega rutas por modelo o por perfil y requiere Hermes 0.22.5 o posterior.

### 11.2 Consecuencias para el diseño

Claude Code debe tratar lo siguiente como recomendaciones sujetas a verificación, no como configuración aprobada:

1. Usar un Project Manager como identidad operativa principal y delegar especialistas mediante el mecanismo más simple que preserve instrucciones, herramientas y trazabilidad.
2. Evaluar `profile_routes` solo si la versión instalada, el plugin oficial y las pruebas justifican perfiles persistentes por especialista. La delegación predeterminada puede ser suficiente para la primera versión.
3. Usar cron para los ciclos de lunes a viernes, viernes y sábado; no confiar en subagentes en segundo plano para trabajo que deba sobrevivir reinicios.
4. Fijar explícitamente `Australia/Hobart` en la programación después de confirmar que coincide con la intención del usuario. Las horas exactas siguen pendientes.
5. Elegir un solo archivo de contexto de proyecto para Hermes y evitar reglas duplicadas o contradictorias entre `.hermes.md`, `AGENTS.md` y `CLAUDE.md`.
6. Configurar un directorio de trabajo explícito y controles reales de acceso. Un perfil separado no constituye aislamiento.
7. Exponer a cada rol solo las herramientas necesarias. Las integraciones con escritura deben aplicar puertas de aprobación y controles de idempotencia.
8. No desactivar las protecciones de comandos. Las aprobaciones de Hermes para comandos peligrosos complementan, pero no sustituyen, las aprobaciones de negocio de esta especificación.

### 11.3 Inventario que Claude Code debe producir antes de construir

Claude Code debe generar un informe de solo lectura que incluya:

- sistema operativo y arquitectura del Mac;
- forma de instalación y versión real de Hermes;
- canal de actualización y commit o etiqueta cuando esté disponible;
- perfiles existentes y su propósito, sin exponer secretos;
- gateways, Telegram, email, cron, plugins, MCPs y habilidades disponibles;
- modelos y proveedores configurados, sin copiar tokens;
- Job Application Engine: ubicación proporcionada por el usuario, estructura, comandos, contratos, pruebas y estado del repositorio;
- evaluador A–H: punto de entrada, entradas, salidas, versión y prueba reproducible;
- Baserow: conexión existente, tablas, campos, relaciones, estados, permisos, volumen y trazabilidad;
- integración Hermes–Baserow existente: mecanismo, herramientas expuestas, operaciones, errores y pruebas;
- estructura actual de documentos y backups;
- estado real del VPS y restricciones de Hostinger;
- diferencias entre Mac y VPS que afecten rutas, permisos, servicios, zona horaria o persistencia.

La inspección no autoriza cambios. Cualquier comando que pueda modificar estado debe esperar al plan aprobado.

### 11.4 Registro de decisiones técnicas por verificar

| ID | Punto | Evidencia necesaria | Decisión posterior |
|---|---|---|---|
| TV-01 | Versión instalada de Hermes | Salida de versión y método de instalación | Compatibilidad y estrategia de actualización. |
| TV-02 | Arquitectura de agentes | Prueba de delegación predeterminada y, si aplica, perfiles | Subagentes con instrucciones o perfiles persistentes. |
| TV-03 | Plugin advanced-delegation | Versión, catálogo, instalación y prueba | Usarlo o mantener delegación predeterminada. |
| TV-04 | Job Application Engine | Auditoría de estructura y comandos | Adaptador y límites de escritura. |
| TV-05 | Evaluador A–H | Prueba reproducible y contrato real | Llamada, validación y almacenamiento. |
| TV-06 | Baserow | Esquema e integración reales | Mapeo de campos; migraciones solo si son necesarias y aprobadas. |
| TV-07 | Gmail | Cuenta emisora, destinatario, mecanismo y prueba | Gateway email, skill, conector u otro método verificado de menor privilegio. |
| TV-08 | Telegram | Bot, usuario autorizado, adjuntos y gateway | Canal de coordinación y entrega. |
| TV-09 | Horarios | Preferencia del usuario y zona del sistema | Cron exacto de lunes a viernes, viernes y sábado. |
| TV-10 | Formato del informe | Prueba en Gmail y límite de tres páginas | Cuerpo, HTML, PDF u otra representación. |
| TV-11 | Modelos y Codex | Compatibilidad de la instalación y configuración del usuario | El usuario conectará Hermes con Codex después de construir la estructura. |
| TV-12 | Mac y VPS | Entorno, persistencia, servicios y backups | Plan de despliegue y recuperación. |
| TV-13 | Fuente Deep Research | Informe aprobado por el usuario | Inventario definitivo de fuentes y taxonomía. |
| TV-14 | Costos y límites | Proveedores y presupuesto aprobados | Presupuestos, cuotas y alertas. |

### 11.5 Prohibiciones técnicas

Claude Code NO DEBE:

- actualizar Hermes, instalar plugins o modificar perfiles antes del inventario y el plan;
- usar nombres o configuraciones de versiones antiguas sin contrastarlos con la versión instalada;
- asumir que `AGENTS.md` y `CLAUDE.md` se cargan simultáneamente en Hermes;
- asumir que un perfil limita el acceso al sistema de archivos;
- colocar secretos en `config.yaml`, instrucciones, repositorio o ejemplos completos;
- reemplazar la integración Baserow o el evaluador A–H sin demostrar que no son reutilizables;
- habilitar todo el conjunto de herramientas de un MCP cuando baste un subconjunto;
- confiar en reintentos del programador como garantía de exactamente una escritura;
- configurar scraping, cuentas de correo o automatizaciones externas sin verificar términos, permisos y credenciales;
- conectar modelos o proveedores por anticipado. La conexión con Codex queda para una fase guiada posterior.

---

## 12 Entregables de Claude Code

### 12.1 Paquete de descubrimiento

1. **Informe de inventario:** evidencia del entorno actual y brechas.
2. **Mapa del Job Application Engine:** componentes reutilizables, contrato A–H y pruebas.
3. **Inventario de Baserow:** tablas, campos, relaciones, estados y permisos, sin cambios.
4. **Matriz de compatibilidad Hermes:** versión instalada frente a capacidades requeridas.
5. **Registro TV actualizado:** cada punto marcado como verificado, bloqueado o pendiente de decisión.

### 12.2 Paquete de diseño

1. **Diagrama de arquitectura y decisiones:** componentes, flujos, fronteras de confianza y alternativas descartadas.
2. **Matriz de trazabilidad:** requisito de esta especificación a archivo, módulo y prueba.
3. **Contratos de dominio:** oportunidades, tareas, evaluaciones, documentos, aprobaciones, entregas y errores.
4. **Máquina de estados y mapeo Baserow:** semánticas, valores reales y transiciones permitidas.
5. **Modelo de permisos:** herramientas y acciones por rol, incluyendo puertas de aprobación.
6. **Plan de migración:** cualquier cambio requerido en Baserow o archivos, con copia y reversión.

### 12.3 Paquete de implementación

Claude Code debe proponer la estructura concreta después de la inspección. Como mínimo, el repositorio resultante debe contener, con nombres adaptados a las convenciones reales:

- un archivo de contexto de proyecto elegido para Hermes y compatible con Claude Code;
- instrucciones versionadas para Project Manager, Job Hunter, Writer, Research Agent y Recruiter;
- contratos y validadores de entradas y salidas;
- adaptadores para Job Application Engine, A–H, Baserow, Telegram, Gmail y sistema de archivos;
- orquestación de workflows e idempotencia;
- definiciones de programación desactivadas o en modo prueba hasta su aprobación;
- configuración de ejemplo sin secretos;
- tests unitarios, de integración, de contrato, de seguridad y end-to-end;
- fixtures anonimizados o sintéticos que no inventen datos para una postulación real;
- scripts o comandos de diagnóstico y verificación;
- runbook de operación, aprobación, errores, backup, restauración y actualización;
- documentación de despliegue local y posterior despliegue al VPS;
- changelog y mecanismo de versionado de instrucciones.

### 12.4 Artefactos de rol

Si la arquitectura utiliza perfiles Hermes, Claude Code debe crear o actualizar cada `SOUL.md` solo después de confirmar el hogar de perfil correcto. Si utiliza subagentes sin perfiles persistentes, debe conservar las mismas instrucciones como contratos de rol inyectados en cada delegación. Las instrucciones compartidas deben vivir en el contexto del proyecto, no copiarse de forma divergente en cinco archivos.

### 12.5 Documentación de operación

El runbook debe explicar en lenguaje práctico:

- cómo iniciar, detener, pausar y comprobar el sistema;
- cómo ejecutar manualmente cada workflow en modo seguro;
- cómo aprobar o rechazar una acción;
- cómo localizar un informe, una oferta, una versión y un error;
- cómo recuperar una ejecución interrumpida sin duplicar escrituras;
- cómo rotar credenciales sin exponerlas;
- cómo restaurar configuración, documentos y datos;
- cómo trasladar la versión aceptada del Mac al VPS;
- cómo volver a una versión anterior.

---

## 13 Plan de pruebas

### 13.1 Principios

Las pruebas deben usar un entorno controlado. No deben enviar postulaciones, contactar empleadores, modificar el esquema productivo de Baserow ni utilizar datos profesionales inventados como si fueran reales. Los envíos de prueba a Gmail o Telegram deben dirigirse solo a cuentas del usuario y quedar claramente marcados.

### 13.2 Pruebas unitarias de reglas

| ID | Escenario | Resultado esperado |
|---|---|---|
| UT-01 | Fit 50.01 % | Elegible para ranking principal. |
| UT-02 | Fit 50.00 % | Excluida del ranking principal; puede evaluarse como exploratoria. |
| UT-03 | Menos de cinco ofertas elegibles | No se rellena el Top 5 con ofertas que incumplan el umbral. |
| UT-04 | Tres exploratorias | Permanecen separadas y cada una tiene justificación de una línea. |
| UT-05 | Misma vacante en dos fuentes | Un registro con procedencia múltiple. |
| UT-06 | Republicación de la misma vacante | Se actualiza el historial existente. |
| UT-07 | Nuevo proceso verificable | Nuevo registro vinculado al anterior. |
| UT-08 | Información insuficiente | Se intenta completar; luego Pendiente de revisión, sin fit inventado. |
| UT-09 | Oferta vencida | Cambia a Cerrada y no se elimina. |
| UT-10 | Comando de preparación | Autoriza documentos, no envío. |
| UT-11 | Oferta pide solo CV | Writer no genera cover letter ni otros documentos. |
| UT-12 | Hecho profesional ausente | Writer bloquea la afirmación y solicita verificación. |
| UT-13 | Tres rondas negativas | Se detiene y entrega paquete con razones. |
| UT-14 | Requisito legal ausente | Ronda 3 no lo ignora por potencial de desarrollo. |
| UT-15 | Diez días sin respuesta | Se recomienda follow-up; no se envía. |
| UT-16 | Falta de selección del usuario | Se conserva pendiente; no se asume aprobación. |
| UT-17 | Cambio solicitado por el usuario | Writer modifica lo afectado y Recruiter reevalúa. |
| UT-18 | Feedback de mercado | Se propone un cambio; no se aplica sin aprobación. |

### 13.3 Pruebas de contrato

- El adaptador A–H acepta las entradas reales y valida su salida sin cambiar la metodología.
- El adaptador Baserow lee y escribe únicamente campos mapeados y conserva IDs reales.
- Las referencias de archivos guardadas en Baserow resuelven a la versión correcta.
- El parser de Telegram resuelve los números contra la versión correcta del informe.
- El envío Gmail conserva destinatario, asunto, contenido, límite de extensión y confirmación.
- La entrega Telegram conserva documentos, nombres, versiones y correlación.
- Las herramientas de escritura rechazan acciones sin el permiso o la aprobación requeridos.

### 13.4 Pruebas de integración por etapas

**Etapa 1 Project Manager y Job Hunter**

- ejecutar una búsqueda limitada en fuentes aprobadas;
- evaluar una oferta mediante A–H;
- detectar un duplicado;
- escribir y leer el registro de Baserow;
- generar un ranking sin comunicación externa.

**Etapa 2 Project Manager Writer y Recruiter**

- preparar una oportunidad de prueba controlada;
- generar solo los documentos solicitados;
- ejecutar feedback y hasta tres rondas;
- versionar archivos y referencias;
- bloquear el envío.

**Etapa 3 Research Agent**

- producir una síntesis con fuentes y límites;
- proponer una mejora sin aplicarla;
- preparar el insumo de una entrevista simulada.

**Etapa 4 Ciclo integral local**

- ejecutar búsqueda, mantenimiento, informe, selección, preparación, revisión, entrega y seguimiento;
- probar aprobaciones, reintentos y una falla parcial;
- demostrar trazabilidad de principio a fin.

**Etapa 5 VPS**

- desplegar la misma versión aceptada;
- confirmar persistencia, zona horaria, servicios, gateways, secretos y backups;
- ejecutar una prueba integral sin depender del Mac;
- restaurar una copia de prueba y verificar integridad.

### 13.5 Pruebas de fallos

La suite debe inyectar al menos:

- caída temporal de Baserow;
- timeout o fallo de autenticación de una fuente;
- resultado A–H inválido;
- pérdida de conexión después de una escritura potencial;
- fallo de Gmail después de generar el informe;
- fallo de Telegram durante la entrega de un archivo;
- Writer fallando mientras otras postulaciones terminan;
- reinicio durante una tarea programada;
- ausencia de una aprobación requerida;
- solicitud de modificación de código durante una reparación.

Cada prueba debe demostrar que no se duplican efectos, no se pierden resultados completos y no se ejecutan acciones externas sin permiso.

### 13.6 Pruebas de seguridad

- búsqueda automática de secretos en repositorio, logs y artefactos;
- verificación de permisos mínimos por rol e integración;
- rechazo de destinatarios no autorizados;
- bloqueo de cambios estructurales no aprobados;
- validación de archivos y contenido externo no confiable;
- prueba de que instrucciones de una oferta o página web no pueden modificar las reglas del sistema;
- revisión de dependencias y plugins antes de instalarlos;
- prueba de backup y restauración sin credenciales en el repositorio.

---

## 14 Criterios de aceptación

La versión inicial se considera aceptada solo cuando todos los criterios aplicables estén respaldados por evidencia reproducible.

### 14.1 Funcionalidad

- [ ] Los cinco roles tienen instrucciones, entradas, salidas, permisos y límites verificables.
- [ ] Job Hunter registra todas las ofertas con fit > 50 % y no incluye fit = 50 % en el ranking principal.
- [ ] El Top 5 y las tres exploratorias se generan y permanecen separados.
- [ ] La deduplicación, republicación y nuevo proceso producen el comportamiento definido.
- [ ] La información incompleta termina en Pendiente de revisión sin puntaje inventado.
- [ ] La revisión semanal conserva vencidas como Cerrada.
- [ ] El informe del sábado llega al Gmail autorizado, tiene máximo tres páginas y contiene las secciones requeridas.
- [ ] **Prepara las ofertas [números]** prepara las oportunidades correctas y no autoriza envío.
- [ ] Writer genera solo lo solicitado, con hechos del Job Application Engine y versiones rastreables.
- [ ] Recruiter aplica hasta tres rondas y entrega veredicto con razones.
- [ ] Los paquetes terminados llegan por Telegram apenas están listos.
- [ ] Una falla no bloquea otros resultados.
- [ ] El sistema recomienda follow-up a los diez días y bloquea el contacto no aprobado.
- [ ] Una entrevista confirmada produce dos documentos separados.
- [ ] Las mejoras se proponen y versionan, pero no se aplican sin aprobación.

### 14.2 Integridad y seguridad

- [ ] Ningún hecho profesional usado en documentos carece de respaldo en el Job Application Engine.
- [ ] Baserow contiene procedencia, historial y referencias válidas.
- [ ] Las credenciales están fuera del repositorio, instrucciones, logs y documentos.
- [ ] Enviar postulaciones, contactar empresas, cambiar arquitectura y generar gastos está bloqueado sin aprobación.
- [ ] Reintentos y recuperaciones no duplican registros, archivos ni mensajes.
- [ ] Los logs permiten reconstruir cada acción sin exponer secretos ni razonamiento privado.

### 14.3 Operación y despliegue

- [ ] La versión instalada de Hermes y sus capacidades se documentaron.
- [ ] La arquitectura de delegación fue probada, no asumida.
- [ ] Los trabajos programados usan la zona horaria confirmada y sobreviven reinicios según las capacidades verificadas.
- [ ] El sistema local pasa la prueba integral antes del despliegue al VPS.
- [ ] El VPS pasa la misma prueba sin depender del Mac.
- [ ] Existe backup comprobado de instrucciones, configuración no secreta, documentos y datos operativos.
- [ ] Existe un procedimiento de restauración y reversión probado.
- [ ] El usuario puede pausar la automatización y ejecutar un workflow manualmente.

### 14.4 Evidencia de aceptación

Claude Code debe entregar un informe final con:

- versión y commit de la implementación;
- entorno y versión de Hermes probados;
- lista de pruebas, fecha, resultado y evidencia;
- criterios de aceptación cumplidos y pendientes;
- excepciones aprobadas;
- riesgos residuales;
- instrucciones exactas para la siguiente acción del usuario.

Crear archivos o mostrar una demostración parcial no equivale a aceptación.

---

## 15 Secuencia de implementación

### Fase 0 Descubrimiento sin cambios

Producir inventarios, probar solo lectura y completar el registro TV. Detenerse si no puede identificar de forma segura el entorno correcto.

### Fase 1 Diseño y simulación

Definir contratos, mapeos, permisos, estados y fixtures. Simular workflows sin escrituras productivas ni comunicaciones externas.

### Fase 2 Mínimo vertical local

Construir Project Manager más Job Hunter, conectar A–H y Baserow en un alcance controlado y demostrar trazabilidad.

### Fase 3 Preparación de postulaciones

Incorporar Writer y Recruiter, versionado de documentos y puertas de aprobación.

### Fase 4 Investigación comunicaciones y ciclo semanal

Incorporar Research Agent, Telegram, Gmail, mantenimiento, seguimiento y cron. Mantener trabajos programados en modo prueba hasta la aprobación.

### Fase 5 Validación local

Ejecutar pruebas de fallos, seguridad, ciclo integral, backup y restauración en el Mac.

### Fase 6 Migración al VPS

Comparar entornos, desplegar la misma versión aceptada, configurar persistencia y servicios, restaurar datos necesarios y repetir la aceptación.

### Fase 7 Conexión de modelos y operación

El usuario conectará Hermes con Codex mediante un procedimiento guiado posterior. Claude Code debe mantener la implementación independiente del proveedor y documentar los puntos de configuración, sin introducir credenciales ni decisiones de gasto.

---

## 16 Instrucción de ejecución para Claude Code

Claude Code debe comenzar respondiendo a esta especificación con tres entregables breves antes de modificar el entorno:

1. Un resumen de los requisitos que considera obligatorios y de las acciones prohibidas.
2. Un plan de descubrimiento de solo lectura, indicando qué evidencia reunirá y dónde registrará los resultados.
3. Una lista de decisiones técnicas que no puede resolver sin inspección o aprobación, usando los IDs TV de este documento.

Después debe ejecutar la Fase 0. No debe instalar, actualizar, migrar, crear perfiles, editar Baserow ni cambiar la configuración de Hermes durante esa fase. Con el inventario completo, debe proponer la arquitectura mínima, explicar cómo reutiliza los componentes existentes y mostrar la matriz de trazabilidad antes de construir.

Cuando una decisión técnica tenga varias opciones válidas, Claude Code debe presentar la diferencia en términos de seguridad, mantenimiento, compatibilidad y esfuerzo. No debe convertir una recomendación técnica en una decisión confirmada del usuario.

---

## 17 Trazabilidad de decisiones confirmadas

| ID | Decisión | Implementación o prueba asociada |
|---|---|---|
| BR-01 | Claude Code construye y Hermes ejecuta | Inventario, arquitectura y prueba independiente de Claude Code. |
| BR-02 | Project Manager más cuatro especialistas | Instrucciones y contratos de cinco roles. |
| BR-03 | Ciclo lunes a viernes, viernes, sábado y fin de semana | Cron o mecanismo durable verificado. |
| BR-04 | Registro de todas las ofertas con fit > 50 % | UT-01, UT-02 e integración Baserow. |
| BR-05 | Top 5 y tres exploratorias separadas | UT-03 y UT-04. |
| BR-06 | Evaluador A–H existente | TV-05 y prueba de contrato. |
| BR-07 | Baserow como fuente operativa | TV-06 e integración. |
| BR-08 | Job Application Engine como fuente profesional | TV-04 y validación de afirmaciones. |
| BR-09 | Gmail para informe del sábado | TV-07, TV-10 y prueba de entrega. |
| BR-10 | Telegram para coordinación y entregas | TV-08 y pruebas de comando, alerta y archivo. |
| BR-11 | Revisiones de Recruiter hasta tres rondas | UT-13 y flujo Writer–Recruiter. |
| BR-12 | Dos documentos para entrevista | Prueba end-to-end de entrevista. |
| BR-13 | Baserow editable por agentes dentro de su responsabilidad | Matriz de permisos y logs. |
| BR-14 | Acciones externas requieren aprobación | Pruebas negativas de seguridad. |
| BR-15 | Cambios estructurales requieren autorización y Claude Code | Puerta de cambio y runbook. |
| BR-16 | Entregas independientes ante fallos | Prueba de falla parcial. |
| BR-17 | Versiones de documentos y referencias en Baserow | Prueba de Application Package. |
| BR-18 | Mac primero y VPS después | Etapas 4 y 5 de integración. |
| BR-19 | Propuestas flexibles, no cuotas | Informe semanal y ausencia de autoaprobación. |
| BR-20 | Mejora continua con aprobación | Workflow de propuesta, versionado y reversión. |

---

## 18 Fuentes oficiales de Hermes consultadas

Las siguientes fuentes se verificaron el 7 de noviembre de 2026. Claude Code debe volver a contrastarlas con la versión realmente instalada antes de aplicar configuraciones:

1. [Repositorio oficial de Hermes Agent](https://github.com/NousResearch/hermes-agent)
2. [Releases oficiales de Hermes Agent](https://github.com/NousResearch/hermes-agent/releases)
3. [Perfiles y múltiples agentes](https://hermes-agent.nousresearch.com/docs/user-guide/profiles)
4. [Qué función cumple cada archivo](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/which-file-does-what.md)
5. [Tareas programadas con cron](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron)
6. [Configuración de Hermes Agent](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)
7. [Model Context Protocol en Hermes](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp/)
8. [Telegram en Hermes](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram)
9. [Email en Hermes](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/messaging/email.md)
10. [Plugin oficial Advanced Delegation](https://github.com/NousResearch/hermes-official-plugins/blob/main/advanced-delegation/README.md)

---

## 19 Definición de terminado

Career Development OS está listo para operación inicial cuando la implementación local cumple los criterios de aceptación, las integraciones reales han sido probadas, las acciones externas permanecen bajo control humano, las tareas programadas sobreviven las condiciones operativas previstas, los backups pueden restaurarse y el usuario puede comprender, pausar y supervisar el sistema. La migración al VPS se considera terminada solo después de repetir la prueba integral allí.

Hasta entonces, el sistema debe considerarse en construcción o validación, aunque todos los archivos de agentes ya existan.
