/**
 * Error normalizado del cliente de API.
 *
 * Unifica los fallos de transporte (red) y las respuestas HTTP de error del
 * backend en un único tipo, de modo que los componentes y utilidades manejen
 * errores de forma consistente sin interpretar cuerpos crudos ni exponer
 * trazas internas al usuario.
 *
 * Requirements: 6.4, 8.3
 */
export class ApiError extends Error {
  /**
   * @param {Object} params
   * @param {"http"|"network"} params.kind - Origen del error.
   * @param {number|null} [params.status] - Código HTTP (400, 401, 404, 422, 500, ...).
   * @param {string|null} [params.detail] - Mensaje legible provisto por el backend.
   * @param {*} [params.payload] - Cuerpo crudo de la respuesta (p. ej. arreglo de validación 422).
   * @param {string} [params.message] - Mensaje del Error base.
   * @param {*} [params.cause] - Error subyacente (p. ej. fallo de red).
   */
  constructor({ kind, status = null, detail = null, payload = null, message, cause = null }) {
    super(message || detail || "Error de API");
    this.name = "ApiError";
    this.kind = kind; // "http" | "network"
    this.status = status; // 400,401,403,404,409,422,500...
    this.detail = detail; // mensaje legible del backend
    this.payload = payload; // cuerpo crudo (p. ej. arreglo de validación 422)
    this.cause = cause;
  }
}
