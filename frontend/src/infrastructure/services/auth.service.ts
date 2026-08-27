// src/infrastructure/services/auth.service.ts
import { apiClient } from '../api/axios.config';
import type { LoginRequest, LoginResponse } from '../../core/types/auth.types';
export const authService = {
    login: async (credentials: LoginRequest): Promise<LoginResponse> => {
        // Axios automáticamente convierte el body a JSON y la respuesta a objeto
        const response = await apiClient.post<LoginResponse>('/usuarios/login', credentials);
        return response.data;
    }
};