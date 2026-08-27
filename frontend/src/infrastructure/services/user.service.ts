import { apiClient } from '../api/axios.config';
import type { Usuario } from '../../core/types/auth.types';
import type { CrearUsuarioAdminRequest, EditarPasswordRequest } from '../../core/types/user.types';

export const userService = {
    // GET: /api/v1/usuarios/restaurante/{restaurante_id}
    listarPorRestaurante: async (restauranteId: string): Promise<Usuario[]> => {
        const response = await apiClient.get<Usuario[]>(`/usuarios/restaurante/${restauranteId}`);
        return response.data;
    },

    // POST: /api/v1/usuarios/restaurante/{restaurante_id}
    crearUsuario: async (restauranteId: string, data: CrearUsuarioAdminRequest): Promise<Usuario> => {
        const response = await apiClient.post<Usuario>(`/usuarios/restaurante/${restauranteId}`, data);
        return response.data;
    },

    // DELETE: /api/v1/usuarios/{usuario_id}
    eliminarUsuario: async (usuarioId: string): Promise<void> => {
        await apiClient.delete(`/usuarios/${usuarioId}`);
    },

    // PATCH: /api/v1/usuarios/{email}
    editarPassword: async (email: string, data: EditarPasswordRequest): Promise<void> => {
        await apiClient.patch(`/usuarios/${email}`, data);
    }
};
