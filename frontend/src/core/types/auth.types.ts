// src/core/types/auth.types.ts

export type RolUsuario = 'ADMIN' | 'OPERADOR';

export interface Usuario {
    id: string;
    restaurante_id: string;
    nombre: string;
    email: string;
    rol: RolUsuario;
    estado: boolean;
}

export interface LoginResponse {
    access_token: string;
    token_type: string;
    usuario: Usuario;
}

export interface LoginRequest {
    email: string;
    password: string;
}