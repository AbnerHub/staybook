import { Outlet } from "react-router-dom";

import Header from "./Header.jsx";
import Sidebar from "./Sidebar.jsx";

/**
 * AdminLayout: layout persistente del área administrativa. Compone Header,
 * Sidebar y un área de contenido que renderiza la página hija vía <Outlet/>.
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
