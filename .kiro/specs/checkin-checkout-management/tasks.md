# Implementation Plan: Check-in / Check-out Management

## Overview

Implementación del ciclo de vida operativo (check-in / check-out) de una reserva existente para StayBook, siguiendo la arquitectura por capas existente: Core → Model → Repository → Service → API → Migración. Reutiliza `ReservationRepository`, `RoomRepository`, `get_current_admin_user`, `AppException` + handlers globales y `audit_log`. Incluye dos cambios acotados sobre módulos existentes (enum `ReservationStatus` y `get_active_overlapping`) documentados en el diseño. Los tests de propiedades se intercalan para validación temprana.

## Tasks

- [x] 1. Extend reservation status and core exceptions
  - [x] 1.1 Extend `ReservationStatus` enum in `app/models/reservation.py`
    - Add `CHECKED_IN = "checked_in"` and `CHECKED_OUT = "checked_out"` without removing or renaming `CONFIRMED`/`CANCELLED`
    - Do not change any column definitions
    - _Requirements: 1.1, 1.3, 1.4_

  - [x] 1.2 Add check-in/check-out domain exceptions in `app/core/exceptions.py`
    - Add `ReservationInvalidTransitionException` (409) and `CheckInDateNotAllowedException` (409, accepts an optional `detail` to distinguish early vs on/after checkout)
    - Reuse the existing `ReservationNotFoundException` (404) and `RoomNotFoundException` (404); do not create new ones
    - Do not modify `AppException` base class or existing handlers
    - _Requirements: 9.2, 9.4, 9.5, 2.4, 3.2, 3.3, 4.4_

- [x] 2. Update reservation overlap detection
  - [x] 2.1 Modify `get_active_overlapping` in `app/repositories/reservation_repository.py`
    - Change the status filter to include both `CONFIRMED` and `CHECKED_IN` (e.g. `status.in_([CONFIRMED, CHECKED_IN])`)
    - Preserve the half-open interval rule `[check_in_date, check_out_date)` unchanged
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 2.2 Write/extend unit tests for overlap with checked_in
    - `checked_in` reservation participates in overlap (blocks); `checked_out` and `cancelled` do not
    - Confirm adjacency rule (`out == in`) still not treated as overlap
    - _Requirements: 6.1, 6.2_

- [x] 3. Implement the stay service
  - [x] 3.1 Create `StayService` in `app/services/stay_service.py`
    - Constructor receives the same injected `Session` plus `ReservationRepository`, `RoomRepository`, and a `today_provider: Callable[[], date] = date.today`
    - `check_in(reservation_id)`: verify existence (404), status must be `confirmed` else `ReservationInvalidTransitionException` (409), date rule `check_in_date <= today < check_out_date` else `CheckInDateNotAllowedException` (409); set reservation → `checked_in` and room → `RoomStatus.OCUPADA`
    - `check_out(reservation_id)`: verify existence (404), status must be `checked_in` else `ReservationInvalidTransitionException` (409); set reservation → `checked_out` and room → `RoomStatus.DISPONIBLE`; allowed on/before/after planned `check_out_date`
    - Atomic commit helper: both `update` (flush) on the same session, single `session.commit()`, `session.rollback()` on failure; `audit_log("check_in"/"check_out", reservation.id, result)` (never PII)
    - Reuse `RoomRepository` to load/update the room (resolve via `reservation.room_id`; `RoomNotFoundException` if missing)
    - Never change Room status outside the two defined transitions; preserve all other reservation/guest fields
    - _Requirements: 2.1, 2.2, 2.6, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.5, 4.7, 5.1, 5.2, 5.3, 5.4, 8.2, 8.3, 11.1, 11.2, 11.3_

  - [x] 3.2 Write property test for valid check-in and date rule
    - **Property 1, 2, 3**: valid check-in (confirmed + `check_in_date <= today < check_out_date`) → reservation `checked_in`, room `ocupada`; early check-in (`today < check_in_date`) → 409, no changes; late check-in (`today >= check_out_date`) → 409, no changes
    - Inject a fixed `today_provider` for determinism
    - **Validates: Requirements 2.1, 2.2, 3.1, 3.2, 3.3**

  - [x] 3.3 Write property test for invalid check-in transitions
    - **Property 4**: for any initial status other than `confirmed` (`checked_in`, `checked_out`, `cancelled`) → check-in rejected with 409; includes double check-in
    - **Validates: Requirements 2.4**

  - [x] 3.4 Write property test for valid and invalid check-out
    - **Property 5, 6**: `checked_in` → check-out succeeds (reservation `checked_out`, room `disponible`) on any date; any other initial status → 409 (includes double check-out and check-out without check-in)
    - **Validates: Requirements 4.1, 4.2, 4.4, 4.5**

  - [x] 3.5 Write unit test for atomicity and preservation
    - **Property 7, 9**: simulate a failure on the second update → `session.rollback()` invoked and no partial state persisted; on success, id/guest_id/room_id/dates/total_price are preserved and the reservation is not deleted
    - **Validates: Requirements 5.1, 5.2, 2.6, 4.7**

- [x] 4. Checkpoint - Ensure core logic tests pass
  - Ensure all stay service and overlap tests pass so far; ask the user if questions arise.

- [x] 5. Implement the API layer
  - [x] 5.1 Add check-in/check-out endpoints in `app/api/reservations.py`
    - Add a `_get_stay_service` helper that wires `StayService(session=db, ReservationRepository(db), RoomRepository(db))`
    - `POST /api/v1/reservations/{reservation_id}/check-in` → 200, requires admin auth, returns updated reservation
    - `POST /api/v1/reservations/{reservation_id}/check-out` → 200, requires admin auth, returns updated reservation
    - Reuse `get_current_admin_user` and `get_db`; do not add new middleware
    - _Requirements: 2.5, 4.6, 7.1, 7.2, 7.4, 8.1, 10.1_

  - [x] 5.2 Confirm PATCH cannot edit status (no code change expected)
    - Verify `ReservationUpdate` (`extra="forbid"`, fields room_id/check_in_date/check_out_date only) already rejects a client-sent `status` with 422
    - Add a test asserting PATCH with `status` → 422
    - _Requirements: 7.3_

  - [x] 5.3 Write property test for authentication and authorization enforcement
    - **Property 10**: requests without JWT → 401; valid JWT non-admin → 403; on both `/check-in` and `/check-out`
    - **Validates: Requirements 10.1, 10.2, 10.3**

- [x] 6. Integration tests
  - [x] 6.1 Write integration tests for check-in/check-out endpoints
    - Use the existing integration pattern: `StaticPool` shared in-memory SQLite + `get_db` override + admin JWT; seed a room, a guest, and a `confirmed` reservation; inject/control the hotel-local date where needed
    - Cover: check-in success (200, reservation `checked_in`, room becomes `ocupada`), check-in on missing reservation (404), check-in wrong status (409), early/late check-in (409); check-out success (200, reservation `checked_out`, room becomes `disponible`), check-out wrong status (409), double check-out (409); invalid id format (422)
    - Verify error responses use the existing `{"detail", "status_code"}` format
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.2, 3.3, 4.1, 4.2, 4.3, 4.4, 4.6, 5.1, 7.4, 9.3, 9.4, 9.5_

  - [x] 6.2 Write integration test for overlap with checked_in
    - After check-in, attempting to create an overlapping reservation for the same room is rejected (409); after check-out, the range is free again
    - _Requirements: 6.1, 6.2, 6.5_

  - [x] 6.3 Write integration tests for audit log data safety
    - **Property 11**: after check-in/check-out, audit entries contain only operation, timestamp, reservation id, and result — never guest PII, tokens, or passwords
    - _Requirements: 11.1, 11.2, 11.3_

- [x] 7. Create Alembic migration to extend reservation status constraint
  - [x] 7.1 Create migration script
    - Confirm the actual current Alembic head before setting `down_revision` (do not assume `003`)
    - New revision (e.g. `004_extend_reservation_status.py`): `upgrade()` drops `ck_reservations_status` and recreates it as `status IN ('confirmed', 'checked_in', 'checked_out', 'cancelled')`; `downgrade()` restores `status IN ('confirmed', 'cancelled')`
    - _Requirements: 1.2_

- [x] 8. Final verification - Full suite and lint
  - Run `ruff check .` to confirm the whole project passes linting per `pyproject.toml`
  - Run the complete StayBook test suite (`pytest`), not only check-in/check-out tests, to confirm no regressions in Room, Guest, or Reservation Management (especially the `get_active_overlapping` change)
  - Fix any failures before considering the feature complete; ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate the correctness properties from the design document; unit tests validate specific examples and edge cases
- Reuses existing authentication (`get_current_admin_user`), exception handling (`AppException` + global handlers), audit logging (`audit_log`), database session (`get_db`, `Base`), and the existing `ReservationRepository` and `RoomRepository` — none are redesigned
- Two acotated changes to existing modules: extend `ReservationStatus` enum, and widen `get_active_overlapping` to include `checked_in`
- Atomicity: `StayService` owns the single `commit`/`rollback` over the shared injected `Session`; repositories keep doing only `flush`/`refresh`; `get_db` and `SessionLocal` are not modified
- Room status transitions use the existing `RoomStatus.OCUPADA` / `RoomStatus.DISPONIBLE` values (no new/incompatible statuses)
- Status transitions happen only via the dedicated endpoints (and existing cancel); PATCH does not expose `status`
- Out of scope: payments, invoices, refunds, housekeeping, cleaning status, key/card management, notifications, online self check-in, frontend, Docker, CI/CD, AWS
- All tests use `pytest`; property tests use `hypothesis` with `@settings(max_examples=100)`; linting uses `ruff`

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["2.2", "3.1"] },
    { "id": 3, "tasks": ["3.2", "3.3", "3.4", "3.5"] },
    { "id": 4, "tasks": ["4"] },
    { "id": 5, "tasks": ["5.1"] },
    { "id": 6, "tasks": ["5.2", "5.3"] },
    { "id": 7, "tasks": ["6.1", "6.2", "6.3", "7.1"] },
    { "id": 8, "tasks": ["8"] }
  ]
}
```
