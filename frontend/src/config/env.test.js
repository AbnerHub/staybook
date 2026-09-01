import { describe, it, expect, afterEach, vi } from "vitest";
import { getApiBaseUrl } from "./env";

describe("getApiBaseUrl", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("returns VITE_API_BASE_URL when defined", () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://api.example.com");
    expect(getApiBaseUrl()).toBe("http://api.example.com");
  });

  it("falls back to the local default when undefined", () => {
    vi.stubEnv("VITE_API_BASE_URL", undefined);
    expect(getApiBaseUrl()).toBe("http://127.0.0.1:8000");
  });

  it("falls back to the local default when empty", () => {
    vi.stubEnv("VITE_API_BASE_URL", "");
    expect(getApiBaseUrl()).toBe("http://127.0.0.1:8000");
  });

  it("falls back to the local default when only whitespace", () => {
    vi.stubEnv("VITE_API_BASE_URL", "   ");
    expect(getApiBaseUrl()).toBe("http://127.0.0.1:8000");
  });

  it("strips a single trailing slash", () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://api.example.com/");
    expect(getApiBaseUrl()).toBe("http://api.example.com");
  });

  it("strips multiple trailing slashes", () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://api.example.com///");
    expect(getApiBaseUrl()).toBe("http://api.example.com");
  });
});
