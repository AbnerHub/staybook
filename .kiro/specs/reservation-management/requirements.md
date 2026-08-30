# Requirements Document

## Introduction

Este documento define los requerimientos para el módulo de administración de reservas del sistema StayBook. El módulo permite al Administrador crear, consultar, listar, actualizar y cancelar reservas que asocian un huésped existente con una habitación existente durante un rango de fechas. Las reservas se conservan de forma permanente con fines históricos; la cancelación cambia el estado de la reserva pero nunca la elimina.

Este spec reutiliza los módulos ya implementados de habitaciones (Room Management) y huéspedes (Guest Management) para validar la existencia de la habitación y del huésped, y para calcular el precio total a partir del precio por noche configurado en la habitación.

Queda **fuera del alcance** de este spec: las operaciones de check-in y check-out, la modificación del estado de ocupación de la habitación (`status` de Room), los pagos en línea y cualquier funcionalidad móvil. El check-in/check-out y la actualización real de la ocupación de la habitación pertenecerán a un spec futuro independiente.

## Glossary

- **Sistema_De_Reservas**: Módulo del sistema StayBook responsable de la administración de reservas del hotel.
- **API_De_Reservas**: Capa de presentación REST que recibe solicitudes HTTP y devuelve respuestas HTTP relacionadas con reservas.
- **Servicio_De_Reservas**: Capa de lógica de negocio que aplica reglas y validaciones sobre las operaciones de reservas.
- **Repositorio_De_Reservas**: Capa de acceso a datos que ejecuta operaciones sobre la tabla de reservas en PostgreSQL.
- **Reserva**: Entidad que representa la asignación de una Habitación a un Huésped durante un rango de fechas determinado.
- **Administrador**: Usuario del sistema con Rol_Administrador que administra las reservas. Es el único actor contemplado en el MVP de StayBook.
- **Huésped**: Entidad existente (módulo Guest Management) que representa a la persona a la que se asocia la reserva.
- **Habitación**: Entidad existente (módulo Room Management) que representa el cuarto físico que se reserva.
- **Fecha_De_Entrada**: Fecha a partir de la cual comienza la reserva de la habitación (check_in_date).
- **Fecha_De_Salida**: Fecha en la que finaliza la reserva de la habitación (check_out_date).
- **Rango_De_Reserva**: Intervalo de fechas de la reserva, tratado como semiabierto `[Fecha_De_Entrada, Fecha_De_Salida)`.
- **Estado_De_Reserva**: Valor que indica si una reserva está "confirmed" o "cancelled".
- **Reserva_Activa**: Reserva cuyo Estado_De_Reserva es "confirmed" (no cancelada).
- **Solapamiento**: Situación en la que dos Rangos_De_Reserva de la misma Habitación se intersectan considerando el intervalo como semiabierto `[entrada, salida)`.
- **Número_De_Noches**: Cantidad de noches de la reserva, calculada como la diferencia en días entre Fecha_De_Salida y Fecha_De_Entrada.
- **Precio_Total**: Monto total de la reserva, calculado por el sistema como Número_De_Noches multiplicado por el precio por noche configurado en la Habitación.
- **Token_JWT**: Token de autenticación en formato JSON Web Token utilizado para verificar la identidad del usuario.
- **Rol_Administrador**: Rol del sistema que otorga permisos para realizar operaciones de gestión de reservas.
- **Dependencia_De_Autenticación**: Mecanismo de autenticación y autorización basado en dependencias de FastAPI (por ejemplo `get_current_admin_user`) ya existente en StayBook y reutilizado por este módulo para proteger los endpoints.
- **Registro_De_Operaciones**: Sistema de logging que registra las operaciones realizadas sobre las reservas con fines de auditoría.

## Entity Definition

### Reserva (Reservation)

Entidad principal del módulo que representa la asignación de una habitación a un huésped durante un rango de fechas.

| Atributo | Tipo de Dato | Obligatorio | Restricciones | Descripción |
|----------|-------------|-------------|---------------|-------------|
| id | integer | Sí (auto-generado) | Clave primaria, auto-incremental | Identificador único interno de la reserva |
| guest_id | integer | Sí | Debe referenciar un Huésped existente (clave foránea a guests.id) | Identificador del huésped asociado a la reserva |
| room_id | integer | Sí | Debe referenciar una Habitación existente (clave foránea a rooms.id) | Identificador de la habitación reservada |
| check_in_date | date | Sí | Fecha válida; menor que check_out_date | Fecha de inicio de la reserva |
| check_out_date | date | Sí | Fecha válida; estrictamente mayor que check_in_date | Fecha de fin de la reserva |
| status | enum | Sí | Valores permitidos: "confirmed", "cancelled". Valor por defecto: "confirmed" | Estado actual de la reserva |
| total_price | decimal | Sí (auto-calculado) | Calculado por el sistema; no proporcionado por el cliente | Precio total de la reserva = noches × precio por noche de la habitación |
| created_at | datetime | Sí (auto-gestionado) | Se asigna automáticamente al crear el registro | Fecha y hora de creación del registro |
| updated_at | datetime | Sí (auto-gestionado) | Se actualiza automáticamente en cada modificación | Fecha y hora de la última actualización del registro |

**Notas:**
- Los campos `id`, `total_price`, `created_at` y `updated_at` son gestionados automáticamente por el sistema y no son proporcionados por el usuario. En particular, `total_price` es un campo gestionado exclusivamente por el servidor: si el cliente lo envía explícitamente en la creación o actualización, la solicitud se rechaza con HTTP 422 (no se ignora silenciosamente).
- El campo `status` se inicializa con el valor "confirmed" al momento de la creación.
- El Rango_De_Reserva se interpreta como semiabierto `[check_in_date, check_out_date)`: un huésped puede salir (check_out) el mismo día en que otra reserva de la misma habitación inicia (check_in), y esto NO se considera Solapamiento.
- Las reservas se conservan de forma permanente para fines históricos; la cancelación cambia el `status` a "cancelled" pero no elimina el registro.
- Este spec no modifica el estado de ocupación (`status`) de la Habitación; esa responsabilidad pertenece al futuro módulo de check-in/check-out.

## Requirements

### Requerimiento 1: Creación de reservas

**Historia de Usuario:** Como Administrador, quiero crear una reserva para un huésped existente y una habitación existente, para asignar una habitación durante un rango de fechas determinado.

#### Criterios de Aceptación

1. WHEN el Administrador envía una solicitud de creación con un guest_id existente, un room_id existente, una Fecha_De_Entrada y una Fecha_De_Salida válidas (con check_out_date estrictamente posterior a check_in_date) y sin Solapamiento con Reservas_Activas de la misma Habitación, THE Servicio_De_Reservas SHALL crear una nueva Reserva con Estado_De_Reserva "confirmed" y persistirla en la base de datos.
2. WHEN el Servicio_De_Reservas crea una Reserva, THE Servicio_De_Reservas SHALL calcular el Precio_Total como Número_De_Noches (diferencia en días entre Fecha_De_Salida y Fecha_De_Entrada) multiplicado por el precio por noche configurado en la Habitación, sin aceptar un precio total proporcionado por el cliente.
3. THE total_price SHALL ser un campo gestionado exclusivamente por el servidor y no aceptado desde el cliente. IF el Administrador incluye explícitamente un total_price en la solicitud de creación, THEN THE API_De_Reservas SHALL rechazar la solicitud con un código HTTP 422 indicando que total_price no es un campo permitido en la entrada, en lugar de ignorar el valor silenciosamente. THE Servicio_De_Reservas SHALL seguir siendo el único responsable de calcular el Precio_Total a partir del Número_De_Noches resultante y el precio por noche configurado en la Habitación.
4. IF el Administrador envía una solicitud de creación con campos obligatorios faltantes (guest_id, room_id, check_in_date, check_out_date) o con valores de formato inválido, THEN THE API_De_Reservas SHALL retornar un error de validación con código HTTP 422 y una descripción de cada campo faltante o inválido.
5. WHEN la creación de la Reserva se completa exitosamente, THE API_De_Reservas SHALL retornar un código HTTP 201 y los datos de la Reserva creada incluyendo: id, guest_id, room_id, check_in_date, check_out_date, status, total_price, created_at y updated_at.

### Requerimiento 2: Validación de existencia de huésped y habitación

**Historia de Usuario:** Como Administrador, quiero que el sistema valide que el huésped y la habitación existen antes de crear o actualizar una reserva, para evitar reservas inconsistentes que referencien entidades inexistentes.

#### Criterios de Aceptación

1. IF el Administrador intenta crear o actualizar una Reserva con un guest_id que no corresponde a ningún Huésped existente, THEN THE Servicio_De_Reservas SHALL rechazar la operación y THE API_De_Reservas SHALL retornar un error con código HTTP 404 indicando que el huésped no fue encontrado.
2. IF el Administrador intenta crear o actualizar una Reserva con un room_id que no corresponde a ninguna Habitación existente, THEN THE Servicio_De_Reservas SHALL rechazar la operación y THE API_De_Reservas SHALL retornar un error con código HTTP 404 indicando que la habitación no fue encontrada.
3. THE Servicio_De_Reservas SHALL reutilizar los módulos existentes de Huéspedes y Habitaciones para verificar la existencia del guest_id y del room_id, sin duplicar la lógica de acceso a datos de esas entidades.

### Requerimiento 3: Validación de fechas

**Historia de Usuario:** Como Administrador, quiero que el sistema valide que la fecha de salida sea posterior a la fecha de entrada, para evitar reservas con rangos de fechas inválidos.

#### Criterios de Aceptación

1. IF el Administrador envía una solicitud de creación o actualización donde la Fecha_De_Salida es anterior o igual a la Fecha_De_Entrada, THEN THE Servicio_De_Reservas SHALL rechazar la operación y THE API_De_Reservas SHALL retornar un error con código HTTP 422 indicando que la fecha de salida debe ser posterior a la fecha de entrada.
2. THE Servicio_De_Reservas SHALL calcular el Número_De_Noches como el número de días completos entre la Fecha_De_Entrada y la Fecha_De_Salida, garantizando que sea siempre mayor o igual a 1 para toda Reserva válida.

### Requerimiento 4: Prevención de solapamiento de reservas

**Historia de Usuario:** Como Administrador, quiero que el sistema impida que una misma habitación tenga dos reservas activas cuyas fechas se solapen, para evitar la doble asignación de una habitación.

#### Criterios de Aceptación

1. THE Servicio_De_Reservas SHALL tratar el Rango_De_Reserva como el intervalo semiabierto `[check_in_date, check_out_date)` para todas las comprobaciones de Solapamiento.
2. IF el Administrador intenta crear una Reserva cuyo Rango_De_Reserva se solapa con el de una Reserva_Activa existente para la misma Habitación, THEN THE Servicio_De_Reservas SHALL rechazar la operación y THE API_De_Reservas SHALL retornar un error con código HTTP 409 indicando que la habitación ya está reservada en el rango de fechas solicitado.
3. WHEN una Reserva existente para una Habitación finaliza (check_out_date) exactamente en la misma fecha en que otra Reserva para la misma Habitación comienza (check_in_date), THE Servicio_De_Reservas SHALL considerar que NO existe Solapamiento y permitir la operación.
4. WHILE una Reserva tiene Estado_De_Reserva "cancelled", THE Servicio_De_Reservas SHALL excluirla de las comprobaciones de Solapamiento, de modo que su rango de fechas quede disponible para nuevas reservas de la misma Habitación.
5. WHEN el Administrador actualiza las fechas o la habitación de una Reserva existente, THE Servicio_De_Reservas SHALL verificar el Solapamiento contra las demás Reservas_Activas de la Habitación resultante, excluyendo la propia Reserva que se está actualizando de la comprobación.

### Requerimiento 5: Listado de reservas

**Historia de Usuario:** Como Administrador, quiero listar las reservas registradas, para tener visibilidad de las asignaciones de habitaciones del hotel.

#### Criterios de Aceptación

1. WHEN el Administrador solicita el listado de reservas, THE Sistema_De_Reservas SHALL retornar todas las reservas registradas con sus atributos completos (id, guest_id, room_id, check_in_date, check_out_date, status, total_price, created_at y updated_at), incluyendo tanto las reservas "confirmed" como las "cancelled".
2. IF no existen reservas registradas en el sistema, THEN THE API_De_Reservas SHALL retornar una lista vacía con código HTTP 200.
3. THE API_De_Reservas SHALL retornar un código HTTP 200 junto con la lista de reservas en formato JSON.

### Requerimiento 6: Obtener información de una reserva específica

**Historia de Usuario:** Como Administrador, quiero obtener la información detallada de una reserva específica, para consultar sus atributos actuales.

#### Criterios de Aceptación

1. WHEN el Administrador solicita la información de una Reserva existente por su identificador único (id), THE Sistema_De_Reservas SHALL retornar los atributos de la Reserva: id, guest_id, room_id, check_in_date, check_out_date, status, total_price, created_at y updated_at.
2. IF el Administrador solicita la información de una reserva cuyo identificador no existe en la base de datos, THEN THE API_De_Reservas SHALL retornar un error con código HTTP 404 y un mensaje indicando que la reserva no fue encontrada.
3. WHEN la consulta de una Reserva es exitosa, THE API_De_Reservas SHALL retornar un código HTTP 200 junto con los atributos completos de la Reserva en formato JSON.
4. IF el Administrador envía un identificador con formato inválido (no entero positivo), THEN THE API_De_Reservas SHALL retornar un error de validación con código HTTP 422 indicando que el identificador debe ser un número entero positivo.

### Requerimiento 7: Actualización de información de reservas

**Historia de Usuario:** Como Administrador, quiero actualizar la información permitida de una reserva existente, para reflejar cambios en las fechas o en la habitación asignada.

#### Criterios de Aceptación

1. WHEN el Administrador envía una solicitud de actualización con datos válidos para una Reserva existente con Estado_De_Reserva "confirmed", THE Servicio_De_Reservas SHALL modificar únicamente los atributos permitidos incluidos en la solicitud (room_id, check_in_date, check_out_date), preservar los atributos no incluidos sin cambios y persistir los cambios en la base de datos.
2. THE Servicio_De_Reservas SHALL permitir la actualización únicamente de los atributos room_id, check_in_date y check_out_date, y SHALL rechazar cualquier intento de modificar directamente id, guest_id, status, created_at o updated_at a través de la operación de actualización.
3. THE total_price SHALL permanecer como un campo gestionado exclusivamente por el servidor durante la actualización. IF el Administrador incluye explícitamente un total_price en la solicitud de actualización, THEN THE API_De_Reservas SHALL rechazar la solicitud con un código HTTP 422 indicando que total_price no es un campo permitido en la entrada, en lugar de ignorar el valor silenciosamente.
4. WHEN el Administrador envía una actualización parcial que incluye solo algunos de los atributos room_id, check_in_date o check_out_date, THE Servicio_De_Reservas SHALL construir el estado resultante de la Reserva combinando los valores existentes de la Reserva con los cambios proporcionados, y SHALL ejecutar todas las validaciones de negocio (validación de fechas del Requerimiento 3, detección de Solapamiento del Requerimiento 4 y recálculo del Precio_Total) sobre ese estado resultante.
5. WHEN el Servicio_De_Reservas evalúa el Solapamiento durante una actualización, THE Servicio_De_Reservas SHALL verificar el estado resultante contra las demás Reservas_Activas de la Habitación resultante, excluyendo siempre la propia Reserva que se está actualizando de esa comprobación.
6. WHEN el estado resultante de la actualización afecta room_id, check_in_date o check_out_date, THE Servicio_De_Reservas SHALL recalcular el Precio_Total con base en el Número_De_Noches resultante y el precio por noche de la Habitación resultante.
7. IF el Administrador intenta actualizar una reserva que no existe, THEN THE API_De_Reservas SHALL retornar un error con código HTTP 404 indicando que la reserva no fue encontrada.
8. IF el estado resultante de la actualización viola las reglas de validación de fechas (Requerimiento 3), de existencia de entidades (Requerimiento 2) o de Solapamiento (Requerimiento 4), THEN THE Servicio_De_Reservas SHALL rechazar la operación y THE API_De_Reservas SHALL retornar el código HTTP correspondiente (422, 404 o 409) sin persistir cambios.
9. IF el Administrador intenta actualizar una Reserva cuyo Estado_De_Reserva es "cancelled", THEN THE Servicio_De_Reservas SHALL rechazar la operación y THE API_De_Reservas SHALL retornar un error con código HTTP 409 indicando que una reserva cancelada no puede ser modificada.
10. WHEN la actualización de una Reserva es exitosa, THE API_De_Reservas SHALL retornar un código HTTP 200 y todos los atributos actualizados de la Reserva en formato JSON.

### Requerimiento 8: Cancelación de reservas

**Historia de Usuario:** Como Administrador, quiero cancelar una reserva, para liberar el rango de fechas de una habitación conservando el registro histórico de la reserva.

#### Criterios de Aceptación

1. WHEN el Administrador solicita la cancelación de una Reserva existente con Estado_De_Reserva "confirmed", THE Servicio_De_Reservas SHALL cambiar el Estado_De_Reserva a "cancelled" y persistir el cambio sin eliminar el registro de la base de datos.
2. THE Servicio_De_Reservas SHALL conservar todos los demás atributos de la Reserva cancelada (id, guest_id, room_id, check_in_date, check_out_date, total_price, created_at) sin modificarlos, actualizando únicamente el status y el updated_at.
3. IF el Administrador intenta cancelar una reserva que no existe, THEN THE API_De_Reservas SHALL retornar un error con código HTTP 404 indicando que la reserva no fue encontrada.
4. IF el Administrador intenta cancelar una Reserva cuyo Estado_De_Reserva ya es "cancelled", THEN THE Servicio_De_Reservas SHALL rechazar la operación y THE API_De_Reservas SHALL retornar un error con código HTTP 409 indicando que la reserva ya se encuentra cancelada.
5. WHEN la cancelación de una Reserva es exitosa, THE API_De_Reservas SHALL retornar un código HTTP 200 junto con los atributos de la Reserva actualizada mostrando el Estado_De_Reserva "cancelled".
6. THE Sistema_De_Reservas SHALL conservar de forma permanente las reservas canceladas para fines históricos y no ofrecer una operación de eliminación física en el alcance del MVP.

### Requerimiento 9: Separación de responsabilidades por capas

**Historia de Usuario:** Como desarrollador, quiero que el módulo respete la arquitectura por capas, para mantener el código organizado y facilitar el mantenimiento.

#### Criterios de Aceptación

1. THE API_De_Reservas SHALL únicamente recibir solicitudes HTTP, validar datos de entrada mediante esquemas Pydantic definidos en el paquete schemas, y delegar toda operación al Servicio_De_Reservas sin invocar directamente al Repositorio_De_Reservas ni acceder a la base de datos.
2. THE Servicio_De_Reservas SHALL contener toda la lógica de negocio (validación de existencia, validación de fechas, cálculo de precio, prevención de solapamiento y transición de estados), comunicarse con los repositorios o servicios correspondientes para el acceso a datos, y no manejar conceptos HTTP tales como códigos de estado, objetos Request o objetos Response.
3. THE Repositorio_De_Reservas SHALL ejecutar operaciones sobre la base de datos PostgreSQL mediante SQLAlchemy sin implementar reglas de negocio ni validaciones de dominio.
4. THE Sistema_De_Reservas SHALL respetar una dirección de dependencia estricta donde la capa API depende únicamente de Services, la capa Services depende únicamente de Repositories y de los módulos existentes de Huéspedes y Habitaciones, y la capa Repositories depende únicamente de Models, sin dependencias inversas ni circulares entre capas.
5. THE Sistema_De_Reservas SHALL reutilizar los modelos, servicios y repositorios existentes de Room Management y Guest Management donde sea apropiado, en lugar de rediseñarlos o duplicarlos.

### Requerimiento 10: Manejo de errores

**Historia de Usuario:** Como Administrador, quiero recibir mensajes de error claros y consistentes, para entender qué salió mal al realizar una operación.

#### Criterios de Aceptación

1. IF ocurre un error de conexión con la base de datos o una excepción no controlada en cualquier capa del sistema, THEN THE Sistema_De_Reservas SHALL retornar un código HTTP 500 con un mensaje genérico de error interno sin exponer detalles de la infraestructura tales como direcciones de servidor, trazas de pila o nombres de tablas.
2. THE API_De_Reservas SHALL reutilizar el manejo de errores existente en StayBook (los handlers globales `app_exception_handler` y `generic_exception_handler` y las excepciones de dominio que heredan de `AppException`), manteniendo el mismo formato de respuesta de error ya utilizado por los módulos de habitaciones y huéspedes, sin definir un esquema de error nuevo o distinto para reservas.
3. IF el Administrador envía una solicitud con un formato de cuerpo inválido o campos que no cumplen las reglas de tipo o formato definidas en el esquema Pydantic, THEN THE API_De_Reservas SHALL retornar un código HTTP 422 con el detalle de validación generado por FastAPI que indique qué campos son inválidos y la razón del rechazo.
4. IF el Administrador realiza una operación que viola una regla de negocio (como un Solapamiento de reservas, la modificación de una reserva cancelada o la cancelación de una reserva ya cancelada), THEN THE API_De_Reservas SHALL retornar un código HTTP 409 con un mensaje que indique la regla de negocio que fue violada, empleando el mismo mecanismo de excepciones de dominio ya existente.
5. IF el Administrador solicita o referencia un recurso que no existe en el sistema (reserva, huésped o habitación), THEN THE API_De_Reservas SHALL retornar un código HTTP 404 con un mensaje indicando qué recurso no fue encontrado.

### Requerimiento 11: Autenticación y autorización

**Historia de Usuario:** Como Administrador, quiero que las operaciones de gestión de reservas estén protegidas por autenticación y autorización, para que solo usuarios autorizados puedan gestionar las reservas.

#### Criterios de Aceptación

1. THE API_De_Reservas SHALL proteger todos sus endpoints reutilizando la Dependencia_De_Autenticación existente de StayBook (la dependencia de FastAPI `get_current_admin_user`), sin introducir ni requerir un nuevo middleware de autenticación.
2. IF una solicitud no incluye un Token_JWT o el token es inválido (expirado, malformado o con firma incorrecta), THEN la Dependencia_De_Autenticación SHALL rechazar la solicitud y THE API_De_Reservas SHALL retornar un código HTTP 401, con el mismo comportamiento que los módulos de habitaciones y huéspedes.
3. IF el usuario autenticado no posee el Rol_Administrador, THEN la Dependencia_De_Autenticación SHALL rechazar la solicitud y THE API_De_Reservas SHALL retornar un código HTTP 403, con el mismo comportamiento que los módulos de habitaciones y huéspedes.
4. WHEN un usuario con Token_JWT válido y Rol_Administrador realiza una solicitud a cualquier endpoint del módulo de reservas, THE API_De_Reservas SHALL permitir que la solicitud continúe hacia la lógica del módulo sin modificaciones.

### Requerimiento 12: Requerimientos no funcionales

**Historia de Usuario:** Como desarrollador, quiero que el módulo de reservas cumpla con estándares de observabilidad y documentación, para facilitar el diagnóstico de problemas y la integración con otros sistemas.

#### Criterios de Aceptación

1. WHEN una operación de creación, actualización o cancelación de una Reserva se ejecuta (exitosamente o con error), THE Sistema_De_Reservas SHALL registrar en el Registro_De_Operaciones un evento con los siguientes datos: marca temporal (timestamp), tipo de operación (create, update, cancel), identificador de la reserva afectada y resultado de la operación (success o failure).
2. THE Registro_De_Operaciones SHALL excluir datos sensibles tales como tokens de autenticación, contraseñas o información personal del huésped en todos los registros generados.
3. THE API_De_Reservas SHALL generar documentación OpenAPI/Swagger de forma automática mediante FastAPI, accesible en las rutas /docs (interfaz Swagger UI) y /redoc (interfaz ReDoc).
