import { createBrowserRouter, Navigate } from "react-router-dom";

import AdminLayout from "../layout/AdminLayout.jsx";
import NotFound from "../components/NotFound.jsx";
import LoginPage from "../pages/LoginPage.jsx";
import DashboardPage from "../pages/DashboardPage.jsx";
import RoomsPage from "../pages/RoomsPage.jsx";
import GuestsPage from "../pages/GuestsPage.jsx";
import ReservationsPage from "../pages/ReservationsPage.jsx";
import AvailabilityPage from "../pages/AvailabilityPage.jsx";
import HistoryPage from "../pages/HistoryPage.jsx";

/**
 * Definición central del árbol de rutas de la Aplicación_Frontend.
 *
 * Estructura (Req 3.1, 3.2, 3.3, 3.4, 3.5, 4.6):
 * - `/login` → LoginPage, renderizada FUERA del AdminLayout (sin sidebar).
 * - `/` → AdminLayout (layout persistente) con las secciones administrativas
 *   como hijas anidadas renderizadas vía <Outlet/>:
 *     - index → redirección a `/dashboard`.
 *     - dashboard, rooms, guests, reservations, availability, history.
 * - `*` → NotFound (404 genérico, no rompe la app).
 *
 * Preparación para autenticación (Req 3.6, 9.1): el grupo administrativo es un
 * único nodo padre (AdminLayout). Cuando se implemente la autenticación, se
 * insertará aquí un envoltorio <ProtectedRoute> que redirija a `/login` si no
 * hay sesión, sin necesidad de mover las rutas hijas. En esta fase de
 * foundation NO se bloquea el acceso (Req 9.5): todas las rutas permanecen
 * accesibles para validar la base.
 */
/**
 * Array de definición de rutas, exportado por separado para permitir su reuso
 * en pruebas en memoria (`createMemoryRouter(routes, ...)`) sin depender de la
 * instancia de navegador. `router` se construye a partir de este mismo array,
 * de modo que las pruebas ejercitan exactamente el árbol usado en producción.
 */
export const routes = [
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/",
    // FUTURE: wrap <AdminLayout/> in <ProtectedRoute> here to guard admin
    // routes (see Req 3.6, 9.1). No auth enforcement in this phase (Req 9.5).
    element: <AdminLayout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "rooms", element: <RoomsPage /> },
      { path: "guests", element: <GuestsPage /> },
      { path: "reservations", element: <ReservationsPage /> },
      { path: "availability", element: <AvailabilityPage /> },
      { path: "history", element: <HistoryPage /> },
    ],
  },
  {
    path: "*",
    element: <NotFound />,
  },
];

export const router = createBrowserRouter(routes);
