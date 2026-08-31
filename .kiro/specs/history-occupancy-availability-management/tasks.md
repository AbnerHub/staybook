# Implementation Plan: History / Occupancy / Availability Management

## Overview

Implementación de un módulo **de solo lectura** para consultas de ocupación actual, habitaciones ocupadas, disponibilidad por rango de fechas e historial de reservas con filtros, siguiendo la arquitectura por capas existente: Repository (métodos read-only) → Service → API. No introduce escrituras, ni tablas nuevas, ni migraciones. Reutiliza `RoomRepository`, `ReservationRepository`, `get_current_admin_user`, `AppException` + handlers globales, y los schemas `RoomResponse`/`ReservationResponse`. Los tests de propiedades se intercalan para validación temprana.

## Tasks

- [x] 1. Add read-only repository query methods (no writes, no new tables)
  - [x] 1.1 Extend `RoomRepository` with count/query helpers
    - Add `count_all() -> int`, `count_by_status(status) -> int`, `get_by_status(status) -> list[Room]`, `get_not_in_maintenance() -> list[Room]`
    - Read-only only; no business rules; reuse the existing `Session`
    - _Requirements: 1.1, 1.5, 2.1, 3.1, 6.4, 7.3_

  - [x] 1.2 Extend `ReservationRepository` with read-only query methods
    - Add `get_room_ids_with_active_overlap(check_in, check_out) -> set[int]`: single query filtering `status IN (confirmed, checked_in)` AND half-open overlap `check_in_date < check_out AND check_out_date > check_in`, selecting DISTINCT `room_id`
    - Add `query_history(guest_id=None, room_id=None, status=None, date_from=None, date_to=None) -> list[Reservation]`: single query applying only the provided filters (AND); date range uses half-open intersection `check_in_date < date_to AND check_out_date > date_from` and is applied only when both dates are present
    - Reuse the exact active-status set and half-open semantics of the existing `get_active_overlapping` (share a single constant for the active statuses to avoid divergence); do not modify `get_active_overlapping`
    - _Requirements: 3.1, 3.2, 3.3, 3.7, 4.1, 5.1, 5.2, 5.3, 5.4, 5.5, 6.4, 7.3, 10.3_

  - [x] 1.3 Write unit tests for the new repository methods
    - `count_*`/`get_by_status`/`get_not_in_maintenance` with mixed room statuses (disponible/ocupada/mantenimiento)
    - `get_room_ids_with_active_overlap`: intersecting active reservation returns the room id; adjacent (`out == in`) returns nothing; `cancelled`/`checked_out` excluded; `confirmed`/`checked_in` included
    - `query_history`: no filters returns all statuses; each single filter; combined AND filters; date-range intersection; no matches → empty
    - _Requirements: 2.1, 3.2, 3.3, 4.1, 5.4, 5.5_

- [x] 2. Create response and query-param schemas
  - [x] 2.1 Create `app/schemas/query.py`
    - `OccupancySummaryResponse` (total_rooms, occupied_rooms, available_rooms, maintenance_rooms, occupancy_rate: float)
    - `OccupiedRoomResponse` (`from_attributes=True`: id, room_number, room_type, status)
    - Reuse existing `RoomResponse` for availability and `ReservationResponse` for history (do not duplicate)
    - _Requirements: 1.2, 2.2, 3.8, 4.3, 6.4_

  - [x] 2.2 Create query-param models with validation (422 semantics)
    - `AvailabilityQuery` (check_in_date, check_out_date both required) with `model_validator` rejecting `check_out_date <= check_in_date`
    - `HistoryQuery` (all optional: guest_id>0, room_id>0, status: ReservationStatus, date_from, date_to) with a **both-or-neither** `model_validator`: providing only one date → error; both present with `date_to <= date_from` → error
    - Pydantic validation surfaces as HTTP 422 natively via FastAPI
    - _Requirements: 3.4, 3.5, 5.3, 5.7, 5.8, 8.4_

  - [x] 2.3 Write unit tests for query-param validation
    - Availability: missing param, malformed date, `check_out <= check_in` → all invalid
    - History both-or-neither: only date_from → invalid; only date_to → invalid; both with `date_to <= date_from` → invalid; both omitted → valid; both valid → valid; status outside enum → invalid; non-int id → invalid
    - _Requirements: 3.4, 3.5, 5.3, 5.7, 5.8_

- [x] 3. Implement the query service
  - [x] 3.1 Create `QueryService` in `app/services/query_service.py`
    - Constructor: `RoomRepository`, `ReservationRepository`, `today_provider: Callable[[], date] = date.today`
    - `get_current_occupancy()`: derive counts from `Room.status` via repository counts; `occupancy_rate = occupied/total` with zero-division guard (0.0 when total == 0); occupancy derived from existing operational state only (no second source of truth)
    - `list_occupied_rooms()`: return rooms with `status == OCUPADA`
    - `list_available_rooms(check_in, check_out)`: **constant-query (no N+1)** — (1) `get_room_ids_with_active_overlap`, (2) `get_not_in_maintenance`, then in-memory difference. Available ⇔ `status != MANTENIMIENTO` AND not in the blocked set. Do NOT require `status == disponible`
    - `get_reservation_history(filters)`: delegate to `query_history`; date filter applied only when both dates present
    - Read-only: never create/update/delete rooms/guests/reservations
    - _Requirements: 1.1, 1.3, 1.5, 2.1, 3.1, 3.2, 3.3, 3.6, 3.7, 4.1, 4.4, 5.5, 5.6, 6.1, 6.2, 6.5, 7.2, 10.1, 10.2, 10.3, 10.5_

  - [x] 3.2 Property test — occupancy summary consistency
    - **P1/P2**: `occupied + available + maintenance == total`; `occupancy_rate == occupied/total` (0.0 if total == 0); occupied list equals rooms with status OCUPADA
    - **Validates: Requirements 1.2, 1.3, 2.1**

  - [x] 3.3 Property test — availability core semantics
    - **P3/P6**: room available ⇔ `status != MANTENIMIENTO` AND no active (`confirmed`/`checked_in`) overlapping reservation; `cancelled`/`checked_out` never block
    - **Validates: Requirements 3.1, 3.3, 10.2, 10.3**

  - [x] 3.4 Property test — occupied-now but available-future
    - **P4**: a room currently `ocupada` whose `checked_in` reservation ends before the requested future range IS returned as available for that range (availability must not require `status == disponible`)
    - **Validates: Requirements 3.1, 10.2**

  - [x] 3.5 Property test — maintenance always excluded
    - **P7**: a room in `mantenimiento` is never returned as available, even with no reservations and an otherwise-free range
    - **Validates: Requirements 10.5**

  - [x] 3.6 Property test — half-open adjacency
    - **P5**: reservation `[.., D)` does not block range `[D, ..)` and reservation `[D, ..)` does not block range `[.., D)`; intersecting/contained/identical ranges do block
    - **Validates: Requirements 3.2**

  - [x] 3.7 Property test — history filters
    - **P8/P9/P10**: no filters → all statuses; single filters; combined AND filters; nonexistent guest_id/room_id → empty list
    - **Validates: Requirements 4.1, 5.1, 5.2, 5.3, 5.5, 5.6**

- [x] 4. Checkpoint - Ensure core logic tests pass
  - Ensure all query service and repository tests pass so far; ask the user if questions arise.

- [x] 5. Implement the API layer (four GET endpoints)
  - [x] 5.1 Create query router in `app/api/queries.py`
    - `GET /api/v1/occupancy/current` → 200 `OccupancySummaryResponse`
    - `GET /api/v1/occupancy/rooms` → 200 `list[OccupiedRoomResponse]` (empty list allowed)
    - `GET /api/v1/availability?check_in_date&check_out_date` → 200 `list[RoomResponse]` (empty allowed); invalid/missing/`out<=in` → 422
    - `GET /api/v1/history/reservations` with optional filters → 200 `list[ReservationResponse]` (empty allowed); both-or-neither date rule enforced (422)
    - Add a `_get_query_service` helper wiring `QueryService(RoomRepository(db), ReservationRepository(db))`
    - All endpoints use `Depends(get_current_admin_user)`; GET only; params as query string
    - _Requirements: 1.4, 2.3, 2.4, 3.6, 3.8, 4.4, 4.5, 8.1, 8.2, 8.3, 8.6, 9.1_

  - [x] 5.2 Register the query router in `app/main.py`
    - `app.include_router(...)` alongside existing routers; reuse existing exception handlers (no new schema); ensure `/api/v1/history/reservations` does not collide with `/api/v1/reservations/{reservation_id}`
    - _Requirements: 7.1, 8.5, 8.6_

  - [x] 5.3 Property test — authentication and authorization enforcement
    - **P12**: no JWT → 401; valid JWT non-admin → 403; on all four endpoints
    - **Validates: Requirements 9.1, 9.2, 9.3**

- [x] 6. Integration tests
  - [x] 6.1 Integration tests for occupancy endpoints
    - Seed rooms in mixed statuses; assert summary counts + rate (incl. total == 0 → rate 0.0); occupied-rooms list; empty results → 200
    - _Requirements: 1.2, 1.3, 2.3, 2.4, 8.3_

  - [x] 6.2 Integration tests for availability endpoint
    - Occupied-now-but-available-future returns the room; maintenance room never returned; adjacent reservations do not overlap; `cancelled`/`checked_out` do not block; invalid range → 422; empty availability → 200 empty list
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.6, 8.3, 10.2, 10.3, 10.5_

  - [x] 6.3 Integration tests for history endpoint
    - No filters returns all statuses; combined AND filters; nonexistent id → empty; both-or-neither date params (only date_from → 422, only date_to → 422, both invalid order → 422, both omitted → 200, both valid → 200); status outside enum → 422
    - _Requirements: 4.1, 4.4, 5.1, 5.2, 5.3, 5.5, 5.6, 5.8, 8.3_

  - [x] 6.4 Test — constant-query availability (no N+1)
    - Assert `list_available_rooms` issues a constant number of queries regardless of room count (e.g. count repository calls or SQLAlchemy statements)
    - _Requirements: 3.7_

  - [x] 6.5 Test — read-only behavior
    - **P13**: after running each query, the state of `rooms`/`guests`/`reservations` is unchanged (row counts and statuses identical)
    - _Requirements: 6.1_

- [x] 7. Final verification - Full suite and lint
  - Run `ruff check .` to confirm the whole project passes linting per `pyproject.toml`
  - Run the complete StayBook test suite (`pytest`), not only this module's tests, to confirm no regressions in Room, Guest, Reservation or Check-in/Check-out
  - Confirm no new Alembic migration was created (no schema change) and no new tables were introduced
  - Fix any failures before considering the feature complete; ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- Read-only module: no writes to rooms/guests/reservations; no new tables; no migrations
- Availability = `room.status != MANTENIMIENTO` AND no active overlapping reservation; it does NOT require `status == disponible` (a room occupied now may be available for a future range)
- Active blocking statuses: `confirmed` + `checked_in`; `cancelled` + `checked_out` never block
- Overlap uses the approved half-open interval `[check_in_date, check_out_date)`, reusing the existing semantics/constant
- Availability is implemented with a constant number of queries (no per-room querying / no N+1)
- History date filtering is both-or-neither: both provided (with `date_to > date_from`) or both omitted; providing only one → 422; no open-ended date filtering
- The four approved GET endpoints: `/api/v1/occupancy/current`, `/api/v1/occupancy/rooms`, `/api/v1/availability`, `/api/v1/history/reservations`
- Reuses existing authentication (`get_current_admin_user`), error handling (`AppException` + global handlers), DB session (`get_db`, `Base`), and `RoomResponse`/`ReservationResponse`
- Out of scope: payments, billing, invoices, housekeeping, analytics dashboards, notifications, frontend, Docker, CI/CD, AWS, Terraform
- All tests use `pytest`; property tests use `hypothesis` with `@settings(max_examples=100)`; linting uses `ruff`

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "2.1", "2.2"] },
    { "id": 1, "tasks": ["1.3", "2.3", "3.1"] },
    { "id": 2, "tasks": ["3.2", "3.3", "3.4", "3.5", "3.6", "3.7"] },
    { "id": 3, "tasks": ["4"] },
    { "id": 4, "tasks": ["5.1"] },
    { "id": 5, "tasks": ["5.2", "5.3"] },
    { "id": 6, "tasks": ["6.1", "6.2", "6.3", "6.4", "6.5"] },
    { "id": 7, "tasks": ["7"] }
  ]
}
```
