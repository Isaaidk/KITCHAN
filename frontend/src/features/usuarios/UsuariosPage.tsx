import { useEffect, useState } from "react";
import { httpClient } from "../../shared/api/httpClient";
import Icon from "../../shared/components/Icon";
import { useAuthStore } from "../../shared/stores/authStore";
import type { Usuario } from "../../shared/types/usuario";
import UsuarioFormModal, { DatosFormUsuario } from "./UsuarioFormModal";
import styles from "./UsuariosPage.module.css";

function iniciales(nombre: string) {
  return nombre
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

// Color de avatar estable a partir del nombre.
const TONOS = ["#2563eb", "#7c3aed", "#0891b2", "#16a34a", "#d97706", "#db2777"];
function tonoPara(nombre: string) {
  let h = 0;
  for (const c of nombre) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return TONOS[h % TONOS.length];
}

export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [editando, setEditando] = useState<Usuario | null | "nuevo">(null);
  const [cargando, setCargando] = useState(true);
  const restauranteId = useAuthStore((s) => s.usuario?.restaurante_id);

  const cargar = () => {
    if (!restauranteId) return;
    httpClient
      .get<Usuario[]>(`/api/v1/usuarios/restaurante/${restauranteId}`)
      .then(({ data }) => setUsuarios(data))
      .finally(() => setCargando(false));
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

  const activos = usuarios.filter((u) => u.estado).length;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Usuarios</h1>
          <p className="page-subtitle">
            {cargando ? "Cargando equipo..." : `${usuarios.length} en el equipo · ${activos} activos`}
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setEditando("nuevo")}>
          <Icon name="mas" size={16} strokeWidth={2.5} />
          Nuevo usuario
        </button>
      </div>

      <div className="table-wrap animate-in">
        <table className="table">
          <thead>
            <tr>
              <th>Usuario</th>
              <th>Rol</th>
              <th>Estado</th>
              <th className={styles.colAcciones}>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {cargando &&
              [0, 1, 2].map((i) => (
                <tr key={i}>
                  <td>
                    <div className={styles.persona}>
                      <div className="skeleton" style={{ width: 38, height: 38, borderRadius: "50%" }} />
                      <div style={{ display: "grid", gap: 6 }}>
                        <div className="skeleton" style={{ height: 12, width: 120 }} />
                        <div className="skeleton" style={{ height: 10, width: 160 }} />
                      </div>
                    </div>
                  </td>
                  <td>
                    <div className="skeleton" style={{ height: 20, width: 70, borderRadius: 999 }} />
                  </td>
                  <td>
                    <div className="skeleton" style={{ height: 20, width: 60, borderRadius: 999 }} />
                  </td>
                  <td />
                </tr>
              ))}

            {usuarios.map((usuario, i) => (
              <tr key={usuario.id} className={styles.fila} style={{ ["--i" as string]: i }}>
                <td>
                  <div className={styles.persona}>
                    <div
                      className={`${styles.avatar} ${usuario.estado ? "" : styles.avatarInactivo}`}
                      style={{ ["--tono" as string]: tonoPara(usuario.nombre) }}
                    >
                      {iniciales(usuario.nombre)}
                    </div>
                    <div className={styles.personaDatos}>
                      <span className={styles.nombre}>{usuario.nombre}</span>
                      <span className={styles.email}>{usuario.email}</span>
                    </div>
                  </div>
                </td>
                <td>
                  <span
                    className="badge"
                    style={{ ["--badge-color" as string]: usuario.rol === "ADMIN" ? "#7c3aed" : "#0891b2" }}
                  >
                    {usuario.rol}
                  </span>
                </td>
                <td>
                  <span
                    className="badge badge-dot"
                    style={{ ["--badge-color" as string]: usuario.estado ? "#16a34a" : "#dc2626" }}
                  >
                    {usuario.estado ? "Activo" : "Inactivo"}
                  </span>
                </td>
                <td>
                  <div className={styles.acciones}>
                    <button className="btn btn-ghost btn-sm" onClick={() => setEditando(usuario)} title="Editar">
                      <Icon name="editar" size={15} />
                      <span className={styles.accionTexto}>Editar</span>
                    </button>
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => cambiarEstado(usuario)}
                      title={usuario.estado ? "Desactivar" : "Activar"}
                    >
                      <Icon name="power" size={15} />
                      <span className={styles.accionTexto}>{usuario.estado ? "Desactivar" : "Activar"}</span>
                    </button>
                    <button
                      className={`btn btn-ghost btn-sm ${styles.eliminar}`}
                      onClick={() => eliminar(usuario)}
                      title="Eliminar"
                    >
                      <Icon name="papelera" size={15} />
                      <span className={styles.accionTexto}>Eliminar</span>
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {!cargando && usuarios.length === 0 && (
          <div className="empty">
            <div className="empty-icon">
              <Icon name="usuarios" size={20} />
            </div>
            <span className="empty-title">Todavía no hay usuarios</span>
            <span>Agrega a tu equipo para que pueda operar la cola de pedidos.</span>
          </div>
        )}
      </div>

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
