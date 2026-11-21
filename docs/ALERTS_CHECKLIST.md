# Alertas de empleo por correo: lista para configurar (P-3 + P-12, D-P12-1)

Todas las alertas llegan a la casilla iCloud dedicada. El sistema solo lee la carpeta **Career Buddy Alertas**,
en modo de solo lectura, y solo de los remitentes de `config/email-alerts.yaml`. Esta lista la configuras tú
(son tus cuentas). Marca cada fila cuando esté lista.

## Paso 0. La casilla (una vez)
1. **Alias solo para alertas (recomendado).** En icloud.com → Mail → Ajustes → Cuentas → *Agregar un alias*,
   por ejemplo un nombre terminado en "alertas" en el dominio de iCloud. iCloud permite hasta 3 alias gratis.
   Registra **todas** las alertas con ese alias, no con la dirección principal.
2. **Carpeta:** crea la carpeta `Career Buddy Alertas`.
3. **Una sola regla:** Ajustes → Reglas → *Si un mensaje está dirigido a* `<tu alias>` → *Mover a*
   `Career Buddy Alertas`. Con el alias basta una regla, en vez de una por portal.
4. Guarda el alias en `private/config/` (te paso el comando cuando lo tengas). Nunca va al repositorio.
5. Revisa que la cuenta tenga espacio libre: si está llena, las alertas rebotan.

## Paso 1. Las búsquedas (las mismas en SEEK y LinkedIn)
Lugar: **Tasmania** (SEEK: "All Tasmania"; LinkedIn: "Tasmania, Australia"). Frecuencia: **diaria**.
SEEK y LinkedIn aceptan `OR` y comillas en las palabras clave; si un portal no las acepta, crea una alerta por
término principal. No hace falta excluir Senior/Lead/Manager: el sistema ya los descarta.

| # | Nombre de la alerta | Palabras clave | Grupo |
|---|---|---|---|
| 1 | HCB Mejora | "continuous improvement" OR "business improvement" OR "process improvement" OR "business process" OR "operational excellence" | A |
| 2 | HCB Operaciones y activos | "operations analyst" OR "operations coordinator" OR "operations officer" OR "asset management" OR "asset planner" OR "asset officer" | A, C |
| 3 | HCB Ingeniería | "industrial engineer" OR "graduate engineer" OR "process engineer" OR "production engineer" OR "project engineer" OR "quality engineer" OR "reliability engineer" | B |
| 4 | HCB Planificación | "production planner" OR "maintenance planner" OR "maintenance scheduler" OR "work management" OR "supply chain" OR "inventory planner" OR "procurement officer" | C |
| 5 | HCB Proyectos y apoyo técnico | "project coordinator" OR "project officer" OR "engineering support" OR "technical officer" OR "quality coordinator" OR "planning officer" | C, D |

## Paso 2. Portales generales
| ✓ | Portal | Qué crear | Nota |
|---|---|---|---|
| ☐ | **SEEK** | las 5 búsquedas, guardadas con alerta diaria | el canal más importante |
| ☐ | **LinkedIn Jobs** | las 5 búsquedas, "Set alert" diaria | |
| ☐ | Indeed | búsquedas 1, 3 y 5 | opcional |
| ☐ | Work180 | alerta Tasmania, ingeniería | también publica Hydro/Entura |
| ☐ | Hays, Randstad | alerta Tasmania, Engineering / Operations | agencias |
| ☐ | Prosple, GradConnection | alerta graduados de ingeniería, Tasmania | programas de graduados |
| ☐ | councilcareers.com.au | alerta Tasmania | cubre varios concejos (Hobart, Launceston, Burnie...) |

## Paso 3. Plataformas de las empresas (alerta "Tasmania" o "Hobart/Launceston/Devonport/Burnie")
Prioridad 1 primero. Si una plataforma no tiene opción de alerta o pide más de lo razonable, anótalo: queda en
búsqueda web (`search_discovery`).

| ✓ | Prioridad | Empresa | Plataforma | Cómo |
|---|---|---|---|---|
| ☐ | 1 | **TasNetworks** | portal propio | "Job alerts" en su página de empleos |
| ☐ | 1 | TasPorts | portal propio | alerta de empleos |
| ☐ | 1 | TasWater | portal propio | alerta de empleos |
| ☐ | 1 | Hydro Tasmania + Entura | PageUp | "Job alerts" en el listado |
| ☐ | 1 | Marinus Link | Employment Hero | alerta, excluir Victoria |
| ☐ | 1 | Bell Bay Aluminium (Rio Tinto) | Workday | cuenta Workday → "Create job alert", lugar Bell Bay |
| ☐ | 1 | GHD | Oracle Cloud | alerta, lugar Hobart y Launceston |
| ☐ | 1 | Pitt & Sherry | LiveHire | "Join talent community" + alertas |
| ☐ | 1 | Aurora Energy | LiveHire | "Join talent community" + alertas |
| ☐ | 1 | Tassal | Dayforce | alerta, Tasmania |
| ☐ | 2 | WSP | LiveHire | talent community, Tasmania |
| ☐ | 2 | Aurecon | Workday | alerta, Hobart |
| ☐ | 2 | SMEC / Surbana Jurong | Workday | alerta, Tasmania |
| ☐ | 2 | Jacobs, AECOM | portal propio | alerta, Hobart |
| ☐ | 2 | BMD | PageUp | alerta, Tasmania |
| ☐ | 2 | Fulton Hogan | Workday | alerta, Tasmania |
| ☐ | 2 | Downer | Oracle Cloud | alerta, Tasmania |
| ☐ | 2 | BESIX Watpac | SmartRecruiters | alerta, Hobart (estadio Macquarie Point) |
| ☐ | 2 | Saputo (Burnie, Smithton) | Workday | alerta, Tasmania |
| ☐ | 2 | Fonterra (Wynyard) | Avature | alerta, Tasmania |
| ☐ | 2 | Mondelez (Cadbury Claremont) | portal propio | alerta, Claremont / Hobart |
| ☐ | 2 | APA (Basslink) | Workday | alerta, Tasmania |
| ☐ | 2 | Momentum Energy | PageUp | alerta, Hobart |
| ☐ | 2 | Tas Gas (Solstice Energy) | ELMO | alerta |
| ☐ | 3 | Metro Tasmania, Sustainable Timber Tasmania | ELMO | alerta |
| ☐ | 3 | Toll, Kymera (Ecka Granules) | portal propio / Dayforce | alerta, Tasmania |
| ☐ | 3 | Concejos Kingborough, Clarence, Central Coast | applynow / TechnologyOne | alerta si existe |

No hace falta alerta (el sistema ya lee su página): TSS (opcional de respaldo), Glenorchy, Devonport, Nyrstar,
Huon, TasRail, SAGE, Hazell; y el grupo P de P-12 cuando se active.

## Paso 4. Cuando lleguen los primeros correos
Avísame. Con los correos reales confirmo los remitentes de `config/email-alerts.yaml`, escribo un lector por
remitente y corro la prueba RT-16 (una alerta de cada portal convertida en ficha correcta, sin duplicados).
