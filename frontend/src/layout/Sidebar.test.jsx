import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Sidebar from "./Sidebar";

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
    </MemoryRouter>,
  );
}

describe("Sidebar", () => {
  it("renders all six navigation links", () => {
    renderAt("/dashboard");
    for (const label of NAV_LABELS) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
    expect(screen.getAllByRole("link")).toHaveLength(NAV_LABELS.length);
  });

  it("marks the link matching the current route as active", () => {
    renderAt("/rooms");
    const roomsLink = screen.getByRole("link", { name: "Rooms" });
    expect(roomsLink).toHaveAttribute("aria-current", "page");
    expect(roomsLink.className).toContain("sidebar__link--active");
  });

  it("does not mark non-matching links as active", () => {
    renderAt("/rooms");
    const dashboardLink = screen.getByRole("link", { name: "Dashboard" });
    expect(dashboardLink).not.toHaveAttribute("aria-current", "page");
    expect(dashboardLink.className).not.toContain("sidebar__link--active");
  });
});
