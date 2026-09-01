/**
 * Error normalizado del cliente de API.
 *
 * Unifica los fallos de transporte (red) y las respuestas HTTP de error del
 * backend en un único tipo, de modo que los componentes y utilidades manejen
 * errores de forma consistente sin interpretar cuerpos crudos ni exponer
 * trazas internas al usuario.
 */
export class ApiError extends Error {
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
