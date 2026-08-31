import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Hook genérico para estandarizar el ciclo de vida de una llamada al cliente
 * de API: estado de carga, error normalizado y datos, junto con cancelación
 * mediante AbortController.
 *
 * En esta fase de foundation el hook existe como patrón reutilizable y no se
 * conecta a llamadas de negocio. No contiene lógica de negocio.
 *
 * @template T
 * @param {(signal: AbortSignal) => Promise<T>} apiCall
 *   Función asíncrona que recibe un AbortSignal y realiza la llamada al
 *   cliente de API (p. ej. `(signal) => apiGet(ENDPOINTS.rooms, { signal })`).
 * @returns {{ data: T|null, loading: boolean, error: (import("../api/ApiError").ApiError|Error|null), run: (...args: any[]) => Promise<T|undefined> }}
 *   `data`: último resultado exitoso; `loading`: indicador de carga en curso;
 *   `error`: `ApiError` (u otro Error) del último fallo; `run`: dispara la
 *   llamada y actualiza el estado.
 *
 * Requirements: 8.5
 */
export function useApi(apiCall) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Referencia al controlador de la llamada en curso, para poder abortarla
  // al lanzar una nueva o al desmontar el componente.
  const controllerRef = useRef(null);

  const run = useCallback(
    async (...args) => {
      // Aborta cualquier llamada previa aún en vuelo antes de iniciar otra.
      if (controllerRef.current) {
        controllerRef.current.abort();
      }

      const controller = new AbortController();
      controllerRef.current = controller;

      setLoading(true);
      setError(null);

      try {
        const result = await apiCall(controller.signal, ...args);
        // Solo aplica el resultado si esta llamada sigue siendo la vigente.
        if (controllerRef.current === controller) {
          setData(result);
        }
        return result;
      } catch (err) {
        // Ignora cancelaciones: no son un error de cara al usuario.
        if (err && err.name === "AbortError") {
          return undefined;
        }
        if (controllerRef.current === controller) {
          setError(err);
        }
        return undefined;
      } finally {
        if (controllerRef.current === controller) {
          setLoading(false);
          controllerRef.current = null;
        }
      }
    },
    [apiCall],
  );

  // Al desmontar, aborta cualquier llamada en curso para evitar fugas y
  // actualizaciones de estado sobre un componente ya desmontado.
  useEffect(() => {
    return () => {
      if (controllerRef.current) {
        controllerRef.current.abort();
        controllerRef.current = null;
      }
    };
  }, []);

  return { data, loading, error, run };
}
