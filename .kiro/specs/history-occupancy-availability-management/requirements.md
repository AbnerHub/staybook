# Requirements Document

## Introduction

Este documento define los requerimientos para el módulo de administración de historial, ocupación y disponibilidad del sistema StayBook. Es un módulo **de solo lectura / consulta** (read/query) que expone capacidades para que el Administrador consulte el estado actual del hotel y su historial, reutilizando exclusivamente el modelo de datos y las reglas de negocio ya existentes (Room, Guest, Reservation y el ciclo de vida de check-in/check-out).

El Administrador podrá:
- consultar la ocupación actual del hotel;
- consultar las habitaciones actualmente ocupadas;
- consultar la disponibilidad de habitaciones para un rango de fechas solicitado;
- consultar el historial de reservas / estancias;
- filtrar el historial por campos existentes útiles (huésped, habitación, estado de reserva y rango de fechas) cuando corresponda.

Este spec es la última funcionalidad del MVP y **no introduce nuevas fuentes de verdad ni copias históricas**: el historial ya se preserva mediante el ciclo de vida existente de las reservas (las reservas no se eliminan; `cancelled` y `checked_out` permanecen en la base de datos).

Queda **fuera del alcance** de este spec: pagos, facturación, facturas, housekeeping, tableros de analítica, notificaciones, frontend, Docker, CI/CD, AWS y Terraform. Tampoco se crean nuevas operaciones de escritura sobre reservas, habitaciones o huéspedes.

## Hallazgos sobre el código existente (base para estos requerimientos)

Estos requerimientos se basan en la inspección del modelo de datos real de StayBook:

- **`RoomStatus`** (`app/models/room.py`): valores `disponible`, `ocupada`, `mantenimiento`.
- **`ReservationStatus`** (`app/models/reservation.py`): valores `confirmed`, `checked_in`, `checked_out`, `cancelled`.
- **`Reservation`** posee `guest_id` (FK a `guests.id`), `room_id` (FK a `rooms.id`), `check_in_date` (Date), `check_out_date` (Date), `status`, `total_price`, `created_at`, `updated_at`. Las reservas se conservan de forma permanente (no hay borrado físico), por lo que el historial ya existe en la tabla `reservations`.
- **Regla de solapamiento existente** (`ReservationRepository.get_active_overlapping`): intervalo semiabierto `[check_in_date, check_out_date)`, con reservas activas = `confirmed` + `checked_in`, excluyendo `cancelled` y `checked_out`.
- **Ocupación operativa existente**: al hacer check-in la habitación pasa a `ocupada`; al hacer check-out pasa a `disponible` (módulo Check-in/Check-out).

Conclusión de diseño preliminar (a confirmar en design): **no se requiere una nueva tabla**. Todas las consultas de este spec se derivan de las tablas existentes `rooms`, `guests` y `reservations`.

## Glossary

- **Sistema_De_Consultas**: Módulo de StayBook responsable de las consultas de historial, ocupación y disponibilidad.
- **API_De_Consultas**: Capa de presentación REST que recibe solicitudes HTTP de consulta y devuelve respuestas HTTP.
- **Servicio_De_Consultas**: Capa de lógica de negocio que aplica las reglas de consulta reutilizando los repositorios existentes.
- **Administrador**: Usuario con Rol_Administrador. Único actor contemplado en el MVP.
- **Ocupación_Actual**: Estado presente del hotel derivado del estado operativo de las habitaciones y/o del ciclo de vida de las reservas, sin introducir una segunda fuente de verdad.
- **Habitación_Ocupada**: Habitación cuyo estado operativo es `ocupada` (equivalente a tener una reserva en estado `checked_in`).
- **Disponibilidad_Por_Rango**: Determinación de qué habitaciones pueden reservarse para un rango de fechas solicitado, según la regla de solapamiento existente.
- **Reserva_Activa_Para_Disponibilidad**: Reserva que bloquea disponibilidad; incluye estados `confirmed` y `checked_in`, y excluye `cancelled` y `checked_out`.
- **Rango_De_Fechas**: Par (fecha_desde, fecha_hasta) interpretado como intervalo semiabierto `[fecha_desde, fecha_hasta)`.
- **Historial_De_Reservas**: Conjunto de reservas registradas (de cualquier estado) conservadas en la tabla `reservations`.
- **Fecha_Local_Del_Hotel**: Fecha actual en la zona horaria local del hotel, usada para determinar la ocupación "actual".
- **Token_JWT**: Token de autenticación JWT usado para verificar la identidad del usuario.
- **Rol_Administrador**: Rol que otorga permisos para las operaciones de este módulo.
- **Dependencia_De_Autenticación**: Mecanismo de autenticación basado en dependencias de FastAPI (`get_current_admin_user`) ya existente, reutilizado por este módulo.

## Requirements

### Requerimiento 1: Consulta de ocupación actual del hotel

**Historia de Usuario:** Como Administrador, quiero consultar la ocupación actual del hotel, para conocer de un vistazo cuántas habitaciones están ocupadas y cuántas disponibles.

#### Criterios de Aceptación

1. WHEN el Administrador solicita la ocupación actual, THE Servicio_De_Consultas SHALL derivar la Ocupación_Actual a partir del estado existente de las habitaciones y del ciclo de vida de las reservas, sin introducir una segunda fuente de verdad ni una tabla nueva.
2. WHEN se solicita la ocupación actual, THE API_De_Consultas SHALL retornar un resumen que incluya al menos: número total de habitaciones, número de habitaciones ocupadas, número de habitaciones disponibles y una tasa de ocupación (habitaciones ocupadas / total de habitaciones).
3. IF no existen habitaciones registradas en el sistema, THEN THE API_De_Consultas SHALL retornar un resumen con total 0 y tasa de ocupación 0 (sin división por cero) con código HTTP 200.
4. THE API_De_Consultas SHALL retornar código HTTP 200 junto con el resumen de ocupación en formato JSON.
5. THE Servicio_De_Consultas SHALL contar como "ocupada" cada habitación cuyo estado operativo sea `ocupada`; el resumen SHALL ser consistente con las habitaciones que tienen una reserva en estado `checked_in`.

### Requerimiento 2: Consulta de habitaciones actualmente ocupadas

**Historia de Usuario:** Como Administrador, quiero listar las habitaciones actualmente ocupadas, para saber qué cuartos están en uso en este momento.

#### Criterios de Aceptación

1. WHEN el Administrador solicita las habitaciones ocupadas, THE Servicio_De_Consultas SHALL retornar únicamente las habitaciones cuyo estado operativo sea `ocupada`.
2. THE API_De_Consultas SHALL incluir por cada habitación ocupada al menos sus atributos identificatorios (id, room_number, room_type) y su estado operativo.
3. IF no existe ninguna habitación ocupada, THEN THE API_De_Consultas SHALL retornar una lista vacía con código HTTP 200.
4. THE API_De_Consultas SHALL retornar código HTTP 200 junto con la lista en formato JSON.
5. THE Servicio_De_Consultas SHALL derivar el resultado del estado existente de las habitaciones/reservas, sin crear ni mantener una estructura de datos adicional.

### Requerimiento 3: Consulta de disponibilidad por rango de fechas

**Historia de Usuario:** Como Administrador, quiero consultar qué habitaciones están disponibles para un rango de fechas, para poder ubicar futuras reservas.

#### Criterios de Aceptación

1. WHEN el Administrador solicita disponibilidad indicando una fecha de inicio y una fecha de fin, THE Servicio_De_Consultas SHALL retornar las habitaciones que no tienen ninguna Reserva_Activa_Para_Disponibilidad que se solape con el Rango_De_Fechas solicitado.
2. THE Servicio_De_Consultas SHALL evaluar el solapamiento usando el intervalo semiabierto `[check_in_date, check_out_date)` existente, de modo que una habitación cuya reserva termina exactamente en la fecha de inicio solicitada (o que inicia exactamente en la fecha de fin solicitada) SHALL considerarse disponible.
3. THE Servicio_De_Consultas SHALL considerar como activas para bloquear disponibilidad únicamente las reservas en estado `confirmed` o `checked_in`, y SHALL excluir las reservas en estado `cancelled` o `checked_out`.
4. IF la fecha de fin es anterior o igual a la fecha de inicio, THEN THE API_De_Consultas SHALL retornar un error de validación con código HTTP 422 indicando que la fecha de fin debe ser posterior a la fecha de inicio.
5. IF falta alguno de los parámetros de fecha requeridos o su formato es inválido, THEN THE API_De_Consultas SHALL retornar un error de validación con código HTTP 422.
6. IF ninguna habitación está disponible para el rango solicitado, THEN THE API_De_Consultas SHALL retornar una lista vacía con código HTTP 200.
7. THE Servicio_De_Consultas SHALL reutilizar la semántica de solapamiento existente del módulo de reservas en lugar de implementar una regla de solapamiento nueva o divergente.
8. THE API_De_Consultas SHALL retornar código HTTP 200 junto con la lista de habitaciones disponibles en formato JSON.

### Requerimiento 4: Consulta del historial de reservas / estancias

**Historia de Usuario:** Como Administrador, quiero consultar el historial de reservas, para revisar reservas y estancias pasadas y presentes.

#### Criterios de Aceptación

1. WHEN el Administrador solicita el historial de reservas sin filtros, THE Servicio_De_Consultas SHALL retornar las reservas registradas en la tabla `reservations`, incluyendo reservas de todos los estados (`confirmed`, `checked_in`, `checked_out`, `cancelled`).
2. THE Sistema_De_Consultas SHALL derivar el historial exclusivamente de las reservas existentes preservadas por el ciclo de vida, sin crear una copia histórica separada de las reservas.
3. THE API_De_Consultas SHALL incluir por cada reserva los atributos existentes: id, guest_id, room_id, check_in_date, check_out_date, status, total_price, created_at y updated_at.
4. IF no existen reservas que cumplan la consulta, THEN THE API_De_Consultas SHALL retornar una lista vacía con código HTTP 200.
5. THE API_De_Consultas SHALL retornar código HTTP 200 junto con el historial en formato JSON.

### Requerimiento 5: Filtrado del historial de reservas

**Historia de Usuario:** Como Administrador, quiero filtrar el historial por huésped, habitación, estado y rango de fechas, para encontrar rápidamente las reservas relevantes.

#### Criterios de Aceptación

1. WHEN el Administrador filtra el historial por `guest_id`, THE Servicio_De_Consultas SHALL retornar únicamente las reservas asociadas a ese huésped.
2. WHEN el Administrador filtra el historial por `room_id`, THE Servicio_De_Consultas SHALL retornar únicamente las reservas asociadas a esa habitación.
3. WHEN el Administrador filtra el historial por `status`, THE Servicio_De_Consultas SHALL retornar únicamente las reservas cuyo estado coincida con el valor solicitado; IF el valor de estado no pertenece a `ReservationStatus`, THEN THE API_De_Consultas SHALL retornar un error de validación con código HTTP 422.
4. WHEN el Administrador filtra el historial por un rango de fechas, THE Servicio_De_Consultas SHALL retornar las reservas cuyo periodo `[check_in_date, check_out_date)` intersecta el rango solicitado, aplicando una semántica de intersección consistente con la regla semiabierta existente.
5. WHEN el Administrador combina varios filtros, THE Servicio_De_Consultas SHALL aplicarlos de forma conjuntiva (AND), retornando solo las reservas que cumplen todos los filtros indicados.
6. IF el Administrador filtra por un `guest_id` o `room_id` inexistente, THEN THE API_De_Consultas SHALL retornar una lista vacía con código HTTP 200 (no un error), dado que la ausencia de coincidencias es un resultado válido.
7. IF un parámetro de filtro tiene formato inválido (por ejemplo un id no entero o una fecha malformada), THEN THE API_De_Consultas SHALL retornar un error de validación con código HTTP 422.
8. WHEN se aplica un filtro por rango de fechas, IF la fecha de fin es anterior o igual a la fecha de inicio, THEN THE API_De_Consultas SHALL retornar un error de validación con código HTTP 422.

### Requerimiento 6: Preservación de datos y ausencia de nuevas fuentes de verdad

**Historia de Usuario:** Como desarrollador, quiero que este módulo sea estrictamente de lectura y no duplique datos, para mantener una única fuente de verdad y evitar inconsistencias.

#### Criterios de Aceptación

1. THE Sistema_De_Consultas SHALL ser de solo lectura: no SHALL crear, actualizar, eliminar ni cambiar el estado de habitaciones, huéspedes ni reservas.
2. THE Sistema_De_Consultas SHALL derivar todas sus respuestas de las tablas existentes (`rooms`, `guests`, `reservations`), sin introducir una copia histórica ni una segunda fuente de verdad.
3. THE Sistema_De_Consultas SHALL NOT introducir nuevas tablas de base de datos a menos que un requerimiento demuestre que es genuinamente necesario; para el alcance definido, ninguna consulta requiere una tabla nueva.
4. THE Sistema_De_Consultas SHALL reutilizar los modelos y repositorios existentes de Room, Guest y Reservation donde sea apropiado, evitando duplicar lógica de acceso a datos o de negocio.
5. THE Sistema_De_Consultas SHALL derivar la Ocupación_Actual del estado operativo/ciclo de vida existente, sin mantener un contador o marca de ocupación independiente.

### Requerimiento 7: Separación de responsabilidades por capas

**Historia de Usuario:** Como desarrollador, quiero que el módulo respete la arquitectura por capas existente, para mantener el código organizado y consistente con el resto del proyecto.

#### Criterios de Aceptación

1. THE API_De_Consultas SHALL únicamente recibir solicitudes HTTP, validar los parámetros de consulta mediante esquemas/validaciones y delegar al Servicio_De_Consultas, sin acceder directamente a la base de datos.
2. THE Servicio_De_Consultas SHALL contener la lógica de consulta y agregación, comunicándose con los repositorios para el acceso a datos, sin manejar conceptos HTTP.
3. THE acceso a datos SHALL realizarse a través de repositorios (reutilizando los existentes y, si fuese necesario, añadiendo métodos de consulta de solo lectura), sin implementar reglas de negocio en la capa de acceso a datos.
4. THE Sistema_De_Consultas SHALL respetar la dirección de dependencia estricta API → Service → Repository → Model, sin dependencias inversas ni circulares.
5. THE Sistema_De_Consultas SHALL reutilizar la configuración de base de datos y de sesión existente sin rediseñarla.

### Requerimiento 8: Comportamiento HTTP y formato de respuesta

**Historia de Usuario:** Como Administrador, quiero respuestas HTTP predecibles y consistentes con el resto de la API, para integrar y depurar las consultas fácilmente.

#### Criterios de Aceptación

1. THE API_De_Consultas SHALL exponer los endpoints de consulta como operaciones HTTP GET, dado que son de solo lectura.
2. THE API_De_Consultas SHALL aceptar los criterios de disponibilidad y de filtrado del historial como parámetros de query string.
3. THE API_De_Consultas SHALL retornar código HTTP 200 para consultas exitosas, incluyendo el caso de resultados vacíos (lista vacía o resumen con ceros).
4. IF los parámetros de consulta son inválidos (tipo o formato incorrecto, o rango de fechas inválido), THEN THE API_De_Consultas SHALL retornar código HTTP 422.
5. IF ocurre un error no controlado o de conexión con la base de datos, THEN THE API_De_Consultas SHALL retornar código HTTP 500 con un mensaje genérico sin exponer detalles de infraestructura, reutilizando el manejo de errores existente (`AppException` + handlers globales) sin definir un esquema de error nuevo.
6. THE API_De_Consultas SHALL generar documentación OpenAPI/Swagger automáticamente mediante FastAPI, consistente con los módulos existentes.

### Requerimiento 9: Autenticación y autorización

**Historia de Usuario:** Como Administrador, quiero que las consultas de historial, ocupación y disponibilidad estén protegidas, para que solo usuarios autorizados accedan a la información del hotel.

#### Criterios de Aceptación

1. THE API_De_Consultas SHALL proteger todos sus endpoints reutilizando la Dependencia_De_Autenticación existente (`get_current_admin_user`), sin introducir un nuevo middleware de autenticación.
2. IF una solicitud no incluye un Token_JWT o el token es inválido (expirado, malformado o con firma incorrecta), THEN THE API_De_Consultas SHALL retornar código HTTP 401, con el mismo comportamiento que los módulos existentes.
3. IF el usuario autenticado no posee el Rol_Administrador, THEN THE API_De_Consultas SHALL retornar código HTTP 403, con el mismo comportamiento que los módulos existentes.
4. WHEN un usuario con Token_JWT válido y Rol_Administrador realiza una consulta, THE API_De_Consultas SHALL permitir que la solicitud continúe y devuelva los datos solicitados.

### Requerimiento 10: Consistencia de la semántica de ocupación y disponibilidad

**Historia de Usuario:** Como Administrador, quiero que "ocupación actual" y "disponibilidad por rango" sean coherentes con las reglas ya aprobadas, para confiar en que las consultas reflejan la realidad operativa.

#### Criterios de Aceptación

1. THE Servicio_De_Consultas SHALL distinguir claramente entre dos conceptos: la Ocupación_Actual (estado presente, basado en habitaciones `ocupada` / reservas `checked_in`) y la Disponibilidad_Por_Rango (proyección futura basada en reservas `confirmed` + `checked_in` que se solapan con el rango).
2. THE Servicio_De_Consultas SHALL determinar la disponibilidad por rangos de fechas a partir de las fechas y el estado de las reservas, y NO únicamente a partir del estado operativo actual de la habitación.
3. THE Servicio_De_Consultas SHALL excluir de forma consistente las reservas `cancelled` y `checked_out` al calcular la Disponibilidad_Por_Rango, alineado con las reglas de solapamiento aprobadas.
4. WHEN se consulta la Ocupación_Actual, THE Servicio_De_Consultas SHALL usar la Fecha_Local_Del_Hotel a partir de una fuente de fecha consistente y determinista (verificable en pruebas) cuando la noción de "actual" dependa de la fecha.
5. THE Servicio_De_Consultas SHALL tratar una habitación con estado `mantenimiento` como no disponible para reservar en la Disponibilidad_Por_Rango; la definición precisa de cómo se refleja `mantenimiento` en cada consulta SHALL detallarse en el diseño, sin introducir estados de habitación nuevos.
