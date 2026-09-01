import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";

import Loading from "./Loading";
import ErrorMessage from "./ErrorMessage";
import PlaceholderPage from "./PlaceholderPage";
import NotFound from "./NotFound";

describe("Loading", () => {
  it("renders its indicator with the default label", () => {
    render(<Loading />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByText("Cargando…")).toBeInTheDocument();
  });

  it("renders a custom label when passed", () => {
    render(<Loading label="Procesando…" />);
    expect(screen.getByText("Procesando…")).toBeInTheDocument();
  });
});

describe("ErrorMessage", () => {
  it("shows the network message for a network error", () => {
    render(<ErrorMessage error={{ kind: "network" }} />);
    expect(
      screen.getByText("No se pudo conectar con el servidor"),
    ).toBeInTheDocument();
  });

  it("shows the HTTP detail for an http error", () => {
    render(
      <ErrorMessage error={{ kind: "http", detail: "Habitación no encontrada" }} />,
    );
    expect(screen.getByText("Habitación no encontrada")).toBeInTheDocument();
  });

  it("shows a string error verbatim", () => {
    render(<ErrorMessage error="Error simple" />);
    expect(screen.getByText("Error simple")).toBeInTheDocument();
  });

  it("returns null when there is no error", () => {
    const { container } = render(<ErrorMessage error={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("never renders a stack trace", () => {
    const stackText = "at Object.<anonymous> (/app/src/api/client.js:42:11)";
    const error = {
      kind: "http",
      detail: "Solicitud inválida",
      stack: `Error: boom\n    ${stackText}`,
      cause: "internal secret cause",
    };
    const { container } = render(<ErrorMessage error={error} />);
    expect(screen.getByText("Solicitud inválida")).toBeInTheDocument();
    expect(container.textContent).not.toContain(stackText);
    expect(container.textContent).not.toContain("internal secret cause");
  });
});

describe("PlaceholderPage", () => {
  it("renders the section title", () => {
    render(<PlaceholderPage title="Habitaciones" />);
    expect(
      screen.getByRole("heading", { name: "Habitaciones" }),
    ).toBeInTheDocument();
  });

  it("renders the default note when no description is given", () => {
    render(<PlaceholderPage title="Reservas" />);
    expect(
      screen.getByText("Esta sección estará disponible próximamente."),
    ).toBeInTheDocument();
  });

  it("renders a custom description when provided", () => {
    render(<PlaceholderPage title="Reportes" description="Detalle personalizado" />);
    expect(screen.getByText("Detalle personalizado")).toBeInTheDocument();
  });
});

describe("NotFound", () => {
  it("renders the 'Página no encontrada' heading", () => {
    render(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>,
    );
    expect(
      screen.getByRole("heading", { name: "Página no encontrada" }),
    ).toBeInTheDocument();
  });

  it("renders a link back to the dashboard", () => {
    render(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link")).toHaveAttribute("href", "/dashboard");
  });
});
