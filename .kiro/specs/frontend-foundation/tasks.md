# Implementation Plan: Frontend Foundation

## Overview

Inicialización de la base del frontend administrativo de StayBook (React + Vite + JavaScript) en `/frontend`: estructura de proyecto, ruteo con React Router, layout principal con sidebar/header, capa centralizada de cliente de API, configuración de entorno, patrones genéricos de carga/error, páginas placeholder, estilos CSS ligeros, y una tarea de integración para habilitar CORS en el backend FastAPI existente. No se implementa funcionalidad de negocio, login/JWT, state global, Docker ni CI/CD.

## Tasks

- [x] 0. Backend integration — configure FastAPI CORS for the frontend origin
  - [x] 0.1 Add `CORSMiddleware` to `app/main.py`
    - Import `CORSMiddleware` from `fastapi.middleware.cors`
    - Add the middleware with: explicit allowed origins list (at minimum `http://localhost:5173` for local dev), allowed methods `GET, POST, PATCH, DELETE, OPTIONS`, allowed headers including `Content-Type` and `Authorization`, and `allow_credentials=True`
    - Do NOT use `"*"` for origins (incompatible with credentials/authorization)
    - Keep the configuration centralized in `app/main.py`; optionally read allowed origins from an environment variable (e.g. `CORS_ORIGINS`) for future flexibility, with a sensible development default
    - Do not modify backend business logic, routers, services, repositories, models or migrations
    - Run the existing backend test suite (`pytest`) and `ruff check .` to confirm no regressions
    - _Requirements: 10.2, 10.3, 10.4_

- [x] 1. Initialize the React + Vite project in `/frontend`
  - [x] 1.1 Scaffold the Vite + React project
    - Run the Vite initializer (or create manually) in `/frontend` with React + JavaScript (not TypeScript)
    - Ensure `package.json` lists `react`, `react-dom`, `react-router-dom`, `vite`, `@vitejs/plugin-react` as the core dependencies
    - Do not add Redux, Zustand, MUI, Bootstrap, Tailwind or other heavy libraries
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 1.2 Create the project directory structure
    - Arrange the `src/` tree as defined in the design: `router/`, `config/`, `api/`, `auth/`, `layout/`, `components/`, `hooks/`, `pages/`, `styles/`
    - Each folder contains at minimum a placeholder file or its final module stub so the structure is committed to the repo
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 1.3 Configure `.gitignore` and `.env.example`
    - Create `/frontend/.gitignore` ignoring `node_modules/`, `dist/`, `.env`, `.env.local`, `.env.*` (with `!.env.example`)
    - Create `/frontend/.env.example` documenting `VITE_API_BASE_URL=http://127.0.0.1:8000`
    - _Requirements: 1.6, 7.2, 7.4_

  - [x] 1.4 Verify `npm run dev` and `npm run build` succeed
    - After scaffolding, confirm the Vite dev server starts and the production build completes without errors
    - _Requirements: 1.4, 1.5_

- [x] 2. Environment configuration module
  - [x] 2.1 Create `src/config/env.js`
    - Export `getApiBaseUrl()` that reads `import.meta.env.VITE_API_BASE_URL` with fallback `http://127.0.0.1:8000`
    - Strip trailing slashes for consistent URL construction
    - _Requirements: 7.1, 7.3, 7.5_

- [x] 3. Centralized API client
  - [x] 3.1 Create `src/api/ApiError.js`
    - Export `ApiError` class extending `Error` with `kind` (`"http"` | `"network"`), `status`, `detail`, `payload`, `cause`
    - _Requirements: 6.4, 8.3_

  - [x] 3.2 Create `src/api/client.js`
    - Export `apiGet(path, opts)`, `apiPost(path, body, opts)`, `apiPatch(path, body, opts)` that call an internal `request(method, path, ...)` function
    - `request` builds the full URL from `getApiBaseUrl() + path`, sets `Content-Type: application/json`, calls `authHeader()` for the `Authorization` header, and serializes `body` as JSON
    - On fetch failure (network error / CORS block) → throw `ApiError { kind: "network" }`
    - On HTTP 4xx/5xx → parse JSON body, extract `detail`, throw `ApiError { kind: "http", status, detail, payload }`
    - On HTTP 204 → return `null`
    - On success → parse and return JSON body
    - Support an `AbortSignal` (`opts.signal`) for cancellation
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 8.3, 8.4_

  - [x] 3.3 Create `src/api/endpoints.js`
    - Export an `ENDPOINTS` object with path constants for all known backend routes (`/api/v1/rooms/`, `/api/v1/guests/`, `/api/v1/reservations/`, `/api/v1/availability`, `/api/v1/occupancy/current`, `/api/v1/occupancy/rooms`, `/api/v1/history/reservations`, etc.), including parameterized helpers like `room(id)`
    - _Requirements: 6.2, 6.5_

  - [x] 3.4 Create `src/auth/authToken.js`
    - Export `getToken()` returning `null` (stub for future JWT implementation)
    - Export `authHeader()` returning `{ Authorization: "Bearer <token>" }` if `getToken()` returns a truthy value, otherwise an empty object
    - This is the **single future extension point** for authentication
    - _Requirements: 6.3, 9.2_

- [x] 4. Layout and navigation
  - [x] 4.1 Create `src/layout/AdminLayout.jsx`
    - Compose `Header`, `Sidebar`, and a content area rendering `<Outlet/>` (React Router nested route output)
    - Use CSS Flexbox or Grid for the three regions
    - _Requirements: 4.1, 4.3_

  - [x] 4.2 Create `src/layout/Sidebar.jsx`
    - Render `<NavLink>` items for: Dashboard, Rooms, Guests, Reservations, Availability, History
    - `NavLink` applies an active CSS class on the current route
    - _Requirements: 4.2, 4.4_

  - [x] 4.3 Create `src/layout/Header.jsx`
    - Show the application title (e.g. "StayBook")
    - Reserve a slot (e.g. an empty `<div>` or placeholder) for future session actions (logout button), without implementing logic
    - _Requirements: 4.5_

  - [x] 4.4 Create base styles in `src/styles/`
    - `index.css`: minimal reset, CSS custom properties (colors, spacing, fonts), base typography; imported once in `main.jsx`
    - `layout.css`: styles for `AdminLayout`, `Sidebar`, `Header`, active `NavLink` state, and a basic `@media` breakpoint for reduced-width graceful degradation
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [ ] 5. Reusable components and hooks
  - [x] 5.1 Create `src/components/Loading.jsx`
    - Generic loading indicator (spinner or "Cargando…" text), accepts an optional `label` prop
    - _Requirements: 8.1, 8.5_

  - [x] 5.2 Create `src/components/ErrorMessage.jsx`
    - Accepts an `error` prop (expects `ApiError` or a plain object/string)
    - For `kind: "network"` shows "No se pudo conectar con el servidor"
    - For `kind: "http"` shows `error.detail`
    - Never shows stack traces or internal details
    - _Requirements: 8.2, 8.3, 8.6_

  - [x] 5.3 Create `src/components/NotFound.jsx`
    - "Página no encontrada" content with a link back to `/dashboard`
    - _Requirements: 3.5, 11.5_

  - [x] 5.4 Create `src/components/PlaceholderPage.jsx`
    - Accepts `title` and optional `description` props; renders a section with the title and a "funcionalidad pendiente" message
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 5.5 Create `src/hooks/useApi.js`
    - Generic hook returning `{ data, loading, error, run }` that wraps an async API-client call
    - Manages loading/error/data state with `useState`; supports `AbortController` cleanup
    - In this foundation, the hook exists as a reusable pattern but is not wired to business calls
    - _Requirements: 8.5_

- [x] 6. Routing and placeholder pages
  - [x] 6.1 Create the seven placeholder pages in `src/pages/`
    - `LoginPage.jsx` (title "Iniciar sesión", no auth logic), `DashboardPage.jsx`, `RoomsPage.jsx`, `GuestsPage.jsx`, `ReservationsPage.jsx`, `AvailabilityPage.jsx`, `HistoryPage.jsx`
    - Each uses `PlaceholderPage` with an identifying title
    - None contain business logic or real API calls
    - _Requirements: 5.1, 5.2, 5.3, 9.3_

  - [x] 6.2 Create `src/router/routes.jsx`
    - Define the route tree using React Router objects/JSX:
      - `/login` → `LoginPage` (outside `AdminLayout`)
      - `/` → `AdminLayout` (parent):
        - `index` → `<Navigate to="/dashboard" replace />`
        - `/dashboard` → `DashboardPage`
        - `/rooms` → `RoomsPage`
        - `/guests` → `GuestsPage`
        - `/reservations` → `ReservationsPage`
        - `/availability` → `AvailabilityPage`
        - `/history` → `HistoryPage`
      - `*` → `NotFound`
    - Include a code comment marking the exact location where a future `ProtectedRoute` wrapper will be inserted to protect the administrative routes
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.6, 9.1_

  - [x] 6.3 Wire `src/main.jsx` and `src/App.jsx`
    - `main.jsx`: import React, ReactDOM, `index.css`, and render `<App />` (or `<RouterProvider>`)
    - `App.jsx`: mount the router from `routes.jsx`
    - _Requirements: 1.4, 3.1_

- [x] 7. Connectivity verification
  - [x] 7.1 Create `src/api/connectivity.js`
    - Export `checkBackendConnectivity()` that calls `apiGet("/openapi.json")` (public, no JWT required) and returns `{ reachable: true }` on any 2xx or `{ reachable: false, error }` on failure
    - _Requirements: 10.1_

  - [x] 7.2 Add a connectivity indicator to `DashboardPage`
    - On mount, call `checkBackendConnectivity()` and display a small status badge ("Backend alcanzable" / "Backend no alcanzable") — demonstrating that React can communicate with FastAPI over the configured base URL through the centralized API client
    - This is a foundation-only demonstration; it will be replaced by actual dashboard content in a future spec
    - _Requirements: 10.1, 8.4_

- [x] 8. Checkpoint - Verify the foundation manually
  - Start the backend (`uvicorn`) and the frontend dev server (`npm run dev`)
  - Navigate to each route and confirm: sidebar renders, active link highlights, placeholder pages show titles, `/` redirects to `/dashboard`, unknown route shows 404, `/login` renders without sidebar
  - Confirm the Dashboard connectivity indicator shows "Backend alcanzable"
  - Confirm `npm run build` succeeds
  - Ask the user if questions arise

- [x] 9. Foundation tests
  - [x] 9.1 Add Vitest + React Testing Library
    - Add `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, and `jsdom` as dev dependencies
    - Configure Vitest in `vite.config.js` (or `vitest.config.js`) with `environment: "jsdom"`
    - _Requirements: (testing infrastructure)_

  - [x] 9.2 Write routing tests
    - Render the router in memory (MemoryRouter); verify `/dashboard`, `/rooms`, `/guests`, `/reservations`, `/availability`, `/history` each mount their placeholder title; `/` redirects to `/dashboard`; unknown route shows NotFound; `/login` renders without `Sidebar`
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 4.6_

  - [x] 9.3 Write layout/navigation tests
    - `Sidebar` renders all six nav links; `NavLink` active state reflects the current route; `Header` renders title and session slot
    - _Requirements: 4.2, 4.4, 4.5_

  - [x] 9.4 Write API client tests
    - Mock `fetch` globally; verify `apiGet`/`apiPost`/`apiPatch` build URLs from the configured base; 4xx/5xx produces `ApiError` with `status` and `detail`; 204 returns `null`; fetch rejection produces `ApiError { kind: "network" }`; `authHeader()` returns empty when `getToken()` is null and `{ Authorization: "Bearer t" }` when stubbed
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 8.3, 8.4_

  - [x] 9.5 Write config/env test
    - `getApiBaseUrl()` returns `VITE_API_BASE_URL` when defined, falls back to `http://127.0.0.1:8000` when not, and strips trailing slashes
    - _Requirements: 7.1, 7.3_

  - [x] 9.6 Write component tests
    - `Loading` renders its indicator; `ErrorMessage` shows network message vs. HTTP detail and never stack traces; `PlaceholderPage` renders title and description; `NotFound` renders link to dashboard
    - _Requirements: 8.1, 8.2, 8.6, 5.2, 3.5_

  - [x] 9.7 Write connectivity test
    - Mock `fetch`; `checkBackendConnectivity()` returns `{ reachable: true }` on 200 and `{ reachable: false }` on network error
    - _Requirements: 10.1_

- [x] 10. Final verification
  - Run `npm test` (Vitest) in `/frontend` and ensure all foundation tests pass
  - Run `npm run build` and confirm a clean production build
  - Run backend `ruff check .` and `pytest` to confirm the CORS change caused no regressions
  - Verify no Docker, CI/CD, AWS, Terraform files were created
  - Verify no business logic, login/JWT implementation, or state management library was added
  - Ask the user if questions arise

## Notes

- Task 0 is the only backend change: adding `CORSMiddleware` to `app/main.py`, with no business-logic modifications. The rest is frontend-only in `/frontend`.
- CORS configuration explicitly allows the local frontend origin (`http://localhost:5173`), not `"*"`, to be compatible with credentials/authorization. Origins should be environment-configurable for future environments.
- `VITE_API_BASE_URL=http://127.0.0.1:8000` is the primary frontend→backend connection strategy. The Vite proxy is not required; it may be documented in the README as an optional developer convenience.
- JWT authentication is **not** implemented: `getToken()` returns `null`, `authHeader()` returns `{}`. The extension point is in `src/auth/authToken.js`.
- No business CRUD, no validation duplication, no global state library, no UI framework.
- No Docker, AWS, Terraform, CI/CD work.
- Vitest + React Testing Library for lightweight foundation-appropriate testing.
- Each task references specific requirements for traceability.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["0.1", "1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3"] },
    { "id": 2, "tasks": ["1.4", "2.1"] },
    { "id": 3, "tasks": ["3.1", "3.2", "3.3", "3.4"] },
    { "id": 4, "tasks": ["4.1", "4.2", "4.3", "4.4", "5.1", "5.2", "5.3", "5.4", "5.5"] },
    { "id": 5, "tasks": ["6.1", "6.2"] },
    { "id": 6, "tasks": ["6.3", "7.1"] },
    { "id": 7, "tasks": ["7.2"] },
    { "id": 8, "tasks": ["8"] },
    { "id": 9, "tasks": ["9.1"] },
    { "id": 10, "tasks": ["9.2", "9.3", "9.4", "9.5", "9.6", "9.7"] },
    { "id": 11, "tasks": ["10"] }
  ]
}
```
