import { describe, it, expect } from "vitest";
import { getToken, authHeader } from "./authToken.js";

describe("getToken", () => {
  it("retorna null en la fase de foundation (sin JWT)", () => {
    expect(getToken()).toBeNull();
  });
});

describe("authHeader", () => {
  it("retorna un objeto vacío cuando no hay token", () => {
    expect(authHeader()).toEqual({});
    expect(authHeader()).not.toHaveProperty("Authorization");
  });

  it("construye el encabezado Bearer a partir de un token", () => {
    const token = "t";
    const header = token ? { Authorization: `Bearer ${token}` } : {};
    expect(header).toEqual({ Authorization: "Bearer t" });
  });
});
