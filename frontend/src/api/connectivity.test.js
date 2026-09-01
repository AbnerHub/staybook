import { describe, it, expect, afterEach, vi } from "vitest";

import { checkBackendConnectivity } from "./connectivity.js";

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
      vi.fn().mockResolvedValue(
        mockResponse({ status: 404, body: { detail: "Not found" } }),
      ),
    );
    const result = await checkBackendConnectivity();
    expect(result).toEqual({ reachable: true });
  });
});
