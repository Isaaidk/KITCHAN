// src/presentation/router/ProtectedRoute.tsx
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../application/hooks/useAuth';
import type { RolUsuario } from '../../core/types/auth.types';

interface ProtectedRouteProps {
    children: React.ReactNode;
    allowedRoles: RolUsuario[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
    const { user, isAuthenticated } = useAuth();

    if (!isAuthenticated || !user) {
        return <Navigate to="/login" replace />;
    }

    if (!allowedRoles.includes(user.rol)) {
        // Si es un operador intentando entrar a Admin (o viceversa), lo mandamos a su ruta base
        return <Navigate to={user.rol === 'ADMIN' ? '/admin' : '/operador'} replace />;
    }

    return <>{children}</>;
};