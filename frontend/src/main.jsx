import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App.jsx";
// index.css @importa layout.css, por lo que este único import carga toda la base.
import "./styles/index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
