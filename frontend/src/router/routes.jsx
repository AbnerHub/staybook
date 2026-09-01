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
 * Array de definición de rutas, exportado por separado para permitir su reuso
 * en pruebas en memoria (`createMemoryRouter(routes, ...)`). `router` se
 * construye a partir de este mismo array.
 */
export const routes = [
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/",
    // FUTURE: wrap <AdminLayout/> in <ProtectedRoute> here to guard admin
    // routes. No auth enforcement in this phase.
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
