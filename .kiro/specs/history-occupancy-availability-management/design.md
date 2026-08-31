# Design Document: History / Occupancy / Availability Management

## Overview

Módulo **de solo lectura** que expone consultas de ocupación actual, habitaciones ocupadas, disponibilidad por rango de fechas e historial de reservas con filtros. No introduce escrituras, tablas nuevas ni una segunda fuente de verdad: todas las respuestas se derivan de las tablas existentes `rooms`, `guests` y `reservations`.

Reutiliza la arquitectura por capas existente:
- **API Layer** (FastAPI Router) → GET endpoints, valida query params con Pydantic, delega al Service.
- **Service Layer** → lógica de consulta/agregación, aplica las reglas de ocupación y disponibilidad.
- **Repository Layer** → reutiliza `RoomRepository` y añade métodos de consulta de solo lectura a `ReservationRepository` (y, si conviene, un `RoomRepository` de conteo) — sin reglas de negocio.
- **Core Layer** → `get_current_admin_user`, `AppException` + handlers, config/sesión (reutilizados).

### Conceptos clave (dos nociones distintas, Req 1 / 3 / 10)

| Concepto | Significado | Fuente de verdad | Regla |
|----------|-------------|------------------|-------|
| **Ocupación actual** | Estado operativo "ahora" | `Room.status` (mantenido por check-in/check-out) | Ocupada ⇔ `Room.status == OCUPADA` (equivale a tener una reserva `checked_in`) |
| **Disponibilidad por rango** | Proyección para un `[desde, hasta)` futuro | Reservas + estado de habitación | Disponible ⇔ `Room.status != MANTENIMIENTO` **AND** no existe reserva activa solapada |

**Regla de disponibilidad (exacta, aprobada):**

```
room disponible_para_rango(desde, hasta) ⇔
    room.status != MANTENIMIENTO
    AND NOT EXISTS reserva R con:
        R.room_id == room.id
        AND R.status IN (confirmed, checked_in)
        AND R.check_in_date < hasta
        AND R.check_out_date > desde     # intervalo semiabierto [check_in, check_out)
```

Notas críticas de diseño (según restricciones):
- **No** se exige `room.status == DISPONIBLE` para la disponibilidad futura: una habitación puede estar `ocupada` hoy y quedar libre para un rango futuro. Solo `MANTENIMIENTO` excluye incondicionalmente.
- `cancelled` y `checked_out` **no** bloquean (no son activas).
- La condición de solapamiento es idéntica a la de `ReservationRepository.get_active_overlapping` ya aprobada (semiabierta).

## Architecture

```mermaid
graph TD
    Client[Cliente HTTP] --> Auth[get_current_admin_user]
    Auth --> Router[QueryRouter<br>/api/v1/*]
    Router --> Schemas[Pydantic query params + response models]
    Router --> Service[QueryService]
    Service --> RoomRepo[RoomRepository<br>reutilizado + conteos]
    Service --> ResRepo[ReservationRepository<br>+ métodos de consulta read-only]
    RoomRepo --> DB[(PostgreSQL)]
    ResRepo --> DB

    subgraph Core (reutilizado)
        Auth
        Exceptions[AppException + handlers]
    end
```

Dirección de dependencia estricta: API → Service → Repository → Model. Solo lectura en todas las capas.

## API Layer — endpoints y query params

Se agrupan en un router nuevo, por ejemplo `app/api/queries.py` (prefijo `/api/v1`), o pueden montarse bajo prefijos existentes. Todos los endpoints son **GET** y requieren `Depends(get_current_admin_user)`.

### 1. Ocupación actual

```
GET /api/v1/occupancy/current
```
- Sin parámetros.
- 200 → `OccupancySummaryResponse`.

### 2. Habitaciones actualmente ocupadas

```
GET /api/v1/occupancy/rooms
```
- Sin parámetros.
- 200 → `list[OccupiedRoomResponse]` (lista vacía si ninguna).

### 3. Disponibilidad por rango

```
GET /api/v1/availability?check_in_date=YYYY-MM-DD&check_out_date=YYYY-MM-DD
```
- `check_in_date` (date, requerido), `check_out_date` (date, requerido).
- 422 si falta alguno, formato inválido, o `check_out_date <= check_in_date`.
- 200 → `list[RoomResponse]` de habitaciones disponibles (lista vacía si ninguna).

### 4. Historial de reservas con filtros

```
GET /api/v1/reservations/history
    ?guest_id=<int>
    &room_id=<int>
    &status=<confirmed|checked_in|checked_out|cancelled>
    &date_from=YYYY-MM-DD
    &date_to=YYYY-MM-DD
```
- Todos los filtros son **opcionales**; se combinan con AND (Req 5.5).
- `guest_id`/`room_id`: enteros > 0; formato inválido → 422 (Req 5.7).
- `status`: debe pertenecer a `ReservationStatus`; valor fuera del enum → 422 (Req 5.3).
- `date_from`/`date_to`: filtrado por fecha **both-or-neither**. Ambos pueden omitirse (sin filtro por fecha). Si se solicita filtrado por fecha, **ambos** son obligatorios: enviar solo `date_from` → 422; enviar solo `date_to` → 422. Cuando ambos están presentes y `date_to <= date_from` → 422 (Req 5.8). El rango filtra por **intersección** con `[check_in_date, check_out_date)` usando la semántica semiabierta aprobada (Req 5.4).
- Referenciar un `guest_id`/`room_id` inexistente → **200 con lista vacía** (Req 5.6), no error.
- 200 → `list[ReservationResponse]` (reutiliza el schema existente).

> Nota sobre `/api/v1/reservations/history`: para evitar colisión de rutas con `GET /api/v1/reservations/{reservation_id}` del módulo de reservas (donde `history` podría interpretarse como un id), el diseño usa un router con prefijo propio (`/api/v1/reservations/history` registrado antes, o un prefijo distinto como `/api/v1/history/reservations`). El diseño recomienda `/api/v1/history/reservations` para eliminar toda ambigüedad de enrutamiento. **Decisión de diseño:** usar `GET /api/v1/history/reservations`.

Endpoints finales:

| Método | Ruta | Respuesta |
|--------|------|-----------|
| GET | `/api/v1/occupancy/current` | `OccupancySummaryResponse` |
| GET | `/api/v1/occupancy/rooms` | `list[OccupiedRoomResponse]` |
| GET | `/api/v1/availability` | `list[RoomResponse]` |
| GET | `/api/v1/history/reservations` | `list[ReservationResponse]` |

### Validación de query params (422)

Los rangos de fecha se validan con un modelo Pydantic de dependencia (`Depends`) que agrupa los parámetros y aplica un `model_validator`:

```python
class AvailabilityQuery(BaseModel):
    check_in_date: date
    check_out_date: date

    @model_validator(mode="after")
    def _check_range(self):
        if self.check_out_date <= self.check_in_date:
            raise ValueError("check_out_date debe ser posterior a check_in_date")
        return self
```

Un `ValidationError` de Pydantic en query params produce **HTTP 422** de forma nativa en FastAPI (Req 3.4, 3.5, 5.7, 5.8, 8.4).

Para `HistoryQuery`, el filtrado por fecha es **both-or-neither** y su `model_validator` aplica:

```python
class HistoryQuery(BaseModel):
    guest_id: int | None = Field(None, gt=0)
    room_id: int | None = Field(None, gt=0)
    status: ReservationStatus | None = None
    date_from: date | None = None
    date_to: date | None = None

    @model_validator(mode="after")
    def _check_date_range(self):
        # both-or-neither: si uno está presente, el otro es obligatorio
        if (self.date_from is None) != (self.date_to is None):
            raise ValueError(
                "date_from y date_to deben proporcionarse ambos o ninguno"
            )
        # cuando ambos están presentes, date_to debe ser mayor que date_from
        if self.date_from is not None and self.date_to <= self.date_from:
            raise ValueError("date_to debe ser posterior a date_from")
        return self
```

- Solo `date_from` → 422. Solo `date_to` → 422. Ambos con `date_to <= date_from` → 422. Ambos omitidos → sin filtro por fecha. No se implementa filtrado por fecha de extremo abierto.

## Service Layer — `app/services/query_service.py` (nuevo)

```python
class QueryService:
    def __init__(
        self,
        room_repository: RoomRepository,
        reservation_repository: ReservationRepository,
        today_provider: Callable[[], date] = date.today,
    ):
        ...

    def get_current_occupancy(self) -> OccupancySummary: ...
    def list_occupied_rooms(self) -> list[Room]: ...
    def list_available_rooms(self, check_in: date, check_out: date) -> list[Room]: ...
    def get_reservation_history(self, filters: HistoryFilters) -> list[Reservation]: ...
```

### `get_current_occupancy` (Req 1, 10.1)

- Obtiene conteos por estado con **consultas agregadas** (no cargando todas las filas):
  - `total = RoomRepository.count_all()`
  - `occupied = RoomRepository.count_by_status(OCUPADA)`
  - `available_now = RoomRepository.count_by_status(DISPONIBLE)`
  - `maintenance = RoomRepository.count_by_status(MANTENIMIENTO)`
- `occupancy_rate = occupied / total` con **guarda de división por cero** → `0.0` si `total == 0` (Req 1.3).
- La ocupación se deriva de `Room.status` (fuente única, mantenida por check-in/check-out). Es consistente con "reservas `checked_in`" porque ese es justamente el efecto del check-in (Req 1.5).

### `list_occupied_rooms` (Req 2)

- `RoomRepository.get_by_status(OCUPADA)` → lista (posiblemente vacía). Sin estructuras adicionales.

### `list_available_rooms` (Req 3, 10.2, 10.3, 10.5) — evita N+1

Estrategia en **dos consultas** (no una por habitación):

1. Traer los `room_id` con al menos una reserva **activa solapada** en `[check_in, check_out)`:
   `ReservationRepository.get_room_ids_with_active_overlap(check_in, check_out) -> set[int]`
   (una sola consulta: filtra `status IN (confirmed, checked_in)` AND `check_in_date < check_out` AND `check_out_date > check_in`, seleccionando `DISTINCT room_id`).
2. Traer las habitaciones candidatas excluyendo mantenimiento:
   `RoomRepository.get_not_in_maintenance() -> list[Room]` (una sola consulta: `status != MANTENIMIENTO`).
3. En memoria: `available = [r for r in candidatas if r.id not in blocked_room_ids]`.

Esto es **O(1) consultas** (2 queries totales) independientemente del número de habitaciones — evita el patrón N+1 de preguntar solapamiento por cada habitación. Alternativa equivalente: un solo `LEFT JOIN ... WHERE reservation.id IS NULL AND room.status != 'mantenimiento'`; el diseño acepta cualquiera de las dos, priorizando claridad y reutilización de repos. La semántica de solapamiento reutiliza exactamente la regla aprobada (Req 3.7).

### `get_reservation_history` (Req 4, 5) — filtros combinables sin N+1

- Un único método de repositorio construye **una sola consulta** con filtros opcionales aplicados dinámicamente:
  `ReservationRepository.query_history(guest_id=None, room_id=None, status=None, date_from=None, date_to=None) -> list[Reservation]`
- Filtros conjuntivos (AND). Cada filtro presente añade un `WHERE`:
  - `guest_id` → `Reservation.guest_id == guest_id`
  - `room_id` → `Reservation.room_id == room_id`
  - `status` → `Reservation.status == status`
  - rango `[date_from, date_to)` → intersección: `Reservation.check_in_date < date_to AND Reservation.check_out_date > date_from` (consistente con la regla semiabierta, Req 5.4). **Both-or-neither**: el filtro por fecha solo se aplica cuando `date_from` y `date_to` están **ambos** presentes; proveer solo uno de los dos es un error de validación (422) resuelto en la capa de query params, no en el repositorio. No existe comportamiento de rango abierto (open-ended).
- Sin filtros → todas las reservas, todos los estados (Req 4.1). Sin coincidencias → lista vacía (Req 4.4, 5.6).
- Devuelve reservas con todos los campos existentes vía `ReservationResponse` (Req 4.3). No hay N+1: es una sola consulta que retorna filas de `reservations`; no se cargan relaciones por fila (el response usa los `guest_id`/`room_id` escalares ya presentes).

## Data Models / Schemas

No hay cambios de modelos ni tablas nuevas (Req 6.2, 6.3). Se añaden **schemas de respuesta** (Pydantic) en `app/schemas/query.py` (nuevo). Se reutilizan `RoomResponse` y `ReservationResponse` existentes donde aplica.

```python
class OccupancySummaryResponse(BaseModel):
    total_rooms: int
    occupied_rooms: int
    available_rooms: int          # habitaciones en estado 'disponible' ahora
    maintenance_rooms: int
    occupancy_rate: float         # occupied / total, 0.0 si total == 0


class OccupiedRoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    room_number: str
    room_type: RoomType
    status: RoomStatus            # será 'ocupada'
```

- **Disponibilidad** reutiliza `RoomResponse` (schema existente de Room) para no duplicar la forma de la habitación.
- **Historial** reutiliza `ReservationResponse` existente.
- Modelos de **query params** (no de body): `AvailabilityQuery`, `HistoryQuery` (con validación de rango → 422).

### Objetos internos del service

- `OccupancySummary`: dataclass/estructura simple con los conteos (mapeada a `OccupancySummaryResponse`).
- `HistoryFilters`: contenedor de los filtros normalizados que el router pasa al service.

## Repository Layer — métodos de solo lectura añadidos

Se **reutilizan** los repositorios existentes y se añaden únicamente métodos de consulta (sin escrituras, sin reglas de negocio — Req 6.4, 7.3).

`RoomRepository` (añadir):
- `count_all() -> int`
- `count_by_status(status: RoomStatus) -> int`
- `get_by_status(status: RoomStatus) -> list[Room]`  *(ya existe `get_available`; se generaliza o se añade `get_by_status`)*
- `get_not_in_maintenance() -> list[Room]`

`ReservationRepository` (añadir):
- `get_room_ids_with_active_overlap(check_in: date, check_out: date) -> set[int]`
- `query_history(...) -> list[Reservation]`

> `get_active_overlapping` existente permanece intacto; los nuevos métodos comparten su misma semántica de estados activos y de intervalo semiabierto para garantizar consistencia (Req 3.7, 10.3). Se recomienda que el conjunto de estados activos se exprese una sola vez (constante compartida) para evitar divergencia.

## Error Handling

Reutiliza el manejo existente sin esquema nuevo (Req 8.5):

| Condición | HTTP |
|-----------|------|
| Consulta exitosa (incl. resultados vacíos) | 200 |
| Query param inválido (tipo/formato) o rango de fechas inválido (`hasta <= desde`) | 422 (nativo FastAPI/Pydantic) |
| `status` fuera del enum | 422 |
| Token faltante/ inválido | 401 (auth existente) |
| Sin rol admin | 403 (auth existente) |
| Error no controlado / BD | 500 genérico (`generic_exception_handler`) |

No se definen nuevas `AppException`; las consultas no tienen condiciones de negocio que produzcan 404/409 (un id inexistente en filtros devuelve lista vacía, Req 5.6).

## Authorization

Todos los endpoints usan `Depends(get_current_admin_user)` (Req 9). 401/403 con el mismo comportamiento que los módulos existentes. Sin middleware nuevo.

## Correctness Properties

- **P1 — Resumen de ocupación consistente:** `occupied + available + maintenance == total` y `occupancy_rate == occupied/total` (o `0.0` si `total == 0`). (Req 1)
- **P2 — Ocupadas = estado ocupada:** `list_occupied_rooms` devuelve exactamente las habitaciones con `status == OCUPADA`. (Req 2)
- **P3 — Disponibilidad = no-mantenimiento ∧ sin solapamiento activo:** una habitación aparece en disponibilidad sii `status != MANTENIMIENTO` y no tiene reserva activa (`confirmed`/`checked_in`) solapada. (Req 3, 10)
- **P4 — Ocupada-ahora pero disponible-futuro:** una habitación `ocupada` cuya reserva `checked_in` termina antes del rango solicitado aparece como disponible para ese rango futuro. (Restricción explícita)
- **P5 — Frontera semiabierta:** una reserva `[.., D)` no bloquea un rango `[D, ..)` y viceversa. (Req 3.2)
- **P6 — Exclusión de canceladas/checked_out:** reservas `cancelled`/`checked_out` no bloquean disponibilidad. (Req 3.3, 10.3)
- **P7 — Mantenimiento excluye siempre:** una habitación en `mantenimiento` nunca aparece disponible, aun sin reservas. (Req 10.5)
- **P8 — Historial completo por defecto:** sin filtros, devuelve todas las reservas de todos los estados. (Req 4.1)
- **P9 — Filtros AND:** combinar filtros devuelve solo las reservas que cumplen todos. (Req 5.5)
- **P10 — Id inexistente → vacío:** filtrar por guest/room inexistente devuelve `[]` con 200. (Req 5.6)
- **P11 — Rango inválido → 422:** `hasta <= desde` en disponibilidad o en filtro de historial devuelve 422. (Req 3.4, 5.8)
- **P12 — Auth:** sin JWT → 401; no-admin → 403; en todos los endpoints. (Req 9)
- **P13 — Solo lectura:** ninguna consulta modifica `rooms`, `guests` ni `reservations`. (Req 6.1)

## Testing Strategy

Enfoque dual (unit + property-based con Hypothesis) y estructura de carpetas consistente con los módulos existentes.

```
tests/
├── unit/
│   ├── test_query_service.py            # ocupación, disponibilidad, historial (repos mockeados)
│   └── test_query_repository_methods.py # count/get_by_status/get_room_ids_with_active_overlap/query_history (SQLite en memoria)
├── property/
│   └── test_query_properties.py         # P1–P11 (SQLite en memoria)
└── integration/
    └── test_query_api.py                # endpoints + auth + 200/422/401/403
```

Casos y propiedades a cubrir explícitamente:

- **Ocupación (P1, P2):** mezclas de habitaciones `disponible`/`ocupada`/`mantenimiento`; conteos y tasa; caso `total == 0` (sin división por cero, Req 1.3); lista de ocupadas vacía.
- **Exclusión de mantenimiento (P7):** habitación en `mantenimiento` sin reservas → nunca disponible; habitación en `mantenimiento` con hueco libre → tampoco disponible.
- **Fronteras de solapamiento (P5):** rangos adyacentes `[Sep 1, Sep 5)` vs `[Sep 5, Sep 8)` no se bloquean; intersección parcial, contención y rango idéntico sí bloquean.
- **Ocupada-ahora / disponible-futuro (P4):** reserva `checked_in` pasada respecto a un rango futuro → habitación disponible para el futuro aunque hoy esté `ocupada`.
- **Estados activos vs no activos (P6):** `confirmed` y `checked_in` bloquean; `cancelled` y `checked_out` no.
- **Historial — filtros combinados (P8, P9, P10):** sin filtros (todos los estados); por guest; por room; por status; por rango; combinaciones AND; guest/room inexistente → `[]`.
- **Rangos inválidos (P11):** `check_out_date <= check_in_date` en `/availability` → 422; `date_to <= date_from` en `/history/reservations` → 422; fechas malformadas → 422; `status` fuera del enum → 422; id no entero → 422.
- **Auth (P12):** sin token → 401; token válido no-admin → 403; en los cuatro endpoints. Reutiliza los generadores de los tests de auth existentes.
- **Resultados vacíos:** cada endpoint devuelve 200 con lista vacía / resumen en cero cuando no hay datos.
- **N+1 / eficiencia:** test que verifica que `list_available_rooms` usa un número **constante** de consultas (por ejemplo contando llamadas al repositorio o usando un contador de queries de SQLAlchemy), independientemente del número de habitaciones.
- **Solo lectura (P13):** tras ejecutar cada consulta, el estado de `rooms`/`reservations` no cambia.

Configuración: `@settings(max_examples=100)` para property tests; fixtures de SQLite en memoria para unit/property; para integración, `StaticPool` + override de `get_db` + JWT admin, sembrando habitaciones, huéspedes y reservas en varios estados. La verificación final del feature deberá correr `ruff check .` y `pytest` sobre todo el proyecto.

## Design Decisions Summary

| Decisión | Elección | Justificación |
|----------|----------|---------------|
| Nuevas tablas | Ninguna | El historial ya se preserva en `reservations` (Req 6.3) |
| Escrituras | Ninguna | Módulo solo lectura (Req 6.1) |
| Ocupación actual | Derivada de `Room.status` | Fuente única existente (Req 1.5, 6.5) |
| Disponibilidad futura | `status != MANTENIMIENTO` ∧ sin solapamiento activo | Restricción aprobada; no exige `disponible` |
| Estados activos | `confirmed` + `checked_in` | Reutiliza regla existente (Req 3.3) |
| Ruta de historial | `/api/v1/history/reservations` | Evita colisión con `/reservations/{id}` |
| Disponibilidad sin N+1 | 2 consultas (ids solapados + no-mantenimiento) | Evita query por habitación |
| Response de disponibilidad/historial | Reutiliza `RoomResponse` / `ReservationResponse` | No duplicar formas |
| Validación de rango | Pydantic query models → 422 | Consistencia con el resto de la API |
