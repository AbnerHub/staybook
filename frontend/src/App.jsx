import { RouterProvider } from "react-router-dom";

import { router } from "./router/routes.jsx";

// Composición raíz de la Aplicación_Frontend.
// Monta el árbol de rutas central definido en `router/routes.jsx`
// (Req 1.4, 3.1). Toda la navegación de la app pasa por este RouterProvider.
export default function App() {
  return <RouterProvider router={router} />;
}
