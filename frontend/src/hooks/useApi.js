import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Hook genérico para estandarizar el ciclo de vida de una llamada al cliente
 * de API: estado de carga, error normalizado y datos, con cancelación via
 * AbortController. No contiene lógica de negocio.
 */
export function useApi(apiCall) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const controllerRef = useRef(null);

  const run = useCallback(
    async (...args) => {
      if (controllerRef.current) {
        controllerRef.current.abort();
      }

      const controller = new AbortController();
      controllerRef.current = controller;

      setLoading(true);
      setError(null);

      try {
        const result = await apiCall(controller.signal, ...args);
        if (controllerRef.current === controller) {
          setData(result);
        }
        return result;
      } catch (err) {
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
