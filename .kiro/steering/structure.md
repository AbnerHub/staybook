# Structure Steering

## Objetivo

StayBook seguirá una arquitectura por capas (Layered Architecture) para mantener una clara separación de responsabilidades, facilitar el mantenimiento del código y permitir que el proyecto crezca de forma organizada conforme se agreguen nuevas funcionalidades.

La estructura deberá favorecer la reutilización del código, la escalabilidad y una futura implementación en entornos Cloud utilizando contenedores Docker y servicios de AWS.

---

# Arquitectura

El proyecto utilizará una arquitectura por capas con las siguientes responsabilidades:

Presentation Layer (API)

Business Layer (Services)

Data Access Layer (Repositories)

Persistence Layer (Database)

Domain Layer (Models & Schemas)

Core Layer (Configuración y utilidades)

Cada capa tendrá una responsabilidad específica y no deberá invadir las responsabilidades de otra.

---

# Organización del proyecto

## api/

Contendrá todos los endpoints REST de la aplicación.

Responsabilidades:

- Recibir solicitudes HTTP.
- Validar parámetros básicos.
- Llamar al Service correspondiente.
- Devolver respuestas HTTP.

No deberá contener lógica de negocio ni consultas a la base de datos.

---

## services/

Contendrá toda la lógica de negocio del sistema.

Responsabilidades:

- Aplicar reglas de negocio.
- Validar procesos.
- Coordinar operaciones.
- Comunicarse con los repositorios.

Toda decisión del negocio deberá implementarse en esta capa.

---

## repositories/

Será la capa encargada del acceso a datos.

Responsabilidades:

- Consultar PostgreSQL.
- Crear registros.
- Actualizar registros.
- Eliminar registros.

No deberá contener reglas de negocio.

---

## models/

Contendrá los modelos ORM utilizando SQLAlchemy.

Cada modelo representará una tabla de la base de datos.

---

## schemas/

Contendrá los modelos Pydantic utilizados para:

- Request Body
- Response Body
- Validaciones
- Serialización de datos

---

## db/

Contendrá todo lo relacionado con la persistencia.

Ejemplos:

- conexión a PostgreSQL
- Session Factory
- configuración SQLAlchemy
- Alembic
- migraciones

---

## core/

Contendrá componentes compartidos por toda la aplicación.

Ejemplos:

- configuración
- variables de entorno
- utilidades
- constantes
- manejo de excepciones
- logging

---

## tests/

Contendrá las pruebas unitarias y de integración del proyecto.

Las pruebas deberán seguir la misma estructura de la aplicación para facilitar su mantenimiento.

---

# Reglas de arquitectura

Las siguientes reglas deberán respetarse durante todo el desarrollo.

- Los Routers nunca accederán directamente a la base de datos.

- Los Services nunca ejecutarán consultas SQL.

- Los Repositories nunca implementarán reglas de negocio.

- Los Models solo representarán entidades de la base de datos.

- Los Schemas únicamente serán utilizados para la validación y serialización de datos.

- Ninguna credencial deberá almacenarse en el código fuente.

- Toda la configuración deberá obtenerse mediante variables de entorno.

- Cada módulo deberá tener una única responsabilidad.

- Se evitará la duplicación de código.

- La lógica de negocio deberá permanecer desacoplada de la infraestructura.

---

# Organización de funcionalidades

Las nuevas funcionalidades deberán integrarse respetando la arquitectura definida.

Entre ellas:

- Habitaciones
- Clientes
- Reservas
- Check-in
- Check-out
- Historial
- Reportes

La incorporación de nuevos módulos no deberá requerir modificar la estructura principal del proyecto.

---

# Preparación para Cloud

La estructura del proyecto deberá facilitar un futuro despliegue en AWS.

Por esta razón:

- La aplicación será Stateless.

- La configuración dependerá exclusivamente de variables de entorno.

- El proyecto deberá ejecutarse tanto localmente como mediante Docker sin modificar el código.

- El almacenamiento persistente se delegará a PostgreSQL.

- La aplicación no dependerá de rutas específicas del sistema operativo.

- El código deberá estar preparado para ejecutarse posteriormente en servicios como Amazon ECS, AWS Fargate o AWS Lambda, realizando únicamente cambios en la infraestructura y no en la lógica del negocio.

---

# Buenas prácticas

Durante todo el desarrollo deberán respetarse las siguientes prácticas:

- Código limpio y legible.

- Principio de responsabilidad única.

- Separación de responsabilidades.

- Reutilización de componentes.

- Nombres descriptivos para archivos, clases y funciones.

- Documentación automática mediante OpenAPI.

- Cumplimiento del estándar PEP 8.

- El proyecto deberá ser fácilmente mantenible y escalable.