import { Outlet } from "react-router-dom";

import Header from "./Header.jsx";
import Sidebar from "./Sidebar.jsx";

/**
 * AdminLayout
 *
 * Layout persistente del área administrativa. Compone tres regiones:
 * - Header (ancho completo, marca + slot de sesión)
 * - Sidebar (navegación lateral)
 * - Área de contenido que renderiza la página hija activa vía <Outlet/>.
 *
 * La disposición (flex column para la raíz, fila para sidebar + contenido)
 * se define en styles/layout.css usando las clases coordinadas:
 * `.admin-layout`, `.admin-layout__body`, `.admin-layout__sidebar`,
 * `.admin-layout__content`.
 *
 * Requisitos: 4.1 (layout con header, sidebar y área de contenido),
 * 4.3 (navegación entre secciones sin recarga completa vía <Outlet/>).
 */
export default function AdminLayout() {
  return (
    <div className="admin-layout">
      <Header />
      <div className="admin-layout__body">
        <Sidebar />
        <main className="admin-layout__content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
