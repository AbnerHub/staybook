import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Header from "./Header";

describe("Header", () => {
  it("renders the application title", () => {
    render(<Header />);
    expect(screen.getByText("StayBook")).toBeInTheDocument();
  });

  it("renders the reserved session-actions slot", () => {
    const { container } = render(<Header />);
    const sessionSlot = container.querySelector(".header__session");
    expect(sessionSlot).not.toBeNull();
    expect(sessionSlot).toBeEmptyDOMElement();
  });
});
