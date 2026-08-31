/**
 * Pruebas del cliente HTTP centralizado.
 *
 * Cubre construcción de URL desde la base configurada, verbos (GET/POST/PATCH),
 * serialización JSON del cuerpo, normalización de errores HTTP y de red en
 * `ApiError`, respuesta 204 → `null`, e inyección del encabezado
 * `Authorization` cuando existe token.
 *
 * Requirements: 6.1, 6.2, 6.3, 6.4, 8.3, 8.4
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

const BASE = "http://test.local";

/**
 * Construye un mock de `Response` compatible con el cliente.
 * @param {Object} opts
 * @param {number} opts.status
 * @param {boolean} [opts.ok]
 * @param {*} [opts.body] - Cuerpo devuelto por `.json()`.
 * @param {boolean} [opts.json] - Si el `Content-Type` es application/json.
 */
function mockResponse({ status, ok, body = undefined, json = true }) {
  return {
    ok: ok ?? (status >= 200 && status < 300),
    status,
    headers: {
      get: (h) => (h === "Content-Type" ? (json ? "application/json" : "text/plain") : null),
    },
    json: async () => body,
  };
}

// Importación diferida: el cliente lee `import.meta.env` en tiempo de llamada,
// pero importamos tras configurar el entorno para máxima claridad. `ApiError`
// se importa desde el mismo grafo de módulos (tras posibles `resetModules`)
// para que `instanceof` sea consistente bajo ESM.
let apiGet, apiPost, apiPatch, ApiError;

beforeEach(async () => {
  vi.stubEnv("VITE_API_BASE_URL", BASE);
  vi.stubGlobal("fetch", vi.fn());
  ({ apiGet, apiPost, apiPatch } = await import("./client.js"));
  ({ ApiError } = await import("./ApiError.js"));
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
  vi.resetModules();
});

describe("apiGet", () => {
  it("construye la URL desde la base configurada y usa método GET", async () => {
    fetch.mockResolvedValue(mockResponse({ status: 200, body: { ok: true } }));

    const data = await apiGet("/api/v1/rooms/");

    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, options] = fetch.mock.calls[0];
    expect(url).toBe(`${BASE}/api/v1/rooms/`);
    expect(options.method).toBe("GET");
    expect(options.headers["Content-Type"]).toBe("application/json");
    expect(data).toEqual({ ok: true });
  });

  it("agrega parámetros de query cuando se proveen", async () => {
    fetch.mockResolvedValue(mockResponse({ status: 200, body: [] }));

    await apiGet("/api/v1/rooms/", { params: { skip: 0, limit: 10 } });

    const [url] = fetch.mock.calls[0];
    expect(url).toBe(`${BASE}/api/v1/rooms/?skip=0&limit=10`);
  });
});

describe("apiPost", () => {
  it("serializa el cuerpo como JSON y usa método POST", async () => {
    fetch.mockResolvedValue(mockResponse({ status: 201, body: { id: 1 } }));

    const payload = { number: "101", type: "single" };
    const data = await apiPost("/api/v1/rooms/", payload);

    const [url, options] = fetch.mock.calls[0];
    expect(url).toBe(`${BASE}/api/v1/rooms/`);
    expect(options.method).toBe("POST");
    expect(options.body).toBe(JSON.stringify(payload));
    expect(options.headers["Content-Type"]).toBe("application/json");
    expect(data).toEqual({ id: 1 });
  });
});

describe("apiPatch", () => {
  it("serializa el cuerpo como JSON y usa método PATCH", async () => {
    fetch.mockResolvedValue(mockResponse({ status: 200, body: { id: 1, type: "double" } }));

    const payload = { type: "double" };
    const data = await apiPatch("/api/v1/rooms/1", payload);

    const [url, options] = fetch.mock.calls[0];
    expect(url).toBe(`${BASE}/api/v1/rooms/1`);
    expect(options.method).toBe("PATCH");
    expect(options.body).toBe(JSON.stringify(payload));
    expect(data).toEqual({ id: 1, type: "double" });
  });
});

describe("normalización de errores HTTP", () => {
  it("un 404 produce ApiError http con status y detail", async () => {
    fetch.mockResolvedValue(
      mockResponse({ status: 404, body: { detail: "Not found" } }),
    );

    await expect(apiGet("/api/v1/rooms/999")).rejects.toMatchObject({
      kind: "http",
      status: 404,
      detail: "Not found",
    });
    await expect(apiGet("/api/v1/rooms/999")).rejects.toBeInstanceOf(ApiError);
  });

  it("un 500 produce ApiError http con status 500", async () => {
    fetch.mockResolvedValue(
      mockResponse({ status: 500, body: { detail: "Internal error" } }),
    );

    await expect(apiPost("/api/v1/rooms/", {})).rejects.toMatchObject({
      kind: "http",
      status: 500,
      detail: "Internal error",
    });
  });

  it("preserva el cuerpo crudo de un 422 en payload y deja detail nulo", async () => {
    const validationBody = { detail: [{ loc: ["body", "number"], msg: "field required" }] };
    fetch.mockResolvedValue(mockResponse({ status: 422, body: validationBody }));

    let caught;
    try {
      await apiPost("/api/v1/rooms/", {});
    } catch (err) {
      caught = err;
    }

    expect(caught).toBeInstanceOf(ApiError);
    expect(caught.status).toBe(422);
    expect(caught.detail).toBeNull();
    expect(caught.payload).toEqual(validationBody);
  });
});

describe("respuestas sin cuerpo", () => {
  it("un 204 se resuelve como null", async () => {
    fetch.mockResolvedValue(mockResponse({ status: 204, ok: true }));

    const data = await apiGet("/api/v1/reservations/1");
    expect(data).toBeNull();
  });
});

describe("errores de red", () => {
  it("un rechazo de fetch produce ApiError kind network", async () => {
    fetch.mockRejectedValue(new TypeError("Failed to fetch"));

    let caught;
    try {
      await apiGet("/api/v1/rooms/");
    } catch (err) {
      caught = err;
    }

    expect(caught).toBeInstanceOf(ApiError);
    expect(caught.kind).toBe("network");
    expect(caught.status).toBeNull();
  });
});

describe("encabezado Authorization", () => {
  it("no incluye Authorization cuando no hay token (getToken null)", async () => {
    fetch.mockResolvedValue(mockResponse({ status: 200, body: {} }));

    await apiGet("/api/v1/rooms/");

    const [, options] = fetch.mock.calls[0];
    expect(options.headers).not.toHaveProperty("Authorization");
  });

  it("incluye Bearer cuando getToken devuelve un token", async () => {
    // Reimportamos el cliente con el módulo de auth mockeado para que
    // `authHeader()` produzca el encabezado Bearer.
    vi.resetModules();
    vi.doMock("../auth/authToken.js", () => ({
      getToken: () => "t",
      authHeader: () => ({ Authorization: "Bearer t" }),
    }));
    vi.stubEnv("VITE_API_BASE_URL", BASE);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockResponse({ status: 200, body: {} })));

    const client = await import("./client.js");
    await client.apiGet("/api/v1/rooms/");

    const [, options] = fetch.mock.calls[0];
    expect(options.headers.Authorization).toBe("Bearer t");

    vi.doUnmock("../auth/authToken.js");
  });
});
