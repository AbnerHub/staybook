x|  # Implementation Plan: Guest Management

## Overview

Implementación del módulo de administración de huéspedes (registro, consulta, listado y actualización, sin eliminación) para StayBook siguiendo la arquitectura por capas existente: Core → Model/Schemas → Repository → Service → API → Migración. Cada tarea construye sobre la anterior de forma incremental, reutilizando los patrones ya establecidos por Room Management. Los tests de propiedades se intercalan para validación temprana.

## Tasks

- [x] 1. Set up dependencies and core layer extensions
  - [x] 1.1 Add `email-validator` dependency
    - Add `email-validator` (o `pydantic[email]`) to `requirements.txt` to enable `EmailStr` validation
    - Do not modify existing pinned dependencies or project configuration
    - _Requirements: 1.1, 1.4_

  - [x] 1.2 Add guest domain exceptions in `app/core/exceptions.py`
    - Add `GuestNotFoundException` (404), `GuestEmailDuplicateException` (409), `GuestIdentificationDuplicateException` (409) as subclasses of the existing `AppException`
    - Do not modify `AppException` base class or existing Room exceptions
    - _Requirements: 7.4, 7.5, 1.2, 1.3_

  - [x] 1.3 Reuse existing audit logging in `app/core/logging.py` (Option A — no rename)
    - Keep the existing `audit_log(operation, room_id, result)` signature untouched to avoid breaking Room Management tests
    - `GuestService` calls `audit_log` positionally with the guest id, exactly like `RoomService`, so no signature change is required
    - Ensure the log never records tokens, passwords, or guest PII (email, phone, identification number) — only operation, timestamp, id, and result
    - _Requirements: 9.1, 9.2_

- [x] 2. Create data model and schemas
  - [x] 2.1 Create SQLAlchemy model in `app/models/guest.py`
    - Define `IdentificationType` enum (national_id, passport, driver_license, other)
    - Define `Guest` model inheriting from the existing `Base` with columns: id, first_name (100), last_name (100), email (255, unique, indexed), phone (20), identification_type, identification_number (50), created_at, updated_at (timestamps with `server_default=func.now()` and `onupdate=func.now()`)
    - Add `UniqueConstraint("identification_type", "identification_number", name="uq_guests_identification")` via `__table_args__`
    - _Requirements: 1.1, 5.2, 5.4_

  - [x] 2.2 Create Pydantic schemas in `app/schemas/guest.py`
    - `GuestCreate`: first_name (1–100), last_name (1–100), email (`EmailStr`, max 255), phone (7–20), identification_type, identification_number (1–50)
    - `GuestUpdate`: all fields optional with the same constraints
    - `GuestResponse`: all fields with `ConfigDict(from_attributes=True)`
    - Add a validator that strips whitespace on first_name, last_name and identification_number and rejects empty results (prevents whitespace-only values)
    - _Requirements: 1.1, 1.4, 4.1, 4.3, 5.4_

  - [x] 2.3 Write property test for invalid input rejection
    - **Property 4: Invalid input rejection**
    - Generate guest data with at least one invalid field (empty/over-length name, invalid/over-length email, phone outside 7–20, empty/over-length identification_number, type outside enum) and assert Pydantic raises `ValidationError` without persisting
    - **Validates: Requirements 1.4, 4.3**

- [x] 3. Implement repository layer
  - [x] 3.1 Create guest repository in `app/repositories/guest_repository.py`
    - Implement `GuestRepository` with a SQLAlchemy `Session` dependency, mirroring `RoomRepository` style (`flush`/`refresh`, `db.get` by PK)
    - Methods: `create`, `get_by_id`, `get_by_email`, `get_by_identification(identification_type, identification_number)`, `get_all`, `update`
    - Do not implement a `delete` method (guests are preserved) and no business rules
    - _Requirements: 6.3, 2.1, 5.1_

  - [x] 3.2 Write unit tests for repository
    - Test create/get_by_id/get_all/update with in-memory SQLite
    - Test `get_by_email` and `get_by_identification` return None for non-existent values and the correct record when present
    - _Requirements: 2.1, 6.3_

- [x] 4. Implement service layer
  - [x] 4.1 Create guest service in `app/services/guest_service.py`
    - Implement `GuestService` with a `GuestRepository` dependency, mirroring `RoomService`
    - `create_guest`: reject duplicate email (`GuestEmailDuplicateException`) and duplicate (type, number) (`GuestIdentificationDuplicateException`); call `audit_log("create", guest.id, ...)` on completion
    - `list_guests`: delegate to repository `get_all`
    - `get_guest`: get by ID → raise `GuestNotFoundException` if not found
    - `update_guest`: verify existence, check email and identification uniqueness only when the incoming value differs from the current one, apply only provided fields (`exclude_unset`), preserve id and created_at, call `audit_log("update", guest.id, ...)`
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 3.2, 4.1, 4.2, 4.4, 4.5, 5.2, 5.3, 5.4, 9.1_

  - [x] 4.2 Write property test for guest creation round-trip
    - **Property 1: Guest creation round-trip**
    - For any valid guest data, create then retrieve by ID → all fields match
    - **Validates: Requirements 1.1, 3.1**

  - [x] 4.3 Write property test for duplicate email rejection
    - **Property 2: Duplicate email rejection**
    - For any two creation/update attempts with the same email, the second is rejected and the first remains unchanged
    - **Validates: Requirements 1.2, 4.4**

  - [x] 4.4 Write property test for duplicate identification rejection
    - **Property 3: Duplicate identification rejection**
    - For any two creation/update attempts with the same (identification_type, identification_number), the second is rejected
    - **Validates: Requirements 1.3, 4.5**

  - [x] 4.5 Write property test for partial update field preservation
    - **Property 5: Partial update field preservation**
    - For any guest and any subset of fields, update only those fields → other fields remain unchanged, including id and created_at
    - **Validates: Requirements 4.1, 5.3**

  - [x] 4.6 Write property test for list completeness invariant
    - **Property 6: List completeness invariant**
    - For N inserted guests, list_guests returns exactly N guests with all attributes intact
    - **Validates: Requirements 2.1**

- [x] 5. Checkpoint - Ensure core logic tests pass
  - Ensure all guest unit and property tests pass so far; ask the user if questions arise.

- [x] 6. Implement API layer
  - [x] 6.1 Create guest router in `app/api/guests.py`
    - Reuse the existing `get_current_admin_user` dependency and `get_db` session; add a `_get_service` helper like in `app/api/rooms.py`
    - `POST /api/v1/guests` → 201, validate with `GuestCreate`, requires admin auth
    - `GET /api/v1/guests` → 200, returns list of all guests, requires admin auth
    - `GET /api/v1/guests/{guest_id}` → 200, returns single guest, requires admin auth
    - `PATCH /api/v1/guests/{guest_id}` → 200, partial update with `GuestUpdate`, requires admin auth
    - Do not add a DELETE endpoint
    - _Requirements: 1.5, 2.2, 2.3, 3.1, 3.3, 3.4, 4.6, 6.1, 8.1_

  - [x] 6.2 Register guest router in `app/main.py`
    - Include the guest router via `app.include_router(...)`
    - Do not modify the already-registered exception handlers; they already cover guest `AppException` subclasses
    - _Requirements: 6.1, 7.2_

  - [x] 6.3 Write property test for authentication and authorization enforcement
    - **Property 7: Authentication and authorization enforcement**
    - Requests without JWT → 401; requests with valid JWT but non-admin role → 403; no guest data accessible without valid admin credentials
    - **Validates: Requirements 8.1, 8.2, 8.3**

- [x] 7. Integration tests
  - [x] 7.1 Write integration tests for guest API endpoints
    - Test full request/response cycle for POST (201), GET list (200 + empty list), GET by id (200/404), PATCH (200/404/409/422) using the existing test client and JWT mock fixtures
    - Verify error responses use the existing `{"detail", "status_code"}` format from the global handlers
    - _Requirements: 1.5, 2.2, 2.3, 3.1, 3.2, 4.2, 4.6, 7.2, 7.4, 7.5_

  - [x] 7.2 Write integration tests for audit log data safety
    - **Property 8: Audit log data safety**
    - After create/update operations, verify audit log entries contain only operation, timestamp, guest_id (entity_id), and result — never email, phone, identification number, tokens, or passwords
    - _Requirements: 9.1, 9.2_

- [x] 8. Create Alembic migration for guests table
  - [x] 8.1 Create Alembic migration script
    - New revision (e.g. `002_create_guests_table.py`) with `down_revision = "001"`, mirroring the style of `001_create_rooms_table.py`
    - `upgrade()` creates the `guests` table with all columns, `PrimaryKeyConstraint("id")`, `UniqueConstraint("email")`, `UniqueConstraint("identification_type", "identification_number", name="uq_guests_identification")`, and a `CheckConstraint` for `identification_type` values
    - Create index `ix_guests_email`; `downgrade()` drops the index and table in reverse order
    - _Requirements: 1.1, 5.2_

- [x] 9. Final verification - Full suite and lint
  - Run the complete StayBook test suite (`pytest tests/`), not only guest tests, to confirm no regressions in Room Management
  - Run `ruff check .` to confirm the whole project passes linting per `pyproject.toml`
  - Fix any failures before considering the feature complete; ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document; unit tests validate specific examples and edge cases
- The implementation reuses the existing authentication (`get_current_admin_user`), exception handling (`AppException` + global handlers), database configuration (`get_db`, `Base`) and layered architecture — none of these are redesigned
- No DELETE endpoint or repository delete is implemented; guests are preserved for future reservation history
- Out of scope: reservations, check-in, check-out, payments, Docker, CI/CD, AWS
- All tests use `pytest`; property tests use `hypothesis` with `@settings(max_examples=100)`; linting uses `ruff`

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["2.2", "3.1", "8.1"] },
    { "id": 3, "tasks": ["2.3", "3.2", "4.1"] },
    { "id": 4, "tasks": ["4.2", "4.3", "4.4", "4.5", "4.6"] },
    { "id": 5, "tasks": ["6.1"] },
    { "id": 6, "tasks": ["6.2"] },
    { "id": 7, "tasks": ["6.3", "7.1", "7.2"] },
    { "id": 8, "tasks": ["9"] }
  ]
}
```
