import { createBrowserRouter, Navigate } from "react-router-dom";
import AppLayout from "./shared/components/AppLayout";
import ProtectedRoute from "./shared/components/ProtectedRoute";
import LoginPage from "./features/auth/LoginPage";
import RegistroPage from "./features/auth/RegistroPage";
import ColaPedidosPage from "./features/pedidos/ColaPedidosPage";
import HistorialPage from "./features/pedidos/HistorialPage";
import DashboardPage from "./features/analiticas/DashboardPage";
import UsuariosPage from "./features/usuarios/UsuariosPage";
import IntegracionesPage from "./features/integraciones/IntegracionesPage";
import UberCallbackPage from "./features/integraciones/uber/UberCallbackPage";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/registro", element: <RegistroPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: "/", element: <ColaPedidosPage /> },
          { path: "/historial", element: <HistorialPage /> },
          {
            element: <ProtectedRoute roles={["ADMIN"]} />,
            children: [
              { path: "/analiticas", element: <DashboardPage /> },
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
