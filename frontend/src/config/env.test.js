import { describe, it, expect, afterEach, vi } from "vitest";
import { getApiBaseUrl } from "./env";

/**
 * Tests para el módulo de configuración de entorno (config/env).
 *
 * Valida el comportamiento de `getApiBaseUrl()`:
 * - Devuelve `VITE_API_BASE_URL` cuando está definida (Req 7.1).
 * - Cae al valor por defecto `http://127.0.0.1:8000` cuando no está
 *   definida o está vacía (Req 7.3).
 * - Recorta las barras finales para construir URLs de forma consistente
 *   (Req 7.1).
 *
 * Como `env.js` lee `import.meta.env.VITE_API_BASE_URL` en tiempo de
 * llamada (dentro de la función, no al cargar el módulo), `vi.stubEnv`
 * afecta el valor observado por `getApiBaseUrl()`.
 */
describe("getApiBaseUrl", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("returns VITE_API_BASE_URL when defined (Req 7.1)", () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://api.example.com");
    expect(getApiBaseUrl()).toBe("http://api.example.com");
  });

  it("falls back to the local default when undefined (Req 7.3)", () => {
    vi.stubEnv("VITE_API_BASE_URL", undefined);
    expect(getApiBaseUrl()).toBe("http://127.0.0.1:8000");
  });

  it("falls back to the local default when empty (Req 7.3)", () => {
    vi.stubEnv("VITE_API_BASE_URL", "");
    expect(getApiBaseUrl()).toBe("http://127.0.0.1:8000");
  });

  it("falls back to the local default when only whitespace (Req 7.3)", () => {
    vi.stubEnv("VITE_API_BASE_URL", "   ");
    expect(getApiBaseUrl()).toBe("http://127.0.0.1:8000");
  });

  it("strips a single trailing slash (Req 7.1)", () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://api.example.com/");
    expect(getApiBaseUrl()).toBe("http://api.example.com");
  });

  it("strips multiple trailing slashes (Req 7.1)", () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://api.example.com///");
    expect(getApiBaseUrl()).toBe("http://api.example.com");
  });
});
