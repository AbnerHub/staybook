import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Sidebar from "./Sidebar";

/**
 * Tests para Sidebar (navegación lateral).
 *
 * Valida:
 * - Se renderizan los seis enlaces de navegación (Requisito 4.2).
 * - El estado activo de NavLink refleja la ruta actual (Requisito 4.4).
 *
 * Sidebar usa NavLink de react-router, por lo que debe envolverse en un
 * MemoryRouter para proveer contexto de ruteo.
 */

const NAV_LABELS = [
  "Dashboard",
  "Rooms",
  "Guests",
  "Reservations",
  "Availability",
  "History",
];

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Sidebar />
    </MemoryRouter>
  );
}

describe("Sidebar", () => {
  it("renders all six navigation links (Req 4.2)", () => {
    renderAt("/dashboard");

    for (const label of NAV_LABELS) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }

    expect(screen.getAllByRole("link")).toHaveLength(NAV_LABELS.length);
  });

  it("marks the link matching the current route as active (Req 4.4)", () => {
    renderAt("/rooms");

    const roomsLink = screen.getByRole("link", { name: "Rooms" });
    // NavLink establece aria-current="page" y agrega la clase activa cuando la
    // ruta actual coincide con el destino del enlace.
    expect(roomsLink).toHaveAttribute("aria-current", "page");
    expect(roomsLink.className).toContain("sidebar__link--active");
  });

  it("does not mark non-matching links as active (Req 4.4)", () => {
    renderAt("/rooms");

    const dashboardLink = screen.getByRole("link", { name: "Dashboard" });
    expect(dashboardLink).not.toHaveAttribute("aria-current", "page");
    expect(dashboardLink.className).not.toContain("sidebar__link--active");
  });
});
