/**
 * Pruebas de verificación de conectividad con el backend.
 *
 * `checkBackendConnectivity()` sondea `/openapi.json` a través del cliente HTTP
 * centralizado. Estas pruebas mockean `fetch` globalmente y verifican:
 *
 * - Respuesta 200 → `{ reachable: true }`.
 * - Fallo de red (rechazo de fetch) → `{ reachable: false }` con `error` presente.
 * - Respuesta HTTP de error (404) → `{ reachable: true }`: una respuesta HTTP
 *   prueba que el backend respondió (transporte y CORS funcionaron).
 *
 * Nota ESM/instanceof: `connectivity.js` comprueba `error instanceof ApiError`.
 * Para mantener la identidad de `ApiError` consistente, importamos el módulo de
 * forma normal en la parte superior y NO usamos `vi.resetModules()`. Así el
 * `ApiError` del grafo de módulos es el mismo que evalúa `instanceof`.
 *
 * Requirements: 10.1
 */

import { describe, it, expect, afterEach, vi } from "vitest";

import { checkBackendConnectivity } from "./connectivity.js";

/**
 * Construye un mock de `Response` compatible con el cliente HTTP.
 * @param {Object} opts
 * @param {number} opts.status
 * @param {boolean} [opts.ok]
 * @param {*} [opts.body] - Cuerpo devuelto por `.json()`.
 */
function mockResponse({ status, ok, body = {} }) {
  return {
    ok: ok ?? (status >= 200 && status < 300),
    status,
    headers: {
      get: (h) => (h === "Content-Type" ? "application/json" : null),
    },
    json: async () => body,
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("checkBackendConnectivity", () => {
  it("devuelve { reachable: true } cuando fetch responde 200", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockResponse({ status: 200 })));

    const result = await checkBackendConnectivity();

    expect(result).toEqual({ reachable: true });
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("devuelve { reachable: false } con error cuando fetch falla por red", async () => {
    const networkErr = new TypeError("Failed to fetch");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(networkErr));

    const result = await checkBackendConnectivity();

    expect(result.reachable).toBe(false);
    expect(result.error).toBeDefined();
  });

  it("devuelve { reachable: true } ante una respuesta HTTP de error (404)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(mockResponse({ status: 404, body: { detail: "Not found" } })),
    );

    const result = await checkBackendConnectivity();

    // Una respuesta HTTP prueba que el backend respondió: es alcanzable.
    expect(result).toEqual({ reachable: true });
  });
});
