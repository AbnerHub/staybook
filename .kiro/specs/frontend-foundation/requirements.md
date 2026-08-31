# Requirements Document

## Introduction

Este documento define los requerimientos para la **base (foundation) del frontend** de StayBook: una aplicación web administrativa para un único hotel, construida con React + Vite (JavaScript) y React Router, que consume la API REST del backend FastAPI existente.

El alcance de este spec es **exclusivamente la base del frontend**: inicializar el proyecto, definir su estructura, configurar el ruteo del lado del cliente, crear el layout principal y la navegación, crear páginas placeholder, establecer una capa centralizada de cliente/servicios de API, configurar la URL base del backend por variables de entorno, y definir patrones genéricos de carga y manejo de errores. El proyecto debe quedar **preparado** para autenticación JWT, pero la autenticación **no se implementa** en este spec.

**Fuera de alcance** (explícito): implementación de funcionalidad de negocio (CRUD de habitaciones, huéspedes, reservas, check-in/check-out, disponibilidad, historial), implementación de login/JWT, duplicación de reglas de negocio del backend, archivos Docker, AWS, Terraform, CI/CD, rediseño del backend, y librerías de manejo de estado global (Redux, Zustand, etc.) o frameworks pesados innecesarios.

## Contexto técnico

- **Ubicación:** el proyecto frontend vive en el directorio `/frontend` dentro del repositorio StayBook.
- **Stack:** React + Vite + JavaScript, React Router para ruteo del lado del cliente, `fetch` (o un wrapper ligero) para la integración REST. Se evitan librerías de estado global y frameworks innecesarios.
- **Backend:** FastAPI existente, corriendo localmente (por defecto `http://127.0.0.1:8000`), que expone endpoints bajo `/api/v1/...` y protege las operaciones con JWT (rol admin). El frontend consumirá esa API sin reimplementar sus reglas.
- **Actor:** el único usuario es el Administrador del hotel (aplicación administrativa de un solo hotel).

## Glossary

- **Aplicación_Frontend**: La aplicación web administrativa de StayBook construida con React + Vite.
- **Administrador**: Usuario final de la aplicación; personal administrativo del hotel.
- **Cliente_De_API**: Capa centralizada de servicios que encapsula la comunicación HTTP con el backend FastAPI.
- **URL_Base_Del_Backend**: Dirección base configurable del backend (por variable de entorno) sobre la cual se construyen las llamadas a `/api/v1/...`.
- **Layout_Principal**: Estructura visual común (encabezado, barra lateral/navegación y área de contenido) compartida por las páginas autenticadas.
- **Navegación**: Barra lateral (sidebar) que permite moverse entre las secciones de la aplicación.
- **Página_Placeholder**: Página con estructura y título mínimos, sin lógica de negocio, usada como marcador para una sección futura.
- **Estado_De_Carga**: Indicación visual genérica mientras una operación asíncrona está en progreso.
- **Estado_De_Error_De_API**: Manejo y presentación genéricos de errores devueltos por el backend o de fallos de red.
- **Ruta_Protegida**: Ruta que en el futuro requerirá autenticación; en este spec queda preparada estructuralmente pero sin forzar autenticación.
- **Variable_De_Entorno_De_Vite**: Variable de configuración expuesta a la app mediante el mecanismo de entorno de Vite (prefijo `VITE_`).

## Requirements

### Requerimiento 1: Inicialización del proyecto React + Vite

**Historia de Usuario:** Como desarrollador, quiero inicializar el proyecto frontend con React + Vite en `/frontend`, para tener una base moderna, rápida y mantenible sobre la cual construir la aplicación administrativa.

#### Criterios de Aceptación

1. THE Aplicación_Frontend SHALL residir en el directorio `/frontend` dentro del repositorio StayBook, sin mezclarse con el código del backend.
2. THE Aplicación_Frontend SHALL usar React + Vite con JavaScript (no TypeScript), consistente con el stack acordado.
3. THE Aplicación_Frontend SHALL declarar sus dependencias (React, React Router, Vite y utilidades mínimas) en un `package.json`, sin incluir librerías de manejo de estado global ni frameworks de UI pesados.
4. WHEN el desarrollador ejecuta el script de desarrollo de Vite, THE Aplicación_Frontend SHALL levantar un servidor de desarrollo local y servir la aplicación en un puerto local.
5. WHEN el desarrollador ejecuta el script de build de Vite, THE Aplicación_Frontend SHALL generar un build de producción estático sin errores.
6. THE Aplicación_Frontend SHALL incluir un `.gitignore` apropiado para un proyecto Node/Vite (por ejemplo `node_modules`, artefactos de build y archivos de entorno locales).

### Requerimiento 2: Estructura de proyecto mantenible

**Historia de Usuario:** Como desarrollador, quiero una estructura de carpetas clara y mantenible, para que el proyecto escale de forma ordenada al agregar las funcionalidades futuras.

#### Criterios de Aceptación

1. THE Aplicación_Frontend SHALL organizar el código en carpetas con responsabilidades separadas, incluyendo al menos: páginas (vistas de ruta), componentes reutilizables, capa de servicios/cliente de API, configuración, y layout/navegación.
2. THE Aplicación_Frontend SHALL ubicar la capa de comunicación con el backend en una carpeta de servicios dedicada, separada de los componentes de presentación.
3. THE Aplicación_Frontend SHALL mantener la configuración (URL base, constantes) separada de la lógica de presentación.
4. THE estructura SHALL permitir agregar nuevas secciones (páginas, servicios) sin modificar la organización principal del proyecto.
5. THE Aplicación_Frontend SHALL favorecer componentes reutilizables y patrones simples de React (componentes funcionales y hooks), evitando complejidad innecesaria.

### Requerimiento 3: Ruteo del lado del cliente

**Historia de Usuario:** Como Administrador, quiero navegar entre las distintas secciones mediante URLs, para acceder directamente a cada área de la aplicación.

#### Criterios de Aceptación

1. THE Aplicación_Frontend SHALL usar React Router para el ruteo del lado del cliente.
2. THE Aplicación_Frontend SHALL definir rutas para las secciones: Login, Dashboard, Rooms, Guests, Reservations, Availability e History.
3. WHEN el Administrador navega a la ruta de una sección, THE Aplicación_Frontend SHALL renderizar la Página_Placeholder correspondiente dentro del Layout_Principal (excepto Login, que se renderiza fuera del layout con navegación autenticada).
4. WHEN el Administrador accede a la ruta raíz (`/`), THE Aplicación_Frontend SHALL redirigir o mostrar una ruta por defecto definida (por ejemplo el Dashboard) de forma consistente.
5. IF el Administrador navega a una ruta inexistente, THEN THE Aplicación_Frontend SHALL mostrar una página "no encontrada" (404) genérica sin romper la aplicación.
6. THE Aplicación_Frontend SHALL estructurar el ruteo de modo que las rutas de las secciones administrativas puedan convertirse en Rutas_Protegidas cuando se implemente la autenticación, sin requerir una reestructuración del ruteo.

### Requerimiento 4: Layout principal y navegación

**Historia de Usuario:** Como Administrador, quiero un layout consistente con una barra lateral de navegación, para moverme entre secciones de forma predecible.

#### Criterios de Aceptación

1. THE Aplicación_Frontend SHALL proporcionar un Layout_Principal común que incluya al menos: un área de encabezado, una Navegación lateral (sidebar) y un área de contenido donde se renderizan las páginas.
2. THE Navegación SHALL incluir enlaces a: Dashboard, Rooms, Guests, Reservations, Availability e History.
3. WHEN el Administrador selecciona un enlace de la Navegación, THE Aplicación_Frontend SHALL navegar a la ruta correspondiente y renderizar su página dentro del área de contenido, sin recargar la página completa.
4. WHEN una sección está activa, THE Navegación SHALL indicar visualmente el enlace activo correspondiente a la ruta actual.
5. THE Layout_Principal SHALL reservar un espacio para acciones de sesión de usuario (por ejemplo un botón de "cerrar sesión" en el futuro) sin implementar su lógica en este spec.
6. THE página de Login SHALL renderizarse fuera del Layout_Principal (sin sidebar de navegación administrativa).

### Requerimiento 5: Páginas placeholder

**Historia de Usuario:** Como desarrollador, quiero páginas placeholder para cada sección, para tener puntos de anclaje claros donde construir la funcionalidad futura sin implementar lógica de negocio ahora.

#### Criterios de Aceptación

1. THE Aplicación_Frontend SHALL crear Páginas_Placeholder para: Login, Dashboard, Rooms, Guests, Reservations, Availability e History.
2. THE cada Página_Placeholder SHALL mostrar al menos un título identificable de la sección y una indicación de que la funcionalidad está pendiente.
3. THE Páginas_Placeholder SHALL NOT contener lógica de negocio, llamadas de datos reales de negocio, ni reglas replicadas del backend.
4. THE Páginas_Placeholder SHALL ser componentes funcionales de React simples y reutilizables en su patrón.

### Requerimiento 6: Capa centralizada de cliente/servicios de API

**Historia de Usuario:** Como desarrollador, quiero una capa centralizada de cliente de API, para que todas las llamadas al backend pasen por un único punto configurable y consistente.

#### Criterios de Aceptación

1. THE Aplicación_Frontend SHALL proporcionar un Cliente_De_API centralizado que encapsule la construcción de solicitudes HTTP hacia el backend (método, ruta, encabezados, cuerpo y parsing de respuesta).
2. THE Cliente_De_API SHALL construir las URLs de las solicitudes a partir de la URL_Base_Del_Backend configurada, sin URLs de backend embebidas (hardcodeadas) en los componentes.
3. THE Cliente_De_API SHALL centralizar el manejo de encabezados comunes (por ejemplo `Content-Type: application/json`) y estar preparado para adjuntar un encabezado `Authorization: Bearer <token>` cuando la autenticación se implemente en el futuro, sin implementar la obtención del token en este spec.
4. THE Cliente_De_API SHALL exponer una forma consistente de invocar operaciones GET/POST/PATCH y de interpretar respuestas JSON y códigos de estado HTTP.
5. THE componentes de presentación SHALL consumir el backend únicamente a través del Cliente_De_API, sin usar `fetch` directamente en los componentes.
6. THE Cliente_De_API SHALL NOT duplicar ni reimplementar reglas de negocio del backend; se limita a transportar solicitudes y respuestas.

### Requerimiento 7: Configuración de la URL base del backend por entorno

**Historia de Usuario:** Como desarrollador, quiero configurar la URL base del backend mediante variables de entorno, para poder apuntar a distintos entornos sin modificar el código.

#### Criterios de Aceptación

1. THE Aplicación_Frontend SHALL obtener la URL_Base_Del_Backend desde una Variable_De_Entorno_De_Vite (con prefijo `VITE_`, por ejemplo `VITE_API_BASE_URL`).
2. THE Aplicación_Frontend SHALL proporcionar un archivo de ejemplo de entorno (por ejemplo `.env.example`) que documente las variables requeridas y sus valores por defecto para desarrollo local.
3. IF la Variable_De_Entorno_De_Vite de la URL base no está definida, THEN THE Aplicación_Frontend SHALL usar un valor por defecto razonable para desarrollo local (por ejemplo `http://127.0.0.1:8000`) de forma explícita y documentada.
4. THE Aplicación_Frontend SHALL NOT almacenar secretos ni credenciales en el código fuente ni en archivos de entorno versionados; los archivos de entorno locales deben quedar ignorados por Git.
5. THE configuración de entorno SHALL estar centralizada, de modo que la lectura de la URL base ocurra en un único módulo de configuración y no dispersa por los componentes.

### Requerimiento 8: Patrones genéricos de carga y manejo de errores

**Historia de Usuario:** Como Administrador, quiero indicaciones claras de carga y de error, para entender el estado de las operaciones al comunicarse con el backend.

#### Criterios de Aceptación

1. THE Aplicación_Frontend SHALL definir un patrón genérico y reutilizable de Estado_De_Carga para indicar visualmente cuando una operación asíncrona está en progreso.
2. THE Aplicación_Frontend SHALL definir un patrón genérico y reutilizable de Estado_De_Error_De_API para presentar de forma legible los errores devueltos por el backend o los fallos de red.
3. WHEN el backend responde con un código de error (4xx o 5xx), THE Cliente_De_API SHALL exponer esa condición de error de forma que la capa de presentación pueda mostrar el Estado_De_Error_De_API sin exponer trazas internas.
4. WHEN ocurre un fallo de red o el backend no está disponible, THE Aplicación_Frontend SHALL mostrar un mensaje de error genérico y no romper la aplicación (sin pantallas en blanco).
5. THE patrones de carga y error SHALL ser reutilizables entre secciones, sin duplicar su lógica en cada página.
6. THE manejo de errores del frontend SHALL presentar mensajes orientados al usuario y NO asumir ni replicar las reglas de validación del backend; se limita a mostrar lo que el backend informa.

### Requerimiento 9: Preparación para autenticación JWT (sin implementarla)

**Historia de Usuario:** Como desarrollador, quiero dejar el proyecto preparado para autenticación JWT, para poder implementar el login más adelante sin reestructurar la base.

#### Criterios de Aceptación

1. THE Aplicación_Frontend SHALL estructurar el ruteo y el layout de modo que las secciones administrativas puedan protegerse mediante un mecanismo de Ruta_Protegida cuando se implemente la autenticación.
2. THE Cliente_De_API SHALL contemplar un punto único donde, en el futuro, se adjunte el encabezado `Authorization: Bearer <token>` a las solicitudes.
3. THE Aplicación_Frontend SHALL incluir una página de Login como placeholder, sin implementar el flujo de autenticación, la obtención de token, ni el almacenamiento del token en este spec.
4. THE Aplicación_Frontend SHALL NOT implementar validación de credenciales, emisión, almacenamiento ni renovación de tokens JWT en este spec.
5. THE preparación de autenticación SHALL NOT bloquear el acceso a las páginas placeholder durante esta fase de foundation (las rutas permanecen accesibles para poder validar la base).

### Requerimiento 10: Comunicación con el backend local y expectativas de CORS

**Historia de Usuario:** Como desarrollador, quiero que el frontend pueda comunicarse con el backend FastAPI corriendo localmente, para validar de extremo a extremo que la base funciona.

#### Criterios de Aceptación

1. WHEN el backend FastAPI está corriendo localmente y la URL_Base_Del_Backend apunta a él, THE Aplicación_Frontend SHALL poder realizar al menos una solicitud HTTP de verificación de conectividad al backend a través del Cliente_De_API.
2. THE spec SHALL documentar la expectativa de CORS del backend: dado que el servidor de desarrollo de Vite corre en un origen distinto (por ejemplo `http://localhost:5173`) al del backend (por ejemplo `http://127.0.0.1:8000`), el backend deberá permitir solicitudes CORS desde el origen del frontend de desarrollo para que las llamadas del navegador tengan éxito.
3. THE documentación de CORS SHALL indicar que se requiere permitir los métodos (GET, POST, PATCH), los encabezados relevantes (incluido `Authorization` para el futuro) y el origen del frontend de desarrollo, sin especificar la implementación del backend (que queda fuera de alcance de este spec).
4. IF el backend no tiene CORS habilitado para el origen del frontend, THEN el spec SHALL reconocer que las llamadas del navegador fallarán por política de CORS y que habilitar CORS es un prerrequisito de integración (a resolver en el backend, no reimplementando reglas en el frontend).
5. THE Aplicación_Frontend SHALL NOT intentar eludir CORS mediante técnicas inseguras; se asume la configuración correcta de CORS en el backend o el uso del proxy de desarrollo de Vite como alternativa documentada.

### Requerimiento 11: Usabilidad básica y diseño responsivo

**Historia de Usuario:** Como Administrador, quiero una interfaz básica usable y razonablemente responsiva, para operar la aplicación cómodamente en pantallas de escritorio.

#### Criterios de Aceptación

1. THE Aplicación_Frontend SHALL presentar un layout legible y navegable en resoluciones de escritorio típicas (prioridad de la aplicación administrativa).
2. THE Layout_Principal SHALL comportarse de forma razonable en anchos de pantalla reducidos (por ejemplo, la navegación no debe romper el contenido), con un enfoque de responsividad básica apropiada para un MVP.
3. THE Aplicación_Frontend SHALL mantener una apariencia consistente entre secciones mediante estilos compartidos, sin introducir una librería de UI pesada.
4. THE Navegación SHALL permitir identificar claramente la sección actual y las secciones disponibles.
5. THE Aplicación_Frontend SHALL evitar pantallas en blanco: cada ruta válida renderiza al menos su Página_Placeholder con contenido identificable.

### Requerimiento 12: Restricciones de alcance de la foundation

**Historia de Usuario:** Como responsable del proyecto, quiero que la foundation se mantenga acotada, para no adelantar funcionalidad ni introducir complejidad prematura.

#### Criterios de Aceptación

1. THE Aplicación_Frontend SHALL NOT implementar funcionalidad de negocio (CRUD de habitaciones, huéspedes, reservas; check-in/check-out; disponibilidad real; historial real) en este spec.
2. THE Aplicación_Frontend SHALL NOT duplicar ni reimplementar reglas de negocio del backend (validaciones de fechas, solapamiento, cálculo de precios, transiciones de estado, etc.).
3. THE Aplicación_Frontend SHALL NOT incluir archivos Docker, ni configuración de AWS, Terraform o CI/CD.
4. THE Aplicación_Frontend SHALL NOT implementar el flujo de autenticación/JWT.
5. THE Aplicación_Frontend SHALL NOT introducir librerías de manejo de estado global ni frameworks innecesarios; se prefieren patrones simples de React y componentes reutilizables.
6. THE trabajo de este spec SHALL NOT requerir cambios en el backend, salvo la expectativa documentada de habilitar CORS para el origen del frontend de desarrollo (a decidir/implementar por separado en el backend).
