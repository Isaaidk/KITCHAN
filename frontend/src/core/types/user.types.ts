import type { Usuario, RolUsuario } from './auth.types';

export interface CrearUsuarioAdminRequest {
    nombre: string;
    email: string;
    password: string;
    rol: RolUsuario;
}

export interface EditarPasswordRequest {
    password_hash: string; // Según tu Swagger para el PATCH
}

export interface OnboardingRequest {
    restaurante: {
        nombre_comercial: string;
        razon_social: string;
        identificacion_fiscal: string;
        direccion: string;
        telefono: string;
        email_corporativo: string;
    };
    admin: {
        nombre: string;
        email: string;
        password: string;
    };
}