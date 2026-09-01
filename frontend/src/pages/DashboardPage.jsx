import { useEffect, useState } from "react";

import PlaceholderPage from "../components/PlaceholderPage.jsx";
import Loading from "../components/Loading.jsx";
import { checkBackendConnectivity } from "../api/connectivity.js";

/**
 * DashboardPage: placeholder con un indicador mínimo de conectividad que
 * demuestra la comunicación con el backend. Sin lógica de negocio.
 */
export default function DashboardPage() {
  const [status, setStatus] = useState("checking");

  useEffect(() => {
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
