# Requirements Document

## Introduction

Este documento define los requerimientos para el módulo de administración de huéspedes del sistema StayBook. El módulo permite al Administrador gestionar el catálogo de huéspedes, incluyendo su registro, consulta, listado y actualización. Los datos de huéspedes se conservan de forma que puedan sustentar el futuro módulo de reservas e historial. Este spec cubre exclusivamente la gestión de huéspedes para un único hotel y no incluye funcionalidades de habitaciones, reservas, check-in ni check-out. Tampoco contempla la eliminación de huéspedes, ya que su información debe preservarse para el historial de reservas futuro.

## Glossary

- **Sistema_De_Huéspedes**: Módulo del sistema StayBook responsable de la administración de huéspedes del hotel.
- **API_De_Huéspedes**: Capa de presentación REST que recibe solicitudes HTTP y devuelve respuestas HTTP relacionadas con huéspedes.
- **Servicio_De_Huéspedes**: Capa de lógica de negocio que aplica reglas y validaciones sobre las operaciones de huéspedes.
- **Repositorio_De_Huéspedes**: Capa de acceso a datos que ejecuta operaciones sobre la tabla de huéspedes en PostgreSQL.
- **Huésped**: Entidad que representa a una persona registrada en el sistema con sus datos de contacto e identificación.
- **Administrador**: Usuario del sistema con Rol_Administrador que administra los huéspedes. Es el único actor contemplado en el MVP de StayBook.
- **Correo_Electrónico**: Dirección de correo electrónico del huésped, utilizada como dato de contacto único.
- **Documento_De_Identificación**: Combinación del tipo de identificación y el número de identificación que identifica de forma unívoca a un huésped.
- **Tipo_De_Identificación**: Valor que indica la clase de documento de identidad presentado por el huésped.
- **Número_De_Identificación**: Cadena que representa el número del documento de identidad del huésped.
- **Token_JWT**: Token de autenticación en formato JSON Web Token utilizado para verificar la identidad del usuario.
- **Rol_Administrador**: Rol del sistema que otorga permisos para realizar operaciones de gestión de huéspedes.
- **Dependencia_De_Autenticación**: Mecanismo de autenticación y autorización basado en dependencias de FastAPI (por ejemplo `get_current_admin_user`) ya existente en StayBook y reutilizado por este módulo para proteger los endpoints.
- **Registro_De_Operaciones**: Sistema de logging que registra las operaciones realizadas sobre los huéspedes con fines de auditoría.

## Entity Definition

### Huésped (Guest)

Entidad principal del módulo que representa a una persona registrada en el hotel.

| Atributo | Tipo de Dato | Obligatorio | Restricciones | Descripción |
|----------|-------------|-------------|---------------|-------------|
| id | integer | Sí (auto-generado) | Clave primaria, auto-incremental | Identificador único interno del huésped |
| first_name | string | Sí | Entre 1 y 100 caracteres, no vacío tras recortar espacios | Nombre(s) del huésped |
| last_name | string | Sí | Entre 1 y 100 caracteres, no vacío tras recortar espacios | Apellido(s) del huésped |
| email | string | Sí | Formato de correo válido, máximo 255 caracteres, único | Correo electrónico de contacto del huésped |
| phone | string | Sí | Entre 7 y 20 caracteres, admite dígitos, espacios y los símbolos `+`, `-`, `(`, `)` | Número de teléfono de contacto del huésped |
| identification_type | enum | Sí | Valores permitidos: "national_id", "passport", "driver_license", "other" | Tipo de documento de identidad presentado |
| identification_number | string | Sí | Entre 1 y 50 caracteres, no vacío tras recortar espacios | Número del documento de identidad |
| created_at | datetime | Sí (auto-gestionado) | Se asigna automáticamente al crear el registro | Fecha y hora de creación del registro |
| updated_at | datetime | Sí (auto-gestionado) | Se actualiza automáticamente en cada modificación | Fecha y hora de la última actualización del registro |

**Notas:**
- Los campos `id`, `created_at` y `updated_at` son gestionados automáticamente por el sistema y no son proporcionados por el usuario.
- El campo `email` debe ser único en toda la base de datos para evitar duplicidad de huéspedes.
- La combinación de `identification_type` y `identification_number` debe ser única en toda la base de datos, de modo que no existan dos huéspedes con el mismo documento de identidad.
- Los datos del huésped se conservan de forma permanente para sustentar el futuro historial de reservas; el módulo no contempla la eliminación de huéspedes en el MVP.

## Requirements

### Requerimiento 1: Registro de nuevos huéspedes

**Historia de Usuario:** Como Administrador, quiero registrar nuevos huéspedes en el sistema, para mantener un catálogo de personas que puedan asociarse a futuras reservas.

#### Criterios de Aceptación

1. WHEN el Administrador envía una solicitud de registro con datos válidos (nombre y apellido no vacíos de máximo 100 caracteres cada uno, correo electrónico con formato válido de máximo 255 caracteres, teléfono entre 7 y 20 caracteres, tipo de identificación con valor "national_id", "passport", "driver_license" u "other", y número de identificación no vacío de máximo 50 caracteres), THE Servicio_De_Huéspedes SHALL crear un nuevo Huésped y persistirlo en la base de datos.
2. IF el Administrador intenta registrar un huésped con un Correo_Electrónico que ya existe en la base de datos, THEN THE Servicio_De_Huéspedes SHALL rechazar la operación y THE API_De_Huéspedes SHALL retornar un error con código HTTP 409 indicando que el correo electrónico ya está registrado.
3. IF el Administrador intenta registrar un huésped con una combinación de Tipo_De_Identificación y Número_De_Identificación que ya existe en la base de datos, THEN THE Servicio_De_Huéspedes SHALL rechazar la operación y THE API_De_Huéspedes SHALL retornar un error con código HTTP 409 indicando que el documento de identificación ya está registrado.
4. IF el Administrador envía una solicitud de registro con campos obligatorios faltantes (nombre, apellido, correo, teléfono, tipo de identificación o número de identificación) o con valores fuera de los rangos permitidos, THEN THE API_De_Huéspedes SHALL retornar un error de validación con código HTTP 422 y una descripción de cada campo faltante o inválido.
5. WHEN el registro del Huésped se completa exitosamente, THE API_De_Huéspedes SHALL retornar un código HTTP 201 y los datos del Huésped creado incluyendo: id, nombre, apellido, correo, teléfono, tipo de identificación, número de identificación, fecha de creación y fecha de actualización.

### Requerimiento 2: Listado de huéspedes

**Historia de Usuario:** Como Administrador, quiero listar todos los huéspedes registrados, para tener visibilidad del catálogo completo de personas registradas en el hotel.

#### Criterios de Aceptación

1. WHEN el Administrador solicita el listado de huéspedes, THE Sistema_De_Huéspedes SHALL retornar todos los huéspedes registrados con sus atributos completos (id, nombre, apellido, correo, teléfono, tipo de identificación, número de identificación, fecha de creación y fecha de actualización).
2. IF no existen huéspedes registrados en el sistema, THEN THE API_De_Huéspedes SHALL retornar una lista vacía con código HTTP 200.
3. THE API_De_Huéspedes SHALL retornar un código HTTP 200 junto con la lista de huéspedes en formato JSON.

### Requerimiento 3: Obtener información de un huésped específico

**Historia de Usuario:** Como Administrador, quiero obtener la información detallada de un huésped específico, para consultar sus datos de contacto e identificación actuales.

#### Criterios de Aceptación

1. WHEN el Administrador solicita la información de un Huésped existente por su identificador único (id), THE Sistema_De_Huéspedes SHALL retornar los atributos del Huésped: id, first_name, last_name, email, phone, identification_type, identification_number, created_at y updated_at.
2. IF el Administrador solicita la información de un huésped cuyo identificador no existe en la base de datos, THEN THE API_De_Huéspedes SHALL retornar un error con código HTTP 404 y un mensaje indicando que el huésped no fue encontrado.
3. WHEN la consulta de un Huésped es exitosa, THE API_De_Huéspedes SHALL retornar un código HTTP 200 junto con los atributos completos del Huésped en formato JSON.
4. IF el Administrador envía un identificador con formato inválido (no entero positivo), THEN THE API_De_Huéspedes SHALL retornar un error de validación con código HTTP 422 indicando que el identificador debe ser un número entero positivo.

### Requerimiento 4: Actualización de información de huéspedes

**Historia de Usuario:** Como Administrador, quiero actualizar la información de un huésped existente, para reflejar cambios en sus datos de contacto o de identificación.

#### Criterios de Aceptación

1. WHEN el Administrador envía una solicitud de actualización parcial o completa con datos válidos para un Huésped existente, THE Servicio_De_Huéspedes SHALL modificar únicamente los atributos incluidos en la solicitud, preservar los atributos no incluidos sin cambios y persistir los cambios en la base de datos.
2. IF el Administrador intenta actualizar un huésped que no existe, THEN THE API_De_Huéspedes SHALL retornar un error con código HTTP 404 indicando que el huésped no fue encontrado.
3. IF el Administrador envía datos de actualización que violan las reglas de validación (nombre o apellido vacíos o mayores a 100 caracteres, correo con formato inválido o mayor a 255 caracteres, teléfono fuera del rango de 7 a 20 caracteres, tipo de identificación distinto de "national_id", "passport", "driver_license" u "other", o número de identificación vacío o mayor a 50 caracteres), THEN THE API_De_Huéspedes SHALL retornar un error de validación con código HTTP 422 y una descripción de los campos inválidos.
4. IF el Administrador intenta cambiar el Correo_Electrónico a uno que ya existe en otro huésped, THEN THE Servicio_De_Huéspedes SHALL rechazar la operación y THE API_De_Huéspedes SHALL retornar un error con código HTTP 409 indicando duplicidad de correo electrónico.
5. IF el Administrador intenta cambiar el Documento_De_Identificación a una combinación de tipo y número que ya existe en otro huésped, THEN THE Servicio_De_Huéspedes SHALL rechazar la operación y THE API_De_Huéspedes SHALL retornar un error con código HTTP 409 indicando duplicidad de documento de identificación.
6. WHEN la actualización de un Huésped es exitosa, THE API_De_Huéspedes SHALL retornar un código HTTP 200 y todos los atributos actualizados del Huésped en formato JSON.

### Requerimiento 5: Preservación de datos para el historial de reservas

**Historia de Usuario:** Como Administrador, quiero que la información de los huéspedes se conserve de forma consistente y estable, para que pueda asociarse a reservas y sustentar el historial en módulos futuros.

#### Criterios de Aceptación

1. THE Sistema_De_Huéspedes SHALL conservar de forma permanente cada Huésped registrado y no ofrecer una operación de eliminación en el alcance del MVP.
2. THE Sistema_De_Huéspedes SHALL asignar a cada Huésped un identificador único e inmutable (id) que no cambie durante toda la vida del registro, de modo que pueda ser referenciado de forma estable por futuros módulos de reservas.
3. WHEN un Huésped es actualizado, THE Sistema_De_Huéspedes SHALL preservar el identificador (id) y la fecha de creación (created_at) originales sin modificarlos.
4. THE Sistema_De_Huéspedes SHALL garantizar que cada Huésped registrado mantenga en todo momento los datos mínimos necesarios para su identificación (nombre, apellido, correo, teléfono, tipo y número de identificación) sin permitir que ninguno de estos campos obligatorios quede vacío tras una operación de creación o actualización.

### Requerimiento 6: Separación de responsabilidades por capas

**Historia de Usuario:** Como desarrollador, quiero que el módulo respete la arquitectura por capas, para mantener el código organizado y facilitar el mantenimiento.

#### Criterios de Aceptación

1. THE API_De_Huéspedes SHALL únicamente recibir solicitudes HTTP, validar datos de entrada mediante esquemas Pydantic definidos en el paquete schemas, y delegar toda operación al Servicio_De_Huéspedes sin invocar directamente al Repositorio_De_Huéspedes ni acceder a la base de datos.
2. THE Servicio_De_Huéspedes SHALL contener toda la lógica de negocio, comunicarse exclusivamente con el Repositorio_De_Huéspedes para acceso a datos, y no manejar conceptos HTTP tales como códigos de estado, objetos Request o objetos Response.
3. THE Repositorio_De_Huéspedes SHALL ejecutar operaciones sobre la base de datos PostgreSQL mediante SQLAlchemy sin implementar reglas de negocio ni validaciones de dominio.
4. THE Sistema_De_Huéspedes SHALL respetar una dirección de dependencia estricta donde la capa API depende únicamente de Services, la capa Services depende únicamente de Repositories, y la capa Repositories depende únicamente de Models, sin dependencias inversas ni circulares entre capas.

### Requerimiento 7: Manejo de errores

**Historia de Usuario:** Como Administrador, quiero recibir mensajes de error claros y consistentes, para entender qué salió mal al realizar una operación.

#### Criterios de Aceptación

1. IF ocurre un error de conexión con la base de datos o una excepción no controlada en cualquier capa del sistema, THEN THE Sistema_De_Huéspedes SHALL retornar un código HTTP 500 con un mensaje genérico de error interno sin exponer detalles de la infraestructura tales como direcciones de servidor, trazas de pila o nombres de tablas.
2. THE API_De_Huéspedes SHALL reutilizar el manejo de errores existente en StayBook (los handlers globales `app_exception_handler` y `generic_exception_handler` y las excepciones de dominio que heredan de `AppException`), manteniendo el mismo formato de respuesta de error ya utilizado por el módulo de habitaciones, sin definir un esquema de error nuevo o distinto para huéspedes.
3. IF el Administrador envía una solicitud con un formato de cuerpo inválido o campos que no cumplen las reglas de tipo o formato definidas en el esquema Pydantic, THEN THE API_De_Huéspedes SHALL retornar un código HTTP 422 con el detalle de validación generado por FastAPI que indique qué campos son inválidos y la razón del rechazo.
4. IF el Administrador realiza una operación que viola una regla de negocio (como registrar un correo electrónico duplicado o un documento de identificación duplicado), THEN THE API_De_Huéspedes SHALL retornar un código HTTP 409 con un mensaje que indique la regla de negocio que fue violada, empleando el mismo mecanismo de excepciones de dominio ya existente.
5. IF el Administrador solicita un recurso que no existe en el sistema, THEN THE API_De_Huéspedes SHALL retornar un código HTTP 404 con un mensaje indicando que el recurso no fue encontrado.

### Requerimiento 8: Autenticación y autorización

**Historia de Usuario:** Como Administrador, quiero que las operaciones de gestión de huéspedes estén protegidas por autenticación y autorización, para que solo usuarios autorizados puedan gestionar la información de los huéspedes.

#### Criterios de Aceptación

1. THE API_De_Huéspedes SHALL proteger todos sus endpoints reutilizando la Dependencia_De_Autenticación existente de StayBook (la dependencia de FastAPI `get_current_admin_user`), sin introducir ni requerir un nuevo middleware de autenticación.
2. IF una solicitud no incluye un Token_JWT o el token es inválido (expirado, malformado o con firma incorrecta), THEN la Dependencia_De_Autenticación SHALL rechazar la solicitud y THE API_De_Huéspedes SHALL retornar un código HTTP 401, con el mismo comportamiento que el módulo de habitaciones.
3. IF el usuario autenticado no posee el Rol_Administrador, THEN la Dependencia_De_Autenticación SHALL rechazar la solicitud y THE API_De_Huéspedes SHALL retornar un código HTTP 403, con el mismo comportamiento que el módulo de habitaciones.
4. WHEN un usuario con Token_JWT válido y Rol_Administrador realiza una solicitud a cualquier endpoint del módulo de huéspedes, THE API_De_Huéspedes SHALL permitir que la solicitud continúe hacia la lógica del módulo sin modificaciones.

### Requerimiento 9: Requerimientos no funcionales

**Historia de Usuario:** Como Administrador, quiero que el módulo de huéspedes cumpla con estándares de observabilidad y documentación, para facilitar el diagnóstico de problemas y la integración con otros sistemas.

#### Criterios de Aceptación

1. WHEN una operación de creación o actualización de un Huésped se ejecuta (exitosamente o con error), THE Sistema_De_Huéspedes SHALL registrar en el Registro_De_Operaciones un evento con los siguientes datos: marca temporal (timestamp), tipo de operación (create, update), identificador del huésped afectado y resultado de la operación (success o failure).
2. THE Registro_De_Operaciones SHALL excluir datos sensibles tales como tokens de autenticación, contraseñas o información personal de contacto del huésped (correo, teléfono o número de identificación) en todos los registros generados.
3. THE API_De_Huéspedes SHALL generar documentación OpenAPI/Swagger de forma automática mediante FastAPI, accesible en las rutas /docs (interfaz Swagger UI) y /redoc (interfaz ReDoc).
