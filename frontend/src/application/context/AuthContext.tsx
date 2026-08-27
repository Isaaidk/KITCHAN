// src/application/context/AuthContext.tsx
import React, { createContext, useState, useEffect, type ReactNode } from 'react';
import type { Usuario, LoginRequest } from '../../core/types/auth.types';
import { authService } from '../../infrastructure/services/auth.service';
import { STORAGE_KEYS } from '../../core/constants/api.constants';

interface AuthContextType {
    user: Usuario | null;
    isAuthenticated: boolean;
    login: (credentials: LoginRequest) => Promise<void>;
    logout: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<Usuario | null>(null);

    // Al cargar la app, revisamos si ya hay un usuario guardado
    useEffect(() => {
        const storedUser = localStorage.getItem(STORAGE_KEYS.USER);
        if (storedUser) {
            setUser(JSON.parse(storedUser));
        }
    }, []);

    const login = async (credentials: LoginRequest) => {
        const response = await authService.login(credentials);
        
        // Guardamos en LocalStorage
        localStorage.setItem(STORAGE_KEYS.TOKEN, response.access_token);
        localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(response.usuario));
        
        // Guardamos en el estado de React
        setUser(response.usuario);
    };

    const logout = () => {
        localStorage.removeItem(STORAGE_KEYS.TOKEN);
        localStorage.removeItem(STORAGE_KEYS.USER);
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
};