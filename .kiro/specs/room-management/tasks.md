# Implementation Plan: Room Management

## Overview

Implementación del módulo de administración de habitaciones (CRUD completo) para StayBook siguiendo la arquitectura por capas: Core → Models/Schemas → Repository → Service → API. Cada tarea construye sobre la anterior de forma incremental, con tests de propiedades intercalados para validación temprana.

## Tasks

- [x] 1. Set up core layer (exceptions, config, logging, auth)
  - [x] 1.1 Create custom exceptions in `app/core/exceptions.py`
    - Implement `AppException` base class with `detail` and `status_code` fields
    - Implement `RoomNotFoundException` (404), `RoomDuplicateException` (409), `RoomOccupiedException` (409)
    - _Requirements: 8.1, 8.2, 8.4, 8.5_

  - [x] 1.2 Create exception handlers in `app/core/exception_handlers.py`
    - Implement `app_exception_handler` for `AppException` subclasses → JSON with `detail` and `status_code`
    - Implement `generic_exception_handler` for unhandled `Exception` → 500 with generic message, never exposing internals
    - _Requirements: 8.1, 8.2_

  - [x] 1.3 Create configuration module in `app/core/config.py`
    - Implement `Settings` class using `pydantic_settings.BaseSettings`
    - Load `database_url`, `secret_key`, `jwt_algorithm`, `jwt_expiration_minutes`, `app_port`, `debug` from environment
    - _Requirements: 11.1, 11.2_

  - [x] 1.4 Create audit logging module in `app/core/logging.py`
    - Implement `audit_log(operation, room_id, result)` function
    - Log timestamp, operation type, room_id, and result — never log tokens, passwords, or PII
    - _Requirements: 10.1, 10.2_

  - [x] 1.5 Create authentication dependency in `app/core/auth.py`
    - Implement `get_current_user` using `HTTPBearer` to decode/validate JWT
    - Implement `get_current_admin_user` that verifies `role == "admin"`
    - Return HTTP 401 for missing/invalid/expired tokens, HTTP 403 for non-admin users
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 2. Create data models and schemas
  - [x] 2.1 Create SQLAlchemy model in `app/models/room.py`
    - Define `RoomType` enum (individual, doble, suite) and `RoomStatus` enum (disponible, ocupada, mantenimiento)
    - Define `Room` model with columns: id, room_number (unique, indexed), room_type, price_per_night, capacity, status (default disponible), description, floor, created_at, updated_at
    - _Requirements: 1.1, 7.4_

  - [x] 2.2 Create Pydantic schemas in `app/schemas/room.py`
    - `RoomCreate`: room_number (max 10), room_type, price_per_night (0.01–999999.99), capacity (1–20), status (default disponible), description (optional, max 255), floor (optional)
    - `RoomUpdate`: all fields optional with same constraints
    - `RoomResponse`: all fields with `from_attributes=True`
    - _Requirements: 1.1, 1.3, 4.1, 4.3, 6.1_

  - [x] 2.3 Write property test for invalid input rejection
    - **Property 3: Invalid input rejection**
    - Generate room data with at least one invalid field (price ≤ 0, capacity < 1 or > 20, room_number > 10 chars) and assert Pydantic rejects it with `ValidationError`
    - **Validates: Requirements 1.3, 4.3**

- [x] 3. Implement repository layer
  - [x] 3.1 Create room repository in `app/repositories/room_repository.py`
    - Implement `RoomRepository` class with SQLAlchemy `Session` dependency
    - Methods: `create`, `get_by_id`, `get_by_room_number`, `get_all`, `get_available` (filter by status=disponible), `update`, `delete`
    - _Requirements: 7.3, 7.4_

  - [x] 3.2 Write unit tests for repository
    - Test CRUD operations with in-memory SQLite
    - Test `get_available` returns only rooms with status "disponible"
    - Test `get_by_room_number` returns None for non-existent numbers
    - _Requirements: 2.1, 3.1, 7.3_

- [x] 4. Implement service layer
  - [x] 4.1 Create room service in `app/services/room_service.py`
    - Implement `RoomService` with `RoomRepository` dependency
    - `create_room`: check uniqueness of room_number → raise `RoomDuplicateException` if exists, set default status "disponible", call audit_log on success
    - `list_rooms`: delegate to repository `get_all`
    - `list_available_rooms`: delegate to repository `get_available`
    - `get_room`: get by ID → raise `RoomNotFoundException` if not found
    - `update_room`: verify existence, check room_number uniqueness on change, apply only provided fields (`exclude_unset`), call audit_log
    - `delete_room`: verify existence, reject if status "ocupada" (`RoomOccupiedException`), hard delete, call audit_log
    - _Requirements: 1.1, 1.2, 2.1, 3.1, 4.1, 4.4, 5.1, 5.3, 5.4, 5.6, 7.2_

  - [x] 4.2 Write property test for room creation round-trip
    - **Property 1: Room creation round-trip**
    - For any valid room data, create then retrieve by ID → all fields match, status defaults to "disponible" when not set
    - **Validates: Requirements 1.1, 6.1**

  - [x] 4.3 Write property test for duplicate room number rejection
    - **Property 2: Duplicate room number rejection**
    - For any two creation/update attempts with same room_number, the second is rejected and the first remains unchanged
    - **Validates: Requirements 1.2, 4.4**

  - [x] 4.4 Write property test for availability filter correctness
    - **Property 4: Availability filter correctness**
    - Insert rooms with mixed statuses → list_available returns exactly rooms with status "disponible"
    - **Validates: Requirements 3.1, 3.2**

  - [x] 4.5 Write property test for partial update field preservation
    - **Property 5: Partial update field preservation**
    - For any room and any subset of fields, update only those fields → other fields remain unchanged
    - **Validates: Requirements 4.1**

  - [x] 4.6 Write property test for deletion rules by room status
    - **Property 6: Deletion rules by room status**
    - Deletion succeeds iff status ≠ "ocupada"; rooms with "disponible" or "mantenimiento" can be deleted
    - **Validates: Requirements 5.1, 5.3, 5.4**

  - [x] 4.7 Write property test for list completeness invariant
    - **Property 7: List completeness invariant**
    - For N inserted rooms, list_rooms returns exactly N rooms with all attributes intact
    - **Validates: Requirements 2.1**

- [x] 5. Checkpoint - Ensure core logic tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement API layer
  - [x] 6.1 Create database session dependency in `app/db/session.py`
    - Configure SQLAlchemy engine and session factory from `settings.database_url`
    - Create `get_db` dependency that yields a session and handles cleanup
    - _Requirements: 11.2, 7.4_

  - [x] 6.2 Create room router in `app/api/rooms.py`
    - `POST /api/v1/rooms` → 201, validate with `RoomCreate`, requires admin auth
    - `GET /api/v1/rooms` → 200, returns list of all rooms, requires admin auth
    - `GET /api/v1/rooms/available` → 200, returns available rooms, requires admin auth
    - `GET /api/v1/rooms/{room_id}` → 200, returns single room, requires admin auth
    - `PATCH /api/v1/rooms/{room_id}` → 200, partial update with `RoomUpdate`, requires admin auth
    - `DELETE /api/v1/rooms/{room_id}` → 204, hard delete, requires admin auth
    - _Requirements: 1.4, 2.2, 2.3, 3.3, 4.5, 5.5, 6.3, 7.1, 9.4_

  - [x] 6.3 Register router and exception handlers in `app/main.py`
    - Create FastAPI app instance
    - Register `app_exception_handler` for `AppException`
    - Register `generic_exception_handler` for `Exception`
    - Include room router
    - _Requirements: 7.1, 8.1, 10.3_

  - [x] 6.4 Write property test for authentication and authorization enforcement
    - **Property 8: Authentication and authorization enforcement**
    - Requests without JWT → 401; requests with valid JWT but non-admin role → 403; no room data accessible without valid admin credentials
    - **Validates: Requirements 9.1, 9.2, 9.3**

- [x] 7. Integration tests and error safety
  - [ ]* 7.1 Write integration tests for error response safety
    - **Property 9: Error response safety**
    - Simulate unhandled exceptions → verify response contains only generic message, never exposes stack traces, SQL, or server addresses
    - _Requirements: 8.1, 8.2_

  - [x] 7.2 Write integration tests for audit log data safety
    - **Property 10: Audit log data safety**
    - After create/update/delete operations, verify audit log entries contain only operation, timestamp, room_id, and result — never tokens or passwords
    - _Requirements: 10.1, 10.2_

- [x] 8. Create Alembic migration for rooms table
  - [x] 8.1 Create Alembic migration script
    - Generate migration to create `rooms` table with all columns, constraints (CHECK for enums, price, capacity), indexes on `room_number` and `status`
    - _Requirements: 1.1, 7.3, 7.4_

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The implementation uses Python 3.13 with FastAPI, SQLAlchemy, Pydantic, and Hypothesis for PBT
- All tests use `pytest` as runner; property tests use `hypothesis` with `@settings(max_examples=100)`
- Core layer is built first to provide shared utilities (exceptions, config, auth) for all subsequent layers

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.3", "1.4"] },
    { "id": 1, "tasks": ["1.2", "1.5", "2.1"] },
    { "id": 2, "tasks": ["2.2", "3.1"] },
    { "id": 3, "tasks": ["2.3", "3.2", "4.1"] },
    { "id": 4, "tasks": ["4.2", "4.3", "4.4", "4.5", "4.6", "4.7"] },
    { "id": 5, "tasks": ["6.1", "8.1"] },
    { "id": 6, "tasks": ["6.2"] },
    { "id": 7, "tasks": ["6.3"] },
    { "id": 8, "tasks": ["6.4", "7.1", "7.2"] }
  ]
}
```
