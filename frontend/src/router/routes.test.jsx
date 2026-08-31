import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

import { routes } from "./routes.jsx";

// El DashboardPage dispara una verificación de conectividad al montarse
// (checkBackendConnectivity → apiGet → fetch). En las pruebas de ruteo no
// queremos golpear la red ni generar advertencias, por lo que mockeamos el
// módulo de conectividad para devolver un resultado resuelto de inmediato.
vi.mock("../api/connectivity.js", () => ({
  checkBackendConnectivity: vi.fn().mockResolvedValue({ reachable: true }),
}));

/**
 * Renderiza el árbol de rutas real en memoria en la ruta indicada.
 * Usa `createMemoryRouter(routes, ...)` para ejercitar exactamente el mismo
 * array de rutas que consume la app en producción (Req 3.1).
 */
function renderAt(initialPath) {
  const testRouter = createMemoryRouter(routes, {
    initialEntries: [initialPath],
  });
  return render(<RouterProvider router={testRouter} />);
}

describe("router (rutas del lado del cliente)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // Req 3.2 / 3.3: cada ruta administrativa monta su Página_Placeholder
  // dentro del Layout_Principal, mostrando su título identificable.
  it.each([
    ["/dashboard", "Dashboard"],
    ["/rooms", "Rooms"],
    ["/guests", "Guests"],
    ["/reservations", "Reservations"],
    ["/availability", "Availability"],
    ["/history", "History"],
  ])("monta la página placeholder de %s con su título", async (path, title) => {
    renderAt(path);
    // `findBy*` espera a que se resuelvan las actualizaciones asíncronas de
    // estado (p. ej. el indicador de conectividad del Dashboard), evitando
    // advertencias de `act(...)`.
    expect(
      await screen.findByRole("heading", { level: 1, name: title }),
    ).toBeInTheDocument();
  });

  // Req 3.3 / 4.6: las rutas administrativas se renderizan DENTRO del
  // Layout_Principal, por lo que la navegación lateral está presente.
  it("renderiza las rutas administrativas dentro del layout con sidebar", async () => {
    renderAt("/dashboard");
    expect(
      await screen.findByRole("navigation", { name: "Navegación principal" }),
    ).toBeInTheDocument();
  });

  // Req 3.4: la ruta raíz redirige de forma consistente al Dashboard.
  it("redirige la ruta raíz `/` al Dashboard", async () => {
    renderAt("/");
    expect(
      await screen.findByRole("heading", { level: 1, name: "Dashboard" }),
    ).toBeInTheDocument();
  });

  // Req 3.5: una ruta inexistente muestra la página 404 sin romper la app.
  it("muestra NotFound (404) en una ruta desconocida", () => {
    renderAt("/ruta-que-no-existe");
    expect(screen.getByText("Página no encontrada")).toBeInTheDocument();
    // No debe montar la navegación administrativa en el 404.
    expect(
      screen.queryByRole("navigation", { name: "Navegación principal" }),
    ).toBeNull();
  });

  // Req 4.6: la página de Login se renderiza FUERA del Layout_Principal,
  // por lo que no debe presentar la barra lateral de navegación.
  it("renderiza /login sin la barra lateral (fuera del layout)", () => {
    renderAt("/login");
    expect(
      screen.getByRole("heading", { level: 1, name: "Iniciar sesión" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("navigation", { name: "Navegación principal" }),
    ).toBeNull();
    // Ningún enlace de navegación administrativa debe estar presente.
    expect(screen.queryByText("Reservations")).toBeNull();
  });
});
