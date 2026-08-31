/**
 * Cliente HTTP centralizado de StayBook.
 *
 * Único punto de acceso a la API REST del backend FastAPI. Los componentes
 * nunca deben usar `fetch` directamente: consumen `apiGet`, `apiPost` y
 * `apiPatch` desde aquí. Este módulo se encarga de:
 *
 * - Construir la URL a partir de la base configurable (`getApiBaseUrl()`).
 * - Fijar `Content-Type: application/json` e inyectar el encabezado
 *   `Authorization` mediante `authHeader()` (punto único de extensión).
 * - Serializar el cuerpo como JSON y parsear la respuesta JSON.
 * - Normalizar errores de transporte y HTTP en `ApiError`.
 * - Soportar cancelación vía `AbortSignal` (`opts.signal`).
 *
 * Requirements: 6.1, 6.2, 6.3, 6.4, 8.3, 8.4
 */

import { getApiBaseUrl } from "../config/env.js";
import { authHeader } from "../auth/authToken.js";
import { ApiError } from "./ApiError.js";

/**
 * Combina la base con el path y, opcionalmente, agrega parámetros de query.
 *
 * @param {string} base - URL base sin barra final (de `getApiBaseUrl()`).
 * @param {string} path - Ruta del backend (p. ej. `/api/v1/rooms/`).
 * @param {Object|undefined} params - Pares clave/valor para el query string.
 * @returns {string} URL completa.
 */
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

/**
 * Indica si una respuesta trae un cuerpo JSON según su `Content-Type`.
 * @param {Response} response
 * @returns {boolean}
 */
function isJsonResponse(response) {
  const contentType = response.headers.get("Content-Type") || "";
  return contentType.includes("application/json");
}

/**
 * Normaliza una respuesta HTTP en datos o en un `ApiError`.
 *
 * - `204 No Content` → `null`.
 * - `!response.ok` (4xx/5xx) → intenta parsear el cuerpo JSON, extrae `detail`
 *   (formato del backend `{"detail": "..."}`; en 422 `detail` puede ser un
 *   arreglo, que se conserva crudo en `payload`) y lanza `ApiError` HTTP.
 * - Éxito con cuerpo JSON → objeto parseado.
 * - Éxito sin cuerpo JSON → `null`.
 *
 * @param {Response} response
 * @returns {Promise<*>}
 */
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
      // El backend devuelve `detail` como string en errores de negocio; en 422
      // de FastAPI es un arreglo de errores de validación. No se interpreta ni
      // se reescribe: se preserva el arreglo crudo en `payload`.
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

/**
 * Ejecuta una solicitud HTTP y normaliza el resultado.
 *
 * @param {string} method - Método HTTP (`GET`, `POST`, `PATCH`).
 * @param {string} path - Ruta del backend.
 * @param {Object} [opts]
 * @param {*} [opts.body] - Cuerpo a serializar como JSON.
 * @param {Object} [opts.params] - Parámetros de query.
 * @param {AbortSignal} [opts.signal] - Señal para cancelar la solicitud.
 * @returns {Promise<*>}
 * @throws {ApiError} `kind: "network"` en fallo de transporte, `kind: "http"` en 4xx/5xx.
 */
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

/**
 * Solicitud GET.
 * @param {string} path
 * @param {{ params?: Object, signal?: AbortSignal }} [opts]
 * @returns {Promise<*>}
 */
export async function apiGet(path, { params, signal } = {}) {
  return request("GET", path, { params, signal });
}

/**
 * Solicitud POST con cuerpo JSON.
 * @param {string} path
 * @param {*} body
 * @param {{ params?: Object, signal?: AbortSignal }} [opts]
 * @returns {Promise<*>}
 */
export async function apiPost(path, body, { params, signal } = {}) {
  return request("POST", path, { body, params, signal });
}

/**
 * Solicitud PATCH con cuerpo JSON.
 * @param {string} path
 * @param {*} body
 * @param {{ params?: Object, signal?: AbortSignal }} [opts]
 * @returns {Promise<*>}
 */
export async function apiPatch(path, body, { params, signal } = {}) {
  return request("PATCH", path, { body, params, signal });
}
