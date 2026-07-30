## El stack para StayBook será:

Lenguaje:Python 3.13                      --- Ya tengo bases y FastAPI funciona muy bien con Python.
Framework:FastAPI                         --- Excelente para APIs REST, documentación automática y buena integración con AWS.
Base de datos:PostgreSQL                  --- Ideal para un sistema con muchas relaciones (habitaciones, clientes y reservas).
ORM:SQLAlchemy	                          --- El estándar más utilizado con FastAPI.
Migraciones:Alembic                       --- Permite versionar el esquema de la base de datos.
API REST                                  --- Suficiente para el alcance del proyecto.
Contenedores:Docker	                  --- Fundamental para desplegar en AWS.
Control de versiones:Git                  --- Imprescindible para cualquier proyecto profesional.
Configuración:Variables de entorno (.env) --- Evita credenciales en el código y facilita múltiples entornos.
Documentación OpenAPI / Swagger	          --- FastAPI la genera automáticamente.

## Comentarios:
- La API Rest debe de ser statless.
- Toda la configuración del sistema deberá obtenerse mediante variables de entorno. No se deberán almacenar credenciales 
  o configuraciones sensibles dentro del código fuente.
- La aplicación deberá ejecutarse de forma consistente 
  tanto en un entorno local como mediante contenedores Docker, manteniendo el mismo comportamiento entre ambos ambientes.
- El código deberá seguir PEP 8.

## Arquitectura 

- Arquitectura por capas (Controllers, Services y Repositories)

