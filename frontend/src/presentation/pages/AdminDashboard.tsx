import React, { useEffect, useState } from 'react';
import { useAuth } from '../../application/hooks/useAuth';
import { userService } from '../../infrastructure/services/user.service';
import type { Usuario } from '../../core/types/auth.types';
import { Modal } from '../components/Modal';

export const AdminDashboard: React.FC = () => {
    const { user, logout } = useAuth();
    const [usuarios, setUsuarios] = useState<Usuario[]>([]);
    
    // Estados para Modals
    const [isCreateModalOpen, setCreateModalOpen] = useState(false);
    const [isEditModalOpen, setEditModalOpen] = useState(false);
    const [selectedUser, setSelectedUser] = useState<Usuario | null>(null);

    // Cargar Usuarios
    const fetchUsuarios = async () => {
        if (user?.restaurante_id) {
            try {
                const data = await userService.listarPorRestaurante(user.restaurante_id);
                setUsuarios(data);
            } catch (error) {
                console.error("Error al cargar usuarios", error);
            }
        }
    };

    useEffect(() => {
        fetchUsuarios();
    }, [user]);

    // Manejador: Crear Usuario
    const handleCrearUsuario = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        const formData = new FormData(e.currentTarget);
        try {
            await userService.crearUsuario(user!.restaurante_id, {
                nombre: formData.get('nombre') as string,
                email: formData.get('email') as string,
                password: formData.get('password') as string,
                rol: formData.get('rol') as 'ADMIN' | 'OPERADOR',
            });
            setCreateModalOpen(false);
            fetchUsuarios(); // Recargar tabla fluida
        } catch (error) {
            alert("Error al crear usuario.");
        }
    };

    // Manejador: Editar Contraseña
    const handleEditarPassword = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        if (!selectedUser) return;
        const formData = new FormData(e.currentTarget);
        try {
            await userService.editarPassword(selectedUser.email, {
                password_hash: formData.get('new_password') as string
            });
            setEditModalOpen(false);
            alert("Contraseña actualizada correctamente.");
        } catch (error) {
            alert("Error al actualizar la contraseña.");
        }
    };

    // Manejador: Eliminar Usuario
    const handleEliminar = async (usuarioId: string) => {
        if (window.confirm("¿Estás seguro de eliminar este usuario permanentemente?")) {
            try {
                await userService.eliminarUsuario(usuarioId);
                fetchUsuarios();
            } catch (error) {
                alert("Error al eliminar usuario.");
            }
        }
    };

    return (
        <div style={{ padding: '20px', maxWidth: '1000px', margin: '0 auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2>Panel de Administrador - KITCHAN</h2>
                <button onClick={logout} style={{ padding: '8px 16px', background: '#dc3545', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Cerrar Sesión</button>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                <h3>Gestión de Usuarios</h3>
                <button onClick={() => setCreateModalOpen(true)} style={{ padding: '8px 16px', background: '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
                    + Nuevo Usuario
                </button>
            </div>

            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                    <tr style={{ borderBottom: '2px solid #ccc', backgroundColor: '#f8f9fa' }}>
                        <th style={thStyle}>Nombre</th>
                        <th style={thStyle}>Email</th>
                        <th style={thStyle}>Rol</th>
                        <th style={thStyle}>Estado</th>
                        <th style={thStyle}>Acciones</th>
                    </tr>
                </thead>
                <tbody>
                    {usuarios.map(u => (
                        <tr key={u.id} style={{ borderBottom: '1px solid #eee' }}>
                            <td style={tdStyle}>{u.nombre}</td>
                            <td style={tdStyle}>{u.email}</td>
                            <td style={tdStyle}>{u.rol}</td>
                            <td style={tdStyle}>
                                <span style={{ color: u.estado ? 'green' : 'red', fontWeight: 'bold' }}>
                                    {u.estado ? 'Activo' : 'Inactivo'}
                                </span>
                            </td>
                            <td style={tdStyle}>
                                <button onClick={() => { setSelectedUser(u); setEditModalOpen(true); }} style={actionBtnStyle}>🔑 Cambiar Pass</button>
                                <button onClick={() => handleEliminar(u.id)} style={{ ...actionBtnStyle, color: 'red' }}>🗑️ Eliminar</button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>

            {/* Modal: Crear Usuario */}
            <Modal isOpen={isCreateModalOpen} onClose={() => setCreateModalOpen(false)} title="Crear Nuevo Usuario">
                <form onSubmit={handleCrearUsuario} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                    <input name="nombre" placeholder="Nombre Completo" required style={inputStyle} />
                    <input name="email" type="email" placeholder="Correo Electrónico" required style={inputStyle} />
                    <input name="password" type="password" placeholder="Contraseña Temporal" required style={inputStyle} />
                    <select name="rol" required style={inputStyle}>
                        <option value="OPERADOR">OPERADOR</option>
                        <option value="ADMIN">ADMINISTRADOR</option>
                    </select>
                    <button type="submit" style={submitBtnStyle}>Guardar Usuario</button>
                </form>
            </Modal>

            {/* Modal: Editar Contraseña */}
            <Modal isOpen={isEditModalOpen} onClose={() => setEditModalOpen(false)} title={`Editar Contraseña de ${selectedUser?.nombre}`}>
                <form onSubmit={handleEditarPassword} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                    <input name="new_password" type="password" placeholder="Nueva Contraseña" required style={inputStyle} />
                    <button type="submit" style={submitBtnStyle}>Actualizar Contraseña</button>
                </form>
            </Modal>
        </div>
    );
};

// Estilos de la tabla y formularios
const thStyle = { padding: '12px' };
const tdStyle = { padding: '12px' };
const actionBtnStyle = { background: 'none', border: 'none', cursor: 'pointer', marginRight: '10px' };
const inputStyle = { padding: '10px', borderRadius: '4px', border: '1px solid #ccc', width: '95%' };
const submitBtnStyle = { padding: '10px', backgroundColor: '#0056b3', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', marginTop: '10px' };