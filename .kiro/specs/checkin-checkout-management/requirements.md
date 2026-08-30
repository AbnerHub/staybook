# Requirements Document

## Introduction

Este documento define los requerimientos para el módulo de administración de check-in y check-out del sistema StayBook. El módulo gestiona el ciclo de vida operativo de una reserva existente: permite al Administrador registrar la entrada (check-in) y la salida (check-out) de un huésped, actualizando de forma consistente el estado de la reserva y el estado operativo de la habitación asociada.

Este spec reutiliza los módulos ya implementados de habitaciones (Room Management), huéspedes (Guest Management) y reservas (Reservation Management). Extiende el ciclo de vida de la reserva con dos nuevos estados y define las transiciones válidas entre ellos.

Queda **fuera del alcance** de este spec: pagos, facturas, reembolsos, ajustes de tarifa por entrada/salida anticipada o tardía, flujos de limpieza (housekeeping), estado de limpieza, gestión de llaves o tarjetas, notificaciones, auto check-in del huésped en línea, frontend, Docker, CI/CD e infraestructura AWS.

## Hallazgos sobre el código existente (base para estos requerimientos)

Estos requerimientos se basan en la inspección del código real de StayBook:

- **`ReservationStatus` actual** (en `app/models/reservation.py`) contiene únicamente los valores `confirmed` y `cancelled`. Este spec requiere **extender** ese enum con `checked_in` y `checked_out`.
- **`RoomStatus` existente** (en `app/models/room.py`) usa valores en español: `disponible`, `ocupada`, `mantenimiento`. El comportamiento conceptual "habitación ocupada / disponible" se mapea a los valores existentes `ocupada` y `disponible`. Este spec **no** introduce valores nuevos ni incompatibles en `RoomStatus`; reutiliza `RoomStatus.OCUPADA` y `RoomStatus.DISPONIBLE`.
- **`ReservationRepository.get_active_overlapping`** actualmente filtra solo por `status == confirmed`. Este spec requiere **modificar** esa consulta para considerar activas las reservas con estado `confirmed` **o** `checked_in`, de modo que una reserva con check-in realizado siga bloqueando reservas solapadas.
- **Migración `003_create_reservations_table.py`** define un `CheckConstraint` `status IN ('confirmed', 'cancelled')`. Este spec requiere una **nueva migración** que amplíe los valores permitidos para incluir `checked_in` y `checked_out`.

## Glossary

- **Sistema_De_Estancia**: Módulo del sistema StayBook responsable de gestionar el ciclo de vida operativo (check-in / check-out) de las reservas.
- **API_De_Estancia**: Capa de presentación REST que recibe solicitudes HTTP y devuelve respuestas HTTP relacionadas con check-in y check-out.
- **Servicio_De_Estancia**: Capa de lógica de negocio que aplica las reglas de transición de estado y coordina los cambios sobre la reserva y la habitación.
- **Reserva**: Entidad existente (módulo Reservation Management) cuyo ciclo de vida operativo gestiona este módulo.
- **Habitación**: Entidad existente (módulo Room Management) cuyo estado operativo se actualiza al hacer check-in o check-out.
- **Administrador**: Usuario del sistema con Rol_Administrador. Es el único actor contemplado en el MVP de StayBook.
- **Estado_De_Reserva**: Valor que indica el estado del ciclo de vida de una reserva: `confirmed`, `checked_in`, `checked_out` o `cancelled`.
- **Estado_Operativo_De_Habitación**: Valor del `RoomStatus` existente que indica el estado de la habitación: `disponible`, `ocupada` o `mantenimiento`.
- **Check_In**: Operación que registra la entrada del huésped a la habitación de una reserva confirmada.
- **Check_Out**: Operación que registra la salida del huésped de una reserva con check-in realizado.
- **Fecha_Local_Del_Hotel**: Fecha actual en la zona horaria local del hotel, utilizada para validar la ventana permitida de check-in.
- **Reserva_Activa_Para_Solapamiento**: Reserva que ocupa efectivamente la habitación para efectos de detección de solapamiento; incluye los estados `confirmed` y `checked_in`, y excluye `cancelled` y `checked_out`.
- **Transición_De_Estado**: Cambio del Estado_De_Reserva de un valor a otro; solo se permiten las transiciones definidas como válidas.
- **Token_JWT**: Token de autenticación en formato JSON Web Token utilizado para verificar la identidad del usuario.
- **Rol_Administrador**: Rol del sistema que otorga permisos para realizar operaciones de gestión de estancia.
- **Dependencia_De_Autenticación**: Mecanismo de autenticación y autorización basado en dependencias de FastAPI (`get_current_admin_user`) ya existente en StayBook y reutilizado por este módulo.
- **Registro_De_Operaciones**: Sistema de logging que registra las operaciones realizadas con fines de auditoría.

## Reservation Lifecycle Definition

### Estados del ciclo de vida

| Estado | Descripción |
|--------|-------------|
| `confirmed` | Reserva creada y vigente; el huésped aún no ha ingresado. Estado inicial. |
| `checked_in` | El huésped ha ingresado a la habitación. La habitación está ocupada. |
| `checked_out` | El huésped ha salido. La estancia finalizó. Estado terminal. |
| `cancelled` | La reserva fue cancelada antes del check-in. Estado terminal. |

### Transiciones válidas

| Transición | Operación | Válida |
|-----------|-----------|--------|
| `confirmed` → `checked_in` | Check-in | Sí |
| `confirmed` → `cancelled` | Cancelación (módulo Reservation Management existente) | Sí |
| `checked_in` → `checked_out` | Check-out | Sí |
| Cualquier otra transición | — | No |

### Transiciones inválidas (ejemplos, deben rechazarse)

- `cancelled` → `checked_in` (no se puede hacer check-in de una reserva cancelada).
- `checked_out` → `checked_in` (no se puede reingresar tras el check-out).
- `confirmed` → `checked_out` (no se puede hacer check-out sin check-in previo).
- `checked_in` → `checked_in` (no se puede hacer check-in dos veces).
- `checked_out` → `checked_out` (no se puede hacer check-out dos veces).
- `checked_in` → `cancelled` (no está contemplado en el alcance del MVP).

## Requirements

### Requerimiento 1: Extensión del ciclo de vida de la reserva

**Historia de Usuario:** Como desarrollador, quiero que la reserva soporte los estados de check-in y check-out, para poder representar el ciclo de vida operativo de una estancia.

#### Criterios de Aceptación

1. THE Sistema_De_Estancia SHALL extender el enum `ReservationStatus` existente para incluir los valores `checked_in` y `checked_out`, además de los valores actuales `confirmed` y `cancelled`, sin eliminar ni renombrar los valores existentes.
2. THE Sistema_De_Estancia SHALL proporcionar una migración de base de datos (Alembic) que amplíe la restricción de valores permitidos de la columna `status` de la tabla `reservations` para admitir `confirmed`, `checked_in`, `checked_out` y `cancelled`.
3. THE Sistema_De_Estancia SHALL preservar `confirmed` como estado inicial de toda reserva creada por el módulo de Reservation Management, sin alterar ese comportamiento existente.
4. THE Sistema_De_Estancia SHALL tratar `checked_out` y `cancelled` como estados terminales desde los cuales no se permite ninguna transición dentro del alcance de este módulo.

### Requerimiento 2: Check-in de una reserva

**Historia de Usuario:** Como Administrador, quiero registrar el check-in de una reserva confirmada, para reflejar que el huésped ingresó y que la habitación quedó ocupada.

#### Criterios de Aceptación

1. WHEN el Administrador solicita el Check_In de una Reserva existente cuyo Estado_De_Reserva es `confirmed` y la operación es permitida según las reglas de fecha, THE Servicio_De_Estancia SHALL cambiar el Estado_De_Reserva a `checked_in` y persistir el cambio.
2. WHEN el Check_In se completa exitosamente, THE Servicio_De_Estancia SHALL actualizar el Estado_Operativo_De_Habitación de la Habitación asociada a `RoomStatus.OCUPADA` (`ocupada`).
3. IF el Administrador solicita el Check_In de una reserva que no existe, THEN THE API_De_Estancia SHALL retornar un error con código HTTP 404 indicando que la reserva no fue encontrada.
4. IF el Administrador solicita el Check_In de una Reserva cuyo Estado_De_Reserva no es `confirmed` (por ejemplo `checked_in`, `checked_out` o `cancelled`), THEN THE Servicio_De_Estancia SHALL rechazar la operación y THE API_De_Estancia SHALL retornar un error con código HTTP 409 indicando que la transición de estado no es válida.
5. WHEN el Check_In se completa exitosamente, THE API_De_Estancia SHALL retornar un código HTTP 200 junto con los datos de la Reserva actualizada mostrando el Estado_De_Reserva `checked_in`.
6. THE Servicio_De_Estancia SHALL preservar todos los demás atributos de la Reserva (id, guest_id, room_id, check_in_date, check_out_date, total_price, created_at) y del Huésped sin modificarlos durante el Check_In.

### Requerimiento 3: Regla de fecha para el check-in

**Historia de Usuario:** Como Administrador, quiero que el sistema valide que el check-in ocurra dentro de la ventana de fechas de la reserva, para evitar entradas anticipadas o fuera del periodo reservado.

#### Criterios de Aceptación

1. THE Servicio_De_Estancia SHALL permitir el Check_In únicamente cuando la Fecha_Local_Del_Hotel sea mayor o igual a `check_in_date` y estrictamente menor que `check_out_date` de la Reserva.
2. IF la Fecha_Local_Del_Hotel es anterior a `check_in_date`, THEN THE Servicio_De_Estancia SHALL rechazar el Check_In (entrada anticipada) y THE API_De_Estancia SHALL retornar un error con código HTTP 409 indicando que el check-in no está permitido antes de la fecha de entrada.
3. IF la Fecha_Local_Del_Hotel es mayor o igual a `check_out_date`, THEN THE Servicio_De_Estancia SHALL rechazar el Check_In y THE API_De_Estancia SHALL retornar un error con código HTTP 409 indicando que el check-in no está permitido en o después de la fecha de salida.
4. THE Servicio_De_Estancia SHALL determinar la Fecha_Local_Del_Hotel a partir de una fuente de fecha configurable/consistente del sistema, de modo que el comportamiento sea determinista y verificable en pruebas.

### Requerimiento 4: Check-out de una reserva

**Historia de Usuario:** Como Administrador, quiero registrar el check-out de una reserva con check-in realizado, para reflejar que el huésped salió y que la habitación quedó disponible.

#### Criterios de Aceptación

1. WHEN el Administrador solicita el Check_Out de una Reserva existente cuyo Estado_De_Reserva es `checked_in`, THE Servicio_De_Estancia SHALL cambiar el Estado_De_Reserva a `checked_out` y persistir el cambio.
2. WHEN el Check_Out se completa exitosamente, THE Servicio_De_Estancia SHALL actualizar el Estado_Operativo_De_Habitación de la Habitación asociada a `RoomStatus.DISPONIBLE` (`disponible`).
3. IF el Administrador solicita el Check_Out de una reserva que no existe, THEN THE API_De_Estancia SHALL retornar un error con código HTTP 404 indicando que la reserva no fue encontrada.
4. IF el Administrador solicita el Check_Out de una Reserva cuyo Estado_De_Reserva no es `checked_in` (por ejemplo `confirmed`, `checked_out` o `cancelled`), THEN THE Servicio_De_Estancia SHALL rechazar la operación y THE API_De_Estancia SHALL retornar un error con código HTTP 409 indicando que la transición de estado no es válida.
5. THE Servicio_De_Estancia SHALL permitir el Check_Out en o antes o después de la `check_out_date` planificada, siempre que la Reserva se encuentre actualmente en estado `checked_in`, sin aplicar ajustes de facturación por salida anticipada o tardía.
6. WHEN el Check_Out se completa exitosamente, THE API_De_Estancia SHALL retornar un código HTTP 200 junto con los datos de la Reserva actualizada mostrando el Estado_De_Reserva `checked_out`.
7. THE Servicio_De_Estancia SHALL preservar de forma permanente la Reserva tras el Check_Out, sin eliminar el registro y sin modificar sus demás atributos.

### Requerimiento 5: Consistencia entre estado de reserva y estado de habitación

**Historia de Usuario:** Como Administrador, quiero que el estado de la reserva y el estado operativo de la habitación se mantengan consistentes, para que el sistema no quede en un estado contradictorio tras un check-in o check-out.

#### Criterios de Aceptación

1. WHEN el Servicio_De_Estancia ejecuta un Check_In o Check_Out, THE Servicio_De_Estancia SHALL aplicar el cambio de Estado_De_Reserva y el cambio de Estado_Operativo_De_Habitación dentro de la misma transacción de base de datos, utilizando la sesión de SQLAlchemy existente.
2. IF cualquiera de los dos cambios (reserva o habitación) falla durante la operación, THEN THE Servicio_De_Estancia SHALL revertir (rollback) ambos cambios, de modo que no se persista un estado parcial o inconsistente.
3. THE Servicio_De_Estancia SHALL reutilizar el `RoomRepository` existente para actualizar el Estado_Operativo_De_Habitación, sin implementar acceso a datos de habitaciones duplicado.
4. THE Sistema_De_Estancia SHALL evitar mecanismos de transacciones distribuidas, colas o bloqueos complejos; la consistencia se logra mediante una única transacción de base de datos con la arquitectura de sesión existente.

### Requerimiento 6: Impacto en la detección de solapamiento de reservas

**Historia de Usuario:** Como Administrador, quiero que una reserva con check-in realizado siga bloqueando reservas solapadas, para evitar la doble asignación de una habitación ocupada.

#### Criterios de Aceptación

1. THE Sistema_De_Estancia SHALL considerar como Reserva_Activa_Para_Solapamiento a las reservas cuyo Estado_De_Reserva sea `confirmed` o `checked_in`.
2. THE Sistema_De_Estancia SHALL excluir de la detección de solapamiento a las reservas cuyo Estado_De_Reserva sea `cancelled` o `checked_out`.
3. THE Sistema_De_Estancia SHALL modificar la consulta `get_active_overlapping` del `ReservationRepository` existente para que incluya los estados `confirmed` y `checked_in`, en lugar de considerar únicamente `confirmed`.
4. THE Sistema_De_Estancia SHALL preservar la regla de solapamiento de intervalo semiabierto `[check_in_date, check_out_date)` ya definida en Reservation Management, sin alterar su semántica.
5. THE Sistema_De_Estancia SHALL determinar la disponibilidad por rangos de fechas futuras a partir de las fechas de la reserva y de su Estado_De_Reserva, y no a partir del Estado_Operativo_De_Habitación actual.

### Requerimiento 7: Endpoints dedicados y protección del PATCH de reservas

**Historia de Usuario:** Como Administrador, quiero operaciones dedicadas de check-in y check-out, para gestionar el ciclo de vida sin poder editar arbitrariamente el estado de la reserva.

#### Criterios de Aceptación

1. THE API_De_Estancia SHALL exponer una operación dedicada de Check_In en `POST /api/v1/reservations/{reservation_id}/check-in`.
2. THE API_De_Estancia SHALL exponer una operación dedicada de Check_Out en `POST /api/v1/reservations/{reservation_id}/check-out`.
3. THE API_De_Estancia SHALL NOT permitir la edición directa y arbitraria del campo `status` de la reserva a través del endpoint PATCH existente de Reservation Management; las transiciones de estado del ciclo de vida operativo se realizan únicamente mediante los endpoints dedicados de check-in y check-out (y la cancelación existente).
4. IF el Administrador envía un identificador de reserva con formato inválido (no entero positivo) a un endpoint de check-in o check-out, THEN THE API_De_Estancia SHALL retornar un error de validación con código HTTP 422.

### Requerimiento 8: Separación de responsabilidades por capas

**Historia de Usuario:** Como desarrollador, quiero que el módulo respete la arquitectura por capas, para mantener el código organizado y facilitar el mantenimiento.

#### Criterios de Aceptación

1. THE API_De_Estancia SHALL únicamente recibir solicitudes HTTP, validar el identificador de la reserva y delegar la operación al Servicio_De_Estancia, sin acceder directamente a la base de datos.
2. THE Servicio_De_Estancia SHALL contener toda la lógica de negocio (validación de existencia, validación de transición de estado, validación de fecha de check-in, y coordinación del cambio de estado de habitación), sin manejar conceptos HTTP tales como códigos de estado, objetos Request o objetos Response.
3. THE Servicio_De_Estancia SHALL reutilizar el `ReservationRepository` y el `RoomRepository` existentes para el acceso a datos, sin duplicar lógica de acceso a datos.
4. THE Sistema_De_Estancia SHALL respetar la dirección de dependencia estricta API → Service → Repository → Model, sin dependencias inversas ni circulares entre capas.
5. THE Sistema_De_Estancia SHALL reutilizar los modelos, servicios y repositorios existentes de Room, Guest y Reservation donde sea apropiado, en lugar de rediseñarlos o duplicarlos.

### Requerimiento 9: Manejo de errores

**Historia de Usuario:** Como Administrador, quiero recibir mensajes de error claros y consistentes, para entender qué salió mal al realizar un check-in o check-out.

#### Criterios de Aceptación

1. IF ocurre un error de conexión con la base de datos o una excepción no controlada en cualquier capa del sistema, THEN THE Sistema_De_Estancia SHALL retornar un código HTTP 500 con un mensaje genérico de error interno sin exponer detalles de la infraestructura.
2. THE API_De_Estancia SHALL reutilizar el manejo de errores existente en StayBook (los handlers globales `app_exception_handler` y `generic_exception_handler` y las excepciones de dominio que heredan de `AppException`), manteniendo el mismo formato de respuesta de error de los módulos existentes, sin definir un esquema de error nuevo.
3. IF el Administrador solicita una operación sobre una reserva inexistente, THEN THE API_De_Estancia SHALL retornar un código HTTP 404 con un mensaje en el campo `detail` indicando que la reserva no fue encontrada.
4. IF el Administrador intenta una Transición_De_Estado inválida (check-in fuera de estado `confirmed`, check-out fuera de estado `checked_in`, doble check-in o doble check-out), THEN THE API_De_Estancia SHALL retornar un código HTTP 409 con un mensaje en el campo `detail` que indique que la transición no es válida.
5. IF el Check_In se rechaza por la regla de fecha (entrada anticipada o en/después de la fecha de salida), THEN THE API_De_Estancia SHALL retornar un código HTTP 409 con un mensaje en el campo `detail` que indique la razón del rechazo.

### Requerimiento 10: Autenticación y autorización

**Historia de Usuario:** Como Administrador, quiero que las operaciones de check-in y check-out estén protegidas por autenticación y autorización, para que solo usuarios autorizados puedan ejecutarlas.

#### Criterios de Aceptación

1. THE API_De_Estancia SHALL proteger todos sus endpoints reutilizando la Dependencia_De_Autenticación existente (`get_current_admin_user`), sin introducir ni requerir un nuevo middleware de autenticación.
2. IF una solicitud no incluye un Token_JWT o el token es inválido (expirado, malformado o con firma incorrecta), THEN la Dependencia_De_Autenticación SHALL rechazar la solicitud y THE API_De_Estancia SHALL retornar un código HTTP 401, con el mismo comportamiento que los módulos existentes.
3. IF el usuario autenticado no posee el Rol_Administrador, THEN la Dependencia_De_Autenticación SHALL rechazar la solicitud y THE API_De_Estancia SHALL retornar un código HTTP 403, con el mismo comportamiento que los módulos existentes.
4. WHEN un usuario con Token_JWT válido y Rol_Administrador realiza una solicitud a cualquier endpoint del módulo, THE API_De_Estancia SHALL permitir que la solicitud continúe hacia la lógica del módulo sin modificaciones.

### Requerimiento 11: Auditoría sin exponer PII

**Historia de Usuario:** Como Administrador, quiero que las operaciones de check-in y check-out queden registradas para auditoría sin exponer datos personales del huésped, para cumplir con la observabilidad y la protección de datos.

#### Criterios de Aceptación

1. WHEN una operación de Check_In o Check_Out se ejecuta (exitosamente o con error), THE Sistema_De_Estancia SHALL registrar en el Registro_De_Operaciones un evento con: marca temporal (timestamp), tipo de operación (check_in o check_out), identificador de la reserva afectada y resultado de la operación (success o failure).
2. THE Registro_De_Operaciones SHALL reutilizar la función de auditoría `audit_log` existente, sin exponer datos sensibles ni PII del huésped (nombre, correo, teléfono o número de identificación), tokens ni contraseñas.
3. THE Sistema_De_Estancia SHALL registrar únicamente identificadores internos (id de reserva) y metadatos de la operación, consistente con el comportamiento de auditoría de los módulos existentes.
