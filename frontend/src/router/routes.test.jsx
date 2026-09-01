import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

import { routes } from "./routes.jsx";

vi.mock("../api/connectivity.js", () => ({
  checkBackendConnectivity: vi.fn().mockResolvedValue({ reachable: true }),
}));

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

  it.each([
    ["/dashboard", "Dashboard"],
    ["/rooms", "Rooms"],
    ["/guests", "Guests"],
    ["/reservations", "Reservations"],
    ["/availability", "Availability"],
    ["/history", "History"],
  ])("monta la página placeholder de %s con su título", async (path, title) => {
    renderAt(path);
    expect(
      await screen.findByRole("heading", { level: 1, name: title }),
    ).toBeInTheDocument();
  });

  it("renderiza las rutas administrativas dentro del layout con sidebar", async () => {
    renderAt("/dashboard");
    expect(
      await screen.findByRole("navigation", { name: "Navegación principal" }),
    ).toBeInTheDocument();
  });

  it("redirige la ruta raíz `/` al Dashboard", async () => {
    renderAt("/");
    expect(
      await screen.findByRole("heading", { level: 1, name: "Dashboard" }),
    ).toBeInTheDocument();
  });

  it("muestra NotFound (404) en una ruta desconocida", () => {
    renderAt("/ruta-que-no-existe");
    expect(screen.getByText("Página no encontrada")).toBeInTheDocument();
    expect(
      screen.queryByRole("navigation", { name: "Navegación principal" }),
    ).toBeNull();
  });

  it("renderiza /login sin la barra lateral (fuera del layout)", () => {
    renderAt("/login");
    expect(
      screen.getByRole("heading", { level: 1, name: "Iniciar sesión" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("navigation", { name: "Navegación principal" }),
    ).toBeNull();
    expect(screen.queryByText("Reservations")).toBeNull();
  });
});
