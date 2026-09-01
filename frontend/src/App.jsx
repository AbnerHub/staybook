import { RouterProvider } from "react-router-dom";

import { router } from "./router/routes.jsx";

// Composición raíz: monta el árbol de rutas central.
export default function App() {
  return <RouterProvider router={router} />;
}
