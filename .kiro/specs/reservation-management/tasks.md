# Implementation Plan: Reservation Management

## Overview

Implementación del módulo de administración de reservas (crear, consultar, listar, actualizar y cancelar, sin eliminación física) para StayBook siguiendo la arquitectura por capas existente: Core → Model/Schemas → Repository → Service → API → Migración. Cada tarea construye sobre la anterior de forma incremental, reutilizando los patrones ya establecidos por Room Management y Guest Management. Los tests de propiedades se intercalan para validación temprana.

## Tasks

- [x] 1. Set up core layer extensions
  - [x] 1.1 Add reservation domain exceptions in `app/core/exceptions.py`
    - Add `ReservationNotFoundException` (404), `ReservationInvalidDatesException` (422), `ReservationOverlapException` (409), `ReservationCancelledNotEditableException` (409), `ReservationAlreadyCancelledException` (409) as subclasses of the existing `AppException`
    - Reuse the existing `GuestNotFoundException` (404) and `RoomNotFoundException` (404) for entity existence checks; do not create new ones
    - Do not modify `AppException` base class or existing Room/Guest exceptions
    - _Requirements: 2.1, 2.2, 3.1, 4.2, 6.2, 7.9, 8.4, 10.4, 10.5_

  - [x] 1.2 Confirm audit logging reuse (no changes)
    - Reuse the existing `audit_log(operation, room_id, result)` signature exactly as used by Room/Guest (Option A); `ReservationService` will call it positionally with the reservation id
    - Do not modify `app/core/logging.py`; ensure no tokens, passwords, or guest PII are ever passed to it
    - _Requirements: 12.1, 12.2_

- [x] 2. Create data model
  - [x] 2.1 Create SQLAlchemy model in `app/models/reservation.py`
    - Define `ReservationStatus` enum (confirmed, cancelled)
    - Define `Reservation` model inheriting from the existing `Base` with columns: id, guest_id (FK guests.id, indexed), room_id (FK rooms.id, indexed), check_in_date (Date), check_out_date (Date), status (SAEnum, default confirmed, indexed), total_price (`Numeric(10, 2)`), created_at, updated_at (timestamps with `server_default=func.now()` and `onupdate=func.now()`)
    - Use `ForeignKey("guests.id")` and `ForeignKey("rooms.id")` for referential integrity; no `relationship()` needed
    - Register the model in `alembic/env.py` (`from app.models.reservation import Reservation  # noqa: F401`)
    - _Requirements: 1.1, 2.1, 2.2, 8.6, 9.5_

- [x] 3. Create schemas
  - [x] 3.1 Create Pydantic schemas in `app/schemas/reservation.py`
    - `ReservationCreate`: `model_config = ConfigDict(extra="forbid")`; guest_id (>0), room_id (>0), check_in_date, check_out_date; `model_validator` rejecting check_out_date <= check_in_date
    - `ReservationUpdate`: `model_config = ConfigDict(extra="forbid")`; room_id/check_in_date/check_out_date all optional (resulting-state date validation happens in the Service)
    - `ReservationResponse`: all fields with `ConfigDict(from_attributes=True)`, total_price as `Decimal`
    - Server-managed fields (id, status, total_price, created_at, updated_at) must NOT be accepted in create/update; `extra="forbid"` makes client-sent total_price or status raise 422
    - _Requirements: 1.3, 1.4, 3.1, 6.1, 7.2, 7.3_

  - [x] 3.2 Write unit tests for reservation schemas
    - Assert `extra="forbid"` rejects a create/update payload containing total_price or status (422 via ValidationError)
    - Assert create rejects check_out_date <= check_in_date
    - _Requirements: 1.3, 3.1, 7.3_

- [x] 4. Implement repository layer
  - [x] 4.1 Create reservation repository in `app/repositories/reservation_repository.py`
    - Implement `ReservationRepository` with a SQLAlchemy `Session` dependency, mirroring Room/Guest repository style (`flush`/`refresh`, `db.get` by PK)
    - Methods: `create`, `get_by_id`, `get_all` (confirmed and cancelled), `update`
    - Do not implement a `delete` method (reservations are preserved)
    - _Requirements: 5.1, 8.6, 9.3_

  - [x] 4.2 Implement overlap query `get_active_overlapping`
    - Signature: `get_active_overlapping(room_id, check_in, check_out, exclude_id=None) -> list[Reservation]`
    - Filter `status == confirmed` only (cancelled reservations do not participate)
    - Half-open overlap rule: `Reservation.check_in_date < check_out AND Reservation.check_out_date > check_in`
    - When `exclude_id` is provided, exclude that reservation id (used during update self-exclusion)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 7.5_

  - [x] 4.3 Write unit tests for repository
    - Test create/get_by_id/get_all/update with in-memory SQLite
    - Test `get_active_overlapping`: intersecting ranges detected, adjacent ranges (out == in) NOT detected, cancelled excluded, `exclude_id` excludes the given reservation
    - _Requirements: 4.3, 4.4, 5.1, 7.5_

- [x] 5. Implement service layer
  - [x] 5.1 Create reservation service in `app/services/reservation_service.py`
    - Implement `ReservationService` with `ReservationRepository`, `RoomRepository`, and `GuestRepository` dependencies (reuse existing Room/Guest repositories)
    - `create_reservation`: validate guest exists (`GuestNotFoundException`), room exists (`RoomNotFoundException`), dates (`ReservationInvalidDatesException`), no overlap with active reservations (`ReservationOverlapException`); compute `total_price = nights * room.price_per_night` using `Decimal`; persist with status confirmed; `audit_log("create", reservation.id, ...)`
    - `list_reservations`: delegate to repository `get_all`
    - `get_reservation`: get by ID → `ReservationNotFoundException` if not found
    - `update_reservation`: reject if not found (404) or cancelled (`ReservationCancelledNotEditableException`, 409); build the resulting state from existing values + provided changes (`exclude_unset`, only room_id/check_in_date/check_out_date); validate resulting room existence, resulting dates, and overlap excluding self (`exclude_id`); recalculate `total_price` on the resulting state; `audit_log("update", ...)`
    - `cancel_reservation`: reject if not found (404) or already cancelled (`ReservationAlreadyCancelledException`, 409); set status = cancelled (preserve all other fields); `audit_log("cancel", ...)`
    - Never modify Room.status in any operation
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 4.2, 4.4, 4.5, 5.1, 6.2, 7.1, 7.4, 7.5, 7.6, 7.9, 8.1, 8.2, 8.4, 9.2, 9.5, 12.1_

  - [x] 5.2 Write property test for creation round-trip and total price
    - **Property 1 & 2**: for valid data, create then get_by_id returns matching fields with status confirmed; `total_price == nights * room.price_per_night`
    - **Validates: Requirements 1.1, 1.2, 3.2, 6.1**

  - [x] 5.3 Write property test for invalid dates
    - **Property 4**: for any check_out <= check_in, creation is rejected and nothing persisted
    - **Validates: Requirements 3.1**

  - [x] 5.4 Write property test for overlap and adjacency
    - **Property 5**: intersecting active ranges for the same room → second rejected (409); adjacent ranges (out == in) → both allowed
    - **Validates: Requirements 4.1, 4.2, 4.3**

  - [x] 5.5 Write property test for cancelled reservations releasing their range
    - **Property 6**: a cancelled reservation is excluded from overlap; its range becomes available for a new reservation of the same room
    - **Validates: Requirements 4.4**

  - [x] 5.6 Write property test for partial update resulting state and self-exclusion
    - **Property 7**: partial update (subset of room_id/check_in_date/check_out_date) validates dates/overlap and recalculates price on the resulting state, excluding the reservation itself from its overlap check
    - **Validates: Requirements 7.4, 7.5, 7.6**

  - [x] 5.7 Write property test for cancellation and missing entities
    - **Property 8 & 9**: cancel sets status cancelled and preserves the record (still retrievable/listable); re-cancel → 409; editing cancelled → 409; create/update with missing guest_id or room_id → 404
    - **Validates: Requirements 2.1, 2.2, 8.1, 8.2, 8.4, 8.6, 7.9**

- [x] 6. Checkpoint - Ensure core logic tests pass
  - Ensure all reservation unit and property tests pass so far; ask the user if questions arise.

- [x] 7. Implement API layer
  - [x] 7.1 Create reservation router in `app/api/reservations.py`
    - Reuse the existing `get_current_admin_user` dependency and `get_db` session; add a `_get_service` helper that wires `ReservationRepository`, `RoomRepository`, and `GuestRepository`
    - `POST /api/v1/reservations` → 201, validate with `ReservationCreate`, requires admin auth
    - `GET /api/v1/reservations` → 200, returns list of all reservations, requires admin auth
    - `GET /api/v1/reservations/{reservation_id}` → 200, returns single reservation, requires admin auth
    - `PATCH /api/v1/reservations/{reservation_id}` → 200, partial update with `ReservationUpdate`, requires admin auth
    - `POST /api/v1/reservations/{reservation_id}/cancel` → 200, returns cancelled reservation, requires admin auth
    - Do not add a DELETE endpoint
    - _Requirements: 1.5, 5.2, 5.3, 6.3, 7.10, 8.5, 9.1, 11.1_

  - [x] 7.2 Register reservation router in `app/main.py`
    - Include the reservation router via `app.include_router(...)` alongside rooms and guests
    - Do not modify the already-registered exception handlers; they already cover reservation `AppException` subclasses
    - _Requirements: 9.1, 10.2_

  - [x] 7.3 Write property test for authentication and authorization enforcement
    - **Property 10**: requests without JWT → 401; requests with valid JWT but non-admin role → 403; no reservation data accessible without valid admin credentials (cover all endpoints including /cancel)
    - **Validates: Requirements 11.1, 11.2, 11.3**

- [x] 8. Integration tests
  - [x] 8.1 Write integration tests for reservation API endpoints
    - Use the guest-management integration pattern: `StaticPool` shared in-memory SQLite + `get_db` override + admin JWT; seed an existing guest and room first (FKs)
    - Cover: create (201), total_price correctness in response, list (200 + empty list), get by id (200/404), invalid dates (422), client-sent total_price/status (422), overlap (409), adjacent reservations allowed (201), partial update (200), update recalculates total_price, update self-exclusion succeeds, cancel (200 → status cancelled), re-cancel (409), edit cancelled (409), missing guest/room (404)
    - Verify error responses use the existing `{"detail", "status_code"}` format
    - _Requirements: 1.5, 2.1, 2.2, 3.1, 4.2, 4.3, 5.2, 6.2, 7.3, 7.4, 7.9, 7.10, 8.1, 8.4, 8.5, 10.2, 10.4, 10.5_

  - [x] 8.2 Write integration tests for audit log data safety
    - **Property 11**: after create/update/cancel operations, verify audit log entries contain only operation, timestamp, reservation id, and result — never guest PII, tokens, or passwords
    - _Requirements: 12.1, 12.2_

- [x] 9. Create Alembic migration for reservations table
  - [x] 9.1 Create Alembic migration script
    - New revision (e.g. `003_create_reservations_table.py`) with `down_revision = "002"`, mirroring the style of the rooms/guests migrations
    - `upgrade()` creates the `reservations` table with all columns, `PrimaryKeyConstraint("id")`, `ForeignKeyConstraint(["guest_id"], ["guests.id"])`, `ForeignKeyConstraint(["room_id"], ["rooms.id"])`, `CheckConstraint` for status values, and `CheckConstraint("check_out_date > check_in_date", name="ck_reservations_dates")`
    - Create indexes `ix_reservations_guest_id`, `ix_reservations_room_id`, `ix_reservations_status`; `downgrade()` drops indexes and table in reverse order
    - _Requirements: 1.1, 2.1, 2.2, 3.1_

- [x] 10. Final verification - Full suite and lint
  - Run `ruff check .` to confirm the whole project passes linting per `pyproject.toml`
  - Run the complete StayBook test suite (`pytest`), not only reservation tests, to confirm no regressions in Room Management or Guest Management
  - Fix any failures before considering the feature complete; ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document; unit tests validate specific examples and edge cases
- The implementation reuses the existing authentication (`get_current_admin_user`), exception handling (`AppException` + global handlers), audit logging (`audit_log`, Option A signature), database configuration (`get_db`, `Base`), and the existing `RoomRepository` and `GuestRepository` — none of these are redesigned
- No DELETE endpoint or repository delete is implemented; reservations are preserved for historical purposes. Cancellation sets status to `cancelled`
- Room occupancy status is never modified by this module (check-in/check-out is a future spec)
- Monetary values use `Decimal` / SQLAlchemy `Numeric`
- Overlap detection uses the half-open rule `existing.check_in_date < requested_check_out AND existing.check_out_date > requested_check_in`, confirmed reservations only, with optional self-exclusion during updates
- Out of scope: check-in/check-out, room occupancy changes, payments, Docker, CI/CD, AWS
- All tests use `pytest`; property tests use `hypothesis` with `@settings(max_examples=100)`; linting uses `ruff`

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["3.1", "4.1"] },
    { "id": 3, "tasks": ["3.2", "4.2"] },
    { "id": 4, "tasks": ["4.3", "5.1"] },
    { "id": 5, "tasks": ["5.2", "5.3", "5.4", "5.5", "5.6", "5.7"] },
    { "id": 6, "tasks": ["6"] },
    { "id": 7, "tasks": ["7.1"] },
    { "id": 8, "tasks": ["7.2", "9.1"] },
    { "id": 9, "tasks": ["7.3", "8.1", "8.2"] },
    { "id": 10, "tasks": ["10"] }
  ]
}
```
