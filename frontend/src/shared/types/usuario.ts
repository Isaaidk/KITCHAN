export type RolUsuario = "ADMIN" | "OPERADOR";

export interface Usuario {
  id: string;
  restaurante_id: string;
  nombre: string;
  email: string;
  rol: RolUsuario;
  estado: boolean;
  /** Fecha de alta (ISO). */
  creado_en?: string | null;
  /** Último inicio de sesión (ISO); null si todavía no ha entrado. */
  ultimo_acceso?: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  usuario: Usuario;
}
