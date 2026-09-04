import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import type { RolUsuario } from "../types/usuario";

interface Props {
  roles?: RolUsuario[];
}

export default function ProtectedRoute({ roles }: Props) {
  const { token, usuario } = useAuthStore();

  if (!token || !usuario) {
    return <Navigate to="/login" replace />;
  }

  if (roles && !roles.includes(usuario.rol)) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
