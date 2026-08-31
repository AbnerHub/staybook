/**
 * Verificación mínima de conectividad con el backend FastAPI.
 *
 * Objetivo (design.md §10): confirmar que el frontend puede alcanzar el backend
 * sin implementar lógica de negocio ni depender de autenticación. Se sondea
 * `GET /openapi.json`, un endpoint público que no requiere JWT y que está
 * disponible siempre que el backend esté en ejecución.
 *
 * Interpretación de resultados:
 * - Cualquier respuesta 2xx → backend alcanzable.
 * - Cualquier respuesta HTTP de error (401, 404, 500, ...) también prueba
 *   conectividad: el transporte y CORS funcionaron; el backend respondió. Por
 *   eso un `ApiError { kind: "http" }` se considera alcanzable.
 * - Solo un fallo de transporte (`ApiError { kind: "network" }`: backend caído,
 *   DNS, o CORS bloqueado a nivel de red) significa NO alcanzable.
 * - Cualquier otro error inesperado se trata como no alcanzable.
 *
 * Requirements: 10.1
 */

import { apiGet } from "./client.js";
import { ENDPOINTS } from "./endpoints.js";
import { ApiError } from "./ApiError.js";

/**
 * @typedef {Object} ConnectivityResult
 * @property {boolean} reachable - `true` si el backend respondió (2xx o cualquier HTTP).
 * @property {Error} [error] - Error causante cuando `reachable` es `false`.
 */

/**
 * Comprueba si el backend es alcanzable sondeando `/openapi.json`.
 *
 * @param {{ signal?: AbortSignal }} [opts] - Opciones (p. ej. cancelación).
 * @returns {Promise<ConnectivityResult>}
 */
export async function checkBackendConnectivity({ signal } = {}) {
  try {
    await apiGet(ENDPOINTS.openapi, { signal });
    return { reachable: true };
  } catch (error) {
    // Una respuesta HTTP (aunque sea de error) prueba que el backend respondió.
    if (error instanceof ApiError && error.kind === "http") {
      return { reachable: true };
    }
    // Fallo de red o error inesperado → no alcanzable.
    return { reachable: false, error };
  }
}
