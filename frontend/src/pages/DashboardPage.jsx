import { useEffect, useState } from "react";

import PlaceholderPage from "../components/PlaceholderPage.jsx";
import Loading from "../components/Loading.jsx";
import { checkBackendConnectivity } from "../api/connectivity.js";

/**
 * DashboardPage
 *
 * Página placeholder del panel principal. En esta fase de foundation no tiene
 * lógica de negocio: solo un indicador mínimo de conectividad que demuestra que
 * React puede comunicarse con el backend FastAPI a través del cliente de API
 * centralizado y la base URL configurada (Req 10.1). Ante un fallo de red se
 * refleja el estado "no alcanzable" (Req 8.4).
 *
 * Este indicador es solo una demostración de la base; será reemplazado por el
 * contenido real del dashboard en una spec futura.
 */
export default function DashboardPage() {
  // status: "checking" | "reachable" | "unreachable"
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    // Evita actualizar el estado tras el desmontaje y cancela la petición
    // en curso si el componente se desmonta antes de resolverse.
    const controller = new AbortController();
    let isMounted = true;

    checkBackendConnectivity({ signal: controller.signal }).then((result) => {
      if (!isMounted) return;
      setStatus(result.reachable ? "reachable" : "unreachable");
    });

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, []);

  return (
    <>
      <PlaceholderPage title="Dashboard" />
      <ConnectivityIndicator status={status} />
    </>
  );
}

/**
 * Indicador de conectividad con el backend.
 * Solo presentación: no interpreta datos de negocio.
 *
 * @param {Object} props
 * @param {"checking"|"reachable"|"unreachable"} props.status
 */
function ConnectivityIndicator({ status }) {
  if (status === "checking") {
    return <Loading label="Verificando conexión…" />;
  }

  const reachable = status === "reachable";
  const modifier = reachable
    ? "connectivity-badge--ok"
    : "connectivity-badge--fail";
  const label = reachable ? "Backend alcanzable" : "Backend no alcanzable";

  return (
    <p
      className={`connectivity-badge ${modifier}`}
      role="status"
      aria-live="polite"
    >
      {label}
    </p>
  );
}
