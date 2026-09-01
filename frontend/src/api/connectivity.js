/**
 * Verificación mínima de conectividad con el backend FastAPI.
 *
 * Sondea `GET /openapi.json`, un endpoint público que no requiere JWT.
 * - Cualquier respuesta 2xx o HTTP de error prueba conectividad → alcanzable.
 * - Solo un fallo de transporte (network) significa NO alcanzable.
 */

import { apiGet } from "./client.js";
import { ENDPOINTS } from "./endpoints.js";
import { ApiError } from "./ApiError.js";

export async function checkBackendConnectivity({ signal } = {}) {
  try {
    await apiGet(ENDPOINTS.openapi, { signal });
    return { reachable: true };
  } catch (error) {
    if (error instanceof ApiError && error.kind === "http") {
      return { reachable: true };
    }
    return { reachable: false, error };
  }
}
