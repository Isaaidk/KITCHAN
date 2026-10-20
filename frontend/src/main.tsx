import React from "react";
import ReactDOM from "react-dom/client";
// Primero los estilos globales (design system) para que los CSS Modules de
// cada componente, que se cargan después, puedan refinarlos.
import "./styles/global.css";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
