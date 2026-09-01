/**
 * Cliente HTTP centralizado de StayBook.
 *
 * Único punto de acceso a la API REST del backend FastAPI. Los componentes
 * nunca deben usar `fetch` directamente: consumen `apiGet`, `apiPost` y
 * `apiPatch` desde aquí.
 */

import { getApiBaseUrl } from "../config/env.js";
import { authHeader } from "../auth/authToken.js";
import { ApiError } from "./ApiError.js";

function buildUrl(base, path, params) {
  let url = `${base}${path}`;
  if (params && typeof params === "object") {
    const search = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        search.append(key, String(value));
      }
    }
    const qs = search.toString();
    if (qs) {
      url += (url.includes("?") ? "&" : "?") + qs;
    }
  }
  return url;
}

function isJsonResponse(response) {
  const contentType = response.headers.get("Content-Type") || "";
  return contentType.includes("application/json");
}

async function parseResponse(response) {
  if (response.status === 204) {
    return null;
  }

  if (!response.ok) {
    let payload = null;
    if (isJsonResponse(response)) {
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
    }

    let detail = null;
    if (payload && typeof payload === "object" && "detail" in payload) {
      const rawDetail = payload.detail;
      detail = typeof rawDetail === "string" ? rawDetail : null;
    }

    throw new ApiError({
      kind: "http",
      status: response.status,
      detail,
      payload,
    });
  }

  if (isJsonResponse(response)) {
    return response.json();
  }

  return null;
}

async function request(method, path, { body, params, signal } = {}) {
  const url = buildUrl(getApiBaseUrl(), path, params);
  const headers = { "Content-Type": "application/json", ...authHeader() };

  let response;
  try {
    response = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (networkErr) {
    throw new ApiError({
      kind: "network",
      message: "No se pudo conectar con el servidor",
      cause: networkErr,
    });
  }

  return parseResponse(response);
}

export async function apiGet(path, { params, signal } = {}) {
  return request("GET", path, { params, signal });
}

export async function apiPost(path, body, { params, signal } = {}) {
  return request("POST", path, { body, params, signal });
}

export async function apiPatch(path, body, { params, signal } = {}) {
  return request("PATCH", path, { body, params, signal });
}
