import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Header from "./Header";

/**
 * Tests para Header (encabezado del área administrativa).
 *
 * Valida:
 * - Se renderiza el título de la aplicación ("StayBook").
 * - Se reserva un slot para acciones de sesión, sin lógica (Requisito 4.5).
 *
 * Header no depende del contexto de ruteo, por lo que se renderiza sin router.
 */
describe("Header", () => {
  it("renders the application title (Req 4.5)", () => {
    render(<Header />);
    expect(screen.getByText("StayBook")).toBeInTheDocument();
  });

  it("renders the reserved session-actions slot (Req 4.5)", () => {
    const { container } = render(<Header />);
    const sessionSlot = container.querySelector(".header__session");
    expect(sessionSlot).not.toBeNull();
    // El slot está reservado para acciones futuras (p. ej. cerrar sesión) y no
    // implementa lógica en esta fase: debe estar vacío.
    expect(sessionSlot).toBeEmptyDOMElement();
  });
});
