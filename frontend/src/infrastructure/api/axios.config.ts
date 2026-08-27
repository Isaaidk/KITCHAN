// src/infrastructure/api/axios.config.ts
import axios from 'axios';
import { API_BASE_URL, STORAGE_KEYS } from '../../core/constants/api.constants';

export const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Interceptor de Peticiones: Inyecta el token antes de que la petición salga al backend
apiClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem(STORAGE_KEYS.TOKEN);
        if (token && config.headers) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Interceptor de Respuestas: Captura errores globales (ej. Token expirado)
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && error.response.status === 401) {
            console.warn("Sesión expirada o no autorizada. Limpiando credenciales...");
            localStorage.removeItem(STORAGE_KEYS.TOKEN);
            localStorage.removeItem(STORAGE_KEYS.USER);
            // Si el token expira, forzamos la recarga para que el router expulse al usuario al Login
            window.location.href = '/login'; 
        }
        return Promise.reject(error);
    }
);