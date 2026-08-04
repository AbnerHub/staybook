# Requirements Document

## Introduction

Este documento define los requerimientos para el módulo de administración de habitaciones del sistema StayBook. El módulo permite al personal del hotel gestionar el catálogo de habitaciones, incluyendo su registro, consulta, actualización, eliminación y verificación de disponibilidad. Este spec cubre exclusivamente la gestión de habitaciones para un único hotel y no incluye funcionalidades de clientes, reservas, check-in ni check-out.

## Glossary

- **Sistema_De_Habitaciones**: Módulo del sistema StayBook responsable de la administración de habitaciones del hotel.
- **API_De_Habitaciones**: Capa de presentación REST que recibe solicitudes HTTP y devuelve respuestas HTTP relacionadas con habitaciones.
- **Servicio_De_Habitaciones**: Capa de lógica de negocio que aplica reglas y validaciones sobre las operaciones de habitaciones.
- **Repositorio_De_Habitaciones**: Capa de acceso a datos que ejecuta operaciones CRUD sobre la tabla de habitaciones en PostgreSQL.
- **Habitación**: Entidad que representa un cuarto físico del hotel con sus atributos (número, tipo, precio, estado, capacidad).
- **Personal_Del_Hotel**: Usuario del sistema que administra las habitaciones.
- **Número_De_Habitación**: Identificador único asignado por el hotel a cada cuarto físico.
- **Estado_De_Habitación**: Valor que indica si una habitación está disponible, ocupada o en mantenimiento.
- **Token_JWT**: Token de autenticación en formato JSON Web Token utilizado para verificar la identidad del usuario.
- **Rol_Administrador**: Rol del sistema que otorga permisos para realizar operaciones de gestión de habitaciones.
- **Middleware_De_Autenticación**: Componente que intercepta las solicitudes HTTP para verificar la autenticación y autorización del usuario antes de permitir el acceso a los endpoints protegidos.
- **Registro_De_Operaciones**: Sistema de logging que registra las operaciones realizadas sobre las habitaciones con fines de auditoría.

## Entity Definition

### Habitación (Room)

Entidad principal del módulo que representa un cuarto físico del hotel.

| Atributo | Tipo de Dato | Obligatorio | Restricciones | Descripción |
|----------|-------------|-------------|---------------|-------------|
| id | integer | Sí (auto-generado) | Clave primaria, auto-incremental | Identificador único interno de la habitación |
| room_number | string | Sí | Máximo 10 caracteres, único | Número o código asignado por el hotel al cuarto físico |
| room_type | enum | Sí | Valores permitidos: "individual", "doble", "suite" | Tipo de habitación según configuración y capacidad |
| price_per_night | decimal | Sí | Rango: 0.01 – 999999.99 | Precio por noche de la habitación en la moneda local |
| capacity | integer | Sí | Rango: 1 – 20 | Número máximo de huéspedes que admite la habitación |
| status | enum | Sí | Valores permitidos: "disponible", "ocupada", "mantenimiento". Valor por defecto: "disponible" | Estado actual de la habitación |
| description | string | No (nullable) | Máximo 255 caracteres | Descripción adicional de la habitación |
| floor | integer | No (nullable) | — | Número de piso donde se ubica la habitación |
| created_at | datetime | Sí (auto-gestionado) | Se asigna automáticamente al crear el registro | Fecha y hora de creación del registro |
| updated_at | datetime | Sí (auto-gestionado) | Se actualiza automáticamente en cada modificación | Fecha y hora de la última actualización del registro |

**Notas:**
- Los campos `id`, `created_at` y `updated_at` son gestionados automáticamente por el sistema y no son proporcionados por el usuario.
- El campo `room_number` debe ser único en toda la base de datos para evitar duplicidad de habitaciones.
- El campo `status` se inicializa con el valor "disponible" al momento de la creación si no se especifica otro valor válido.

## Requirements

### Requerimiento 1: Registro de nuevas habitaciones

**Historia de Usuario:** Como personal del hotel, quiero registrar nuevas habitaciones en el sistema, para mantener actualizado el catálogo de cuartos disponibles.

#### Criterios de Aceptación

1. WHEN el Personal_Del_Hotel envía una solicitud de registro con datos válidos (número de habitación como cadena alfanumérica de máximo 10 caracteres, tipo con valor "individual", "doble" o "suite", precio por noche entre 0.01 y 999,999.99, y capacidad entre 1 y 20 personas), THE Servicio_De_Habitaciones SHALL crear una nueva Habitación con Estado_De_Habitación "disponible" y persistirla en la base de datos.
2. IF el Personal_Del_Hotel intenta registrar una habitación con un Número_De_Habitación que ya existe en la base de datos, THEN THE Servicio_De_Habitaciones SHALL rechazar la operación y retornar un error indicando que el número de habitación ya está registrado.
3. IF el Personal_Del_Hotel envía una solicitud de registro con campos obligatorios faltantes (número, tipo, precio por noche, capacidad) o con valores fuera de los rangos permitidos, THEN THE API_De_Habitaciones SHALL retornar un error de validación con código HTTP 422 y una descripción de cada campo faltante o inválido.
4. WHEN el registro de la Habitación se completa exitosamente, THE API_De_Habitaciones SHALL retornar un código HTTP 201 y los datos de la Habitación creada incluyendo: número, tipo, precio por noche, capacidad y Estado_De_Habitación.

### Requerimiento 2: Listado de habitaciones

**Historia de Usuario:** Como personal del hotel, quiero listar todas las habitaciones registradas, para tener visibilidad del catálogo completo de cuartos del hotel.

#### Criterios de Aceptación

1. WHEN el Personal_Del_Hotel solicita el listado de habitaciones, THE Sistema_De_Habitaciones SHALL retornar todas las habitaciones registradas con sus atributos completos (id, número, tipo, precio por noche, capacidad, estado, descripción, piso, fecha de creación y fecha de actualización).
2. IF no existen habitaciones registradas en el sistema, THEN THE API_De_Habitaciones SHALL retornar una lista vacía con código HTTP 200.
3. THE API_De_Habitaciones SHALL retornar un código HTTP 200 junto con la lista de habitaciones en formato JSON.

### Requerimiento 3: Consulta de disponibilidad de habitaciones

**Historia de Usuario:** Como personal del hotel, quiero consultar la disponibilidad de habitaciones, para saber qué cuartos están libres en un momento dado.

#### Criterios de Aceptación

1. WHEN el Personal_Del_Hotel consulta la disponibilidad, THE Servicio_De_Habitaciones SHALL retornar únicamente las habitaciones cuyo Estado_De_Habitación sea "disponible", incluyendo todos sus atributos (número, tipo, precio por noche, capacidad y estado).
2. IF el Personal_Del_Hotel consulta la disponibilidad y no existen habitaciones con Estado_De_Habitación "disponible", THEN THE API_De_Habitaciones SHALL retornar una lista vacía con código HTTP 200.
3. THE API_De_Habitaciones SHALL retornar un código HTTP 200 junto con la lista de habitaciones disponibles en formato JSON.

### Requerimiento 4: Actualización de información de habitaciones

**Historia de Usuario:** Como personal del hotel, quiero actualizar la información de una habitación existente, para reflejar cambios en el tipo, precio, capacidad o estado del cuarto.

#### Criterios de Aceptación

1. WHEN el Personal_Del_Hotel envía una solicitud de actualización parcial o completa con datos válidos para una Habitación existente, THE Servicio_De_Habitaciones SHALL modificar únicamente los atributos incluidos en la solicitud, preservar los atributos no incluidos sin cambios y persistir los cambios en la base de datos.
2. IF el Personal_Del_Hotel intenta actualizar una habitación que no existe, THEN THE API_De_Habitaciones SHALL retornar un error con código HTTP 404 indicando que la habitación no fue encontrada.
3. IF el Personal_Del_Hotel envía datos de actualización que violan las reglas de validación (precio_por_noche fuera del rango 0.01 a 999999.99, capacidad fuera del rango 1 a 20 personas, estado con un valor distinto a "disponible", "ocupada" o "mantenimiento", o campos de texto que excedan 255 caracteres), THEN THE API_De_Habitaciones SHALL retornar un error de validación con código HTTP 422 y una descripción de los campos inválidos.
4. IF el Personal_Del_Hotel intenta cambiar el Número_De_Habitación a uno que ya existe en otra habitación, THEN THE Servicio_De_Habitaciones SHALL rechazar la operación y THE API_De_Habitaciones SHALL retornar un error indicando duplicidad.
5. WHEN la actualización de una Habitación es exitosa, THE API_De_Habitaciones SHALL retornar un código HTTP 200 y todos los atributos actualizados de la Habitación en formato JSON.

### Requerimiento 5: Eliminación de habitaciones

**Historia de Usuario:** Como personal del hotel, quiero eliminar una habitación del sistema, para remover cuartos que ya no existen o que fueron registrados por error.

#### Criterios de Aceptación

1. WHEN el Personal_Del_Hotel solicita la eliminación de una Habitación existente por su identificador, THE Servicio_De_Habitaciones SHALL eliminar la Habitación de la base de datos de forma permanente (hard delete), removiendo físicamente el registro de la tabla sin posibilidad de recuperación.
2. WHEN el Personal_Del_Hotel intenta eliminar una habitación que no existe, THE Servicio_De_Habitaciones SHALL rechazar la operación y THE API_De_Habitaciones SHALL retornar un error con código HTTP 404 y un mensaje indicando que la habitación no fue encontrada.
3. WHILE una Habitación tiene Estado_De_Habitación "ocupada", THE Servicio_De_Habitaciones SHALL rechazar la eliminación y THE API_De_Habitaciones SHALL retornar un error con código HTTP 409 indicando que no se puede eliminar una habitación ocupada.
4. WHILE una Habitación tiene Estado_De_Habitación "mantenimiento", THE Servicio_De_Habitaciones SHALL permitir la eliminación de la Habitación.
5. WHEN la eliminación de una Habitación es exitosa, THE API_De_Habitaciones SHALL retornar un código HTTP 204 sin cuerpo de respuesta.
6. THE Servicio_De_Habitaciones SHALL implementar eliminación permanente (hard delete) como comportamiento del MVP; una versión futura podrá implementar eliminación lógica (soft delete) mediante un campo de marca temporal.

### Requerimiento 6: Obtener información de una habitación específica

**Historia de Usuario:** Como personal del hotel, quiero obtener la información detallada de una habitación específica, para consultar sus atributos actuales.

#### Criterios de Aceptación

1. WHEN el Personal_Del_Hotel solicita la información de una Habitación existente por su identificador único (id), THE Sistema_De_Habitaciones SHALL retornar los atributos de la Habitación: id, room_number, room_type, price_per_night, capacity, status, description, floor, created_at y updated_at.
2. IF el Personal_Del_Hotel solicita la información de una habitación cuyo identificador no existe en la base de datos, THEN THE API_De_Habitaciones SHALL retornar un error con código HTTP 404 y un mensaje indicando que la habitación no fue encontrada.
3. WHEN la consulta de una Habitación es exitosa, THE API_De_Habitaciones SHALL retornar un código HTTP 200 junto con los atributos completos de la Habitación en formato JSON.
4. IF el Personal_Del_Hotel envía un identificador con formato inválido (no entero positivo), THEN THE API_De_Habitaciones SHALL retornar un error de validación con código HTTP 422 indicando que el identificador debe ser un número entero positivo.

### Requerimiento 7: Separación de responsabilidades por capas

**Historia de Usuario:** Como desarrollador, quiero que el módulo respete la arquitectura por capas, para mantener el código organizado y facilitar el mantenimiento.

#### Criterios de Aceptación

1. THE API_De_Habitaciones SHALL únicamente recibir solicitudes HTTP, validar datos de entrada mediante esquemas Pydantic definidos en el paquete schemas, y delegar toda operación al Servicio_De_Habitaciones sin invocar directamente al Repositorio_De_Habitaciones ni acceder a la base de datos.
2. THE Servicio_De_Habitaciones SHALL contener toda la lógica de negocio, comunicarse exclusivamente con el Repositorio_De_Habitaciones para acceso a datos, y no manejar conceptos HTTP tales como códigos de estado, objetos Request o objetos Response.
3. THE Repositorio_De_Habitaciones SHALL ejecutar operaciones CRUD sobre la base de datos PostgreSQL mediante SQLAlchemy sin implementar reglas de negocio ni validaciones de dominio.
4. THE Sistema_De_Habitaciones SHALL respetar una dirección de dependencia estricta donde la capa API depende únicamente de Services, la capa Services depende únicamente de Repositories, y la capa Repositories depende únicamente de Models, sin dependencias inversas ni circulares entre capas.

### Requerimiento 8: Manejo de errores

**Historia de Usuario:** Como personal del hotel, quiero recibir mensajes de error claros y consistentes, para entender qué salió mal al realizar una operación.

#### Criterios de Aceptación

1. IF ocurre un error de conexión con la base de datos o una excepción no controlada en cualquier capa del sistema, THEN THE Sistema_De_Habitaciones SHALL retornar un código HTTP 500 con un mensaje genérico de error interno sin exponer detalles de la infraestructura tales como direcciones de servidor, trazas de pila o nombres de tablas.
2. THE API_De_Habitaciones SHALL retornar respuestas de error en formato JSON con los campos "detail" (cadena de texto describiendo el error) y "status_code" (código numérico HTTP correspondiente) para todas las operaciones que resulten en códigos HTTP 4xx o 5xx.
3. IF el Personal_Del_Hotel envía una solicitud con un formato de cuerpo inválido o campos que no cumplen las reglas de tipo o formato definidas en el esquema Pydantic, THEN THE API_De_Habitaciones SHALL retornar un código HTTP 422 con un mensaje en el campo "detail" que indique qué campos son inválidos y la razón del rechazo.
4. IF el Personal_Del_Hotel realiza una operación que viola una regla de negocio (como registrar un número de habitación duplicado o eliminar una habitación ocupada), THEN THE API_De_Habitaciones SHALL retornar un código HTTP 409 con un mensaje en el campo "detail" que indique la regla de negocio que fue violada.
5. IF el Personal_Del_Hotel solicita un recurso que no existe en el sistema, THEN THE API_De_Habitaciones SHALL retornar un código HTTP 404 con un mensaje en el campo "detail" indicando que el recurso no fue encontrado.

### Requerimiento 9: Autenticación y autorización

**Historia de Usuario:** Como administrador del hotel, quiero que las operaciones de gestión de habitaciones estén protegidas por autenticación y autorización, para que solo usuarios autorizados puedan modificar el catálogo de habitaciones.

#### Criterios de Aceptación

1. THE Middleware_De_Autenticación SHALL verificar la presencia y validez de un Token_JWT en el encabezado Authorization de cada solicitud dirigida a los endpoints del módulo de habitaciones.
2. IF una solicitud no incluye un Token_JWT o el token es inválido (expirado, malformado o con firma incorrecta), THEN THE API_De_Habitaciones SHALL rechazar la solicitud y retornar un código HTTP 401 con un mensaje en el campo "detail" indicando que la autenticación es requerida.
3. IF el usuario autenticado no posee el Rol_Administrador, THEN THE API_De_Habitaciones SHALL rechazar la solicitud y retornar un código HTTP 403 con un mensaje en el campo "detail" indicando que el usuario no tiene permisos suficientes para realizar la operación.
4. WHEN un usuario con Token_JWT válido y Rol_Administrador realiza una solicitud a cualquier endpoint del módulo de habitaciones, THE Middleware_De_Autenticación SHALL permitir que la solicitud continúe hacia la API_De_Habitaciones sin modificaciones.

### Requerimiento 10: Requerimientos no funcionales

**Historia de Usuario:** Como desarrollador, quiero que el módulo de habitaciones cumpla con estándares de observabilidad, documentación y rendimiento, para facilitar el diagnóstico de problemas, la integración con otros sistemas y garantizar una experiencia de usuario aceptable.

#### Criterios de Aceptación

1. WHEN una operación de creación, actualización o eliminación de una Habitación se ejecuta (exitosamente o con error), THE Sistema_De_Habitaciones SHALL registrar en el Registro_De_Operaciones un evento con los siguientes datos: marca temporal (timestamp), tipo de operación (create, update, delete), identificador de la habitación afectada y resultado de la operación (success o failure).
2. THE Registro_De_Operaciones SHALL excluir datos sensibles tales como tokens de autenticación, contraseñas o información personal de los usuarios en todos los registros generados.
3. THE API_De_Habitaciones SHALL generar documentación OpenAPI/Swagger de forma automática mediante FastAPI, accesible en las rutas /docs (interfaz Swagger UI) y /redoc (interfaz ReDoc).
4. WHEN una solicitud es recibida bajo condiciones normales de carga (una solicitud concurrente con una base de datos conteniendo hasta 1000 habitaciones), THE API_De_Habitaciones SHALL completar la respuesta en un tiempo máximo de 500 milisegundos.

### Requerimiento 11: Preparación para entornos cloud

**Historia de Usuario:** Como desarrollador, quiero que el módulo de habitaciones sea completamente stateless y configurable mediante variables de entorno, para poder desplegarlo en contenedores Docker y servicios cloud sin modificaciones al código.

#### Criterios de Aceptación

1. THE Sistema_De_Habitaciones SHALL operar de forma completamente stateless, sin almacenar estado de sesión en memoria ni utilizar almacenamiento local de archivos para datos operativos.
2. THE Sistema_De_Habitaciones SHALL obtener toda su configuración (URL de base de datos, claves secretas, puerto de escucha y demás parámetros) exclusivamente a partir de variables de entorno.
3. THE Sistema_De_Habitaciones SHALL ejecutarse de forma idéntica en un entorno de desarrollo local y en un contenedor Docker sin requerir modificaciones en el código fuente.
4. THE Sistema_De_Habitaciones SHALL operar sin depender de rutas específicas del sistema operativo ni del sistema de archivos local para datos de tiempo de ejecución.
