# Vistas de Baserow para el seguimiento (solo vistas gratuitas)

Baserow (localhost:8080) es la fuente de verdad de las postulaciones. Las vistas solo cambian **cómo se ven**
los datos; no cambian filas. Las creas tú en la interfaz (el token del sistema solo crea y edita filas).

> Kanban y Calendario son vistas **Premium** de Baserow (de pago, también instalado en tu Mac). Estas cinco vistas
> usan solo funciones gratuitas: Grid con filtros, orden y agrupación, y Gallery. El tablero tipo Kanban de solo
> lectura viene en P-13.

En cada vista: arriba a la izquierda, el nombre de la vista actual → **Create view** (Grid o Gallery) → nombre.
Después usa **Filter**, **Sort**, **Group** y **Hide fields** en la barra de la vista.

## 1. Applications → "Pipeline" (Grid)
- **Group:** Status (los grupos salen en el orden de las opciones: Discovered, Shortlisted, Waiting Documents,
  Preparing, Ready for Review, Applied, Interview, Rejected, Withdrawn, Closed).
- **Filter:** Status *is none of* Rejected, Withdrawn, Closed.
- **Sort:** Closing Date, ascendente.
- **Hide fields:** deja visibles Job Title, Company, Location, Status, Closing Date, Alignment Group,
  Catalogue Title, Next Follow Up, Job URL. Oculta el resto (Notes, Review Reason, Opportunity Ref, Latest Version...).

## 2. Applications → "Cierran pronto" (Grid)
- **Filter (And):** Closing Date *is within* next 14 days · Status *is none of* Applied, Interview, Rejected,
  Withdrawn, Closed.
- **Sort:** Closing Date, ascendente.
- Uso: lo que tienes que decidir esta semana.

## 3. Applications → "Seguimientos" (Grid)
- **Filter (And):** Status *is any of* Applied, Interview · Next Follow Up *is on or before* today.
- **Sort:** Next Follow Up, ascendente.
- Uso: a quién escribir o llamar hoy (lo haces tú; el sistema nunca contacta a nadie).

## 4. Applications → "Fichas" (Gallery)
- **Card fields:** Job Title, Company, Status, Closing Date, Alignment Group, Location.
- **Filter:** Status *is none of* Rejected, Withdrawn, Closed.
- Uso: vista rápida tipo tarjetas; al abrir una ficha ves todos los campos y los Documents enlazados.

## 5. Contacts → "Personas" (Gallery)
- **Card fields:** nombre, cargo, empresa, canal, próximo paso (los nombres exactos de tus columnas de Contacts).
- **Sort:** empresa.

## Consejos
- Para mover una postulación de etapa, cambia **Status** en la fila (en cualquier vista); el sistema también lo
  hace cuando le dices «Enviada X» o «Cerrada X» por Telegram.
- No borres filas: cierra con Status Closed / Withdrawn (el historial se usa en el informe del sábado).
- Si quieres arrastrar tarjetas entre columnas (Kanban), es Baserow Premium. P-13 propone un tablero de solo lectura
  gratuito junto con el estado del sistema.
