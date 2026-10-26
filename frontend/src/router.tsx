import { createBrowserRouter, Navigate } from "react-router-dom";
import AppLayout from "./shared/components/AppLayout";
import ProtectedRoute from "./shared/components/ProtectedRoute";
import LoginPage from "./features/auth/LoginPage";
import RecuperarPasswordPage from "./features/auth/RecuperarPasswordPage";
import ColaPedidosPage from "./features/pedidos/ColaPedidosPage";
import HistorialPage from "./features/pedidos/HistorialPage";
import AnaliticasPage from "./features/analiticas/AnaliticasPage";
import CanalAnaliticasPage from "./features/analiticas/CanalAnaliticasPage";
import DashboardPage from "./features/analiticas/DashboardPage";
import { useAuthStore } from "./shared/stores/authStore";
import UsuariosPage from "./features/usuarios/UsuariosPage";
import IntegracionesPage from "./features/integraciones/IntegracionesPage";
import UberCallbackPage from "./features/integraciones/uber/UberCallbackPage";

/** Pantalla de inicio según el rol: el administrador ve el Dashboard; el operador, la cola. */
function Inicio() {
  const rol = useAuthStore((s) => s.usuario?.rol);
  return rol === "ADMIN" ? <DashboardPage /> : <Navigate to="/cola" replace />;
}

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/recuperar", element: <RecuperarPasswordPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: "/", element: <Inicio /> },
          { path: "/cola", element: <ColaPedidosPage /> },
          { path: "/historial", element: <HistorialPage /> },
          {
            element: <ProtectedRoute roles={["ADMIN"]} />,
            children: [
              { path: "/analiticas", element: <AnaliticasPage /> },
              { path: "/analiticas/:canal", element: <CanalAnaliticasPage /> },
              { path: "/usuarios", element: <UsuariosPage /> },
              { path: "/integraciones", element: <IntegracionesPage /> },
              { path: "/integraciones/uber/callback", element: <UberCallbackPage /> },
            ],
          },
        ],
      },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);
