import { useEffect, useState } from "react";
import { httpClient } from "../../shared/api/httpClient";
import { useAuthStore } from "../../shared/stores/authStore";
import type { Usuario } from "../../shared/types/usuario";
import UsuarioFormModal, { DatosFormUsuario } from "./UsuarioFormModal";
import styles from "./UsuariosPage.module.css";

export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [editando, setEditando] = useState<Usuario | null | "nuevo">(null);
  const restauranteId = useAuthStore((s) => s.usuario?.restaurante_id);

  const cargar = () => {
    if (!restauranteId) return;
    httpClient
      .get<Usuario[]>(`/api/v1/usuarios/restaurante/${restauranteId}`)
      .then(({ data }) => setUsuarios(data));
  };

  useEffect(cargar, [restauranteId]);

  const guardar = async (datos: DatosFormUsuario) => {
    if (editando === "nuevo") {
      await httpClient.post(`/api/v1/usuarios/restaurante/${restauranteId}`, {
        nombre: datos.nombre,
        email: datos.email,
        password: datos.password,
        rol: datos.rol,
      });
    } else if (editando) {
      await httpClient.put(`/api/v1/usuarios/${editando.id}`, {
        nombre: datos.nombre,
        rol: datos.rol,
      });
    }
    setEditando(null);
    cargar();
  };

  const cambiarEstado = async (usuario: Usuario) => {
    await httpClient.patch(`/api/v1/usuarios/${usuario.id}/estado`, { estado: !usuario.estado });
    cargar();
  };

  const eliminar = async (usuario: Usuario) => {
    if (!confirm(`¿Eliminar a ${usuario.nombre}?`)) return;
    await httpClient.delete(`/api/v1/usuarios/${usuario.id}`);
    cargar();
  };

  return (
    <div>
      <div className={styles.encabezado}>
        <h2>Usuarios</h2>
        <button className={styles.nuevo} onClick={() => setEditando("nuevo")}>
          Nuevo usuario
        </button>
      </div>

      <table className={styles.tabla}>
        <thead>
          <tr>
            <th>Nombre</th>
            <th>Email</th>
            <th>Rol</th>
            <th>Estado</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {usuarios.map((usuario) => (
            <tr key={usuario.id}>
              <td>{usuario.nombre}</td>
              <td>{usuario.email}</td>
              <td>{usuario.rol}</td>
              <td>
                <span className={`${styles.badge} ${usuario.estado ? styles.activo : styles.inactivo}`}>
                  {usuario.estado ? "Activo" : "Inactivo"}
                </span>
              </td>
              <td className={styles.acciones}>
                <button onClick={() => setEditando(usuario)}>Editar</button>
                <button onClick={() => cambiarEstado(usuario)}>
                  {usuario.estado ? "Desactivar" : "Activar"}
                </button>
                <button onClick={() => eliminar(usuario)}>Eliminar</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {editando && (
        <UsuarioFormModal
          usuario={editando === "nuevo" ? null : editando}
          onClose={() => setEditando(null)}
          onGuardar={guardar}
        />
      )}
    </div>
  );
}
