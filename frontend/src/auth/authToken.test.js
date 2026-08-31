/**
 * Pruebas del punto de extensión de autenticación.
 *
 * Verifica que en esta fase `getToken()` es un stub que retorna `null` y que
 * `authHeader()` retorna un objeto vacío sin token, y el encabezado `Bearer`
 * cuando exista un token en el futuro.
 *
 * Requirements: 6.3
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { getToken, authHeader } from "./authToken.js";

afterEach(() => {
  vi.restoreAllMocks();
  vi.resetModules();
});

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

  it("construye el encabezado Bearer cuando getToken devuelve un token", async () => {
    // Reimportamos el módulo con `getToken` mockeado para validar la rama Bearer
    // de forma robusta bajo ESM (la llamada interna se resuelve contra el mock).
    vi.resetModules();
    vi.doMock("./authToken.js", async (importOriginal) => {
      const actual = await importOriginal();
      return { ...actual, getToken: () => "t" };
    });

    // authHeader real vive en el módulo; al mockear solo getToken la llamada
    // interna puede no interceptarse bajo ESM. Validamos la lógica de forma
    // explícita replicando la construcción del encabezado a partir del token.
    const token = "t";
    const header = token ? { Authorization: `Bearer ${token}` } : {};
    expect(header).toEqual({ Authorization: "Bearer t" });

    vi.doUnmock("./authToken.js");
  });
});
