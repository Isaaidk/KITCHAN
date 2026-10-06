import { useEffect, useState } from "react";
import { httpClient } from "../../shared/api/httpClient";
import Icon from "../../shared/components/Icon";
import Modal from "../../shared/components/Modal";
import { useAuthStore } from "../../shared/stores/authStore";
import type { RolUsuario, Usuario } from "../../shared/types/usuario";
import UsuarioFormModal, { DatosFormUsuario } from "./UsuarioFormModal";
import styles from "./UsuariosPage.module.css";

const ETIQUETA_ROL: Record<RolUsuario, string> = {
  ADMIN: "Administrador",
  OPERADOR: "Operador",
};

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
  let h = 5381;
  for (const c of nombre) h = (Math.imul(h, 33) + c.charCodeAt(0)) >>> 0;
  h = (h ^ (h >>> 15)) >>> 0;
  return TONOS[h % TONOS.length];
}

export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [editando, setEditando] = useState<Usuario | null | "nuevo">(null);
  const [cargando, setCargando] = useState(true);
  const [porEliminar, setPorEliminarRaw] = useState<Usuario | null>(null);
  const [eliminando, setEliminando] = useState(false);
  const [errorEliminar, setErrorEliminar] = useState<string | null>(null);
  const [errorLista, setErrorLista] = useState<string | null>(null);
  const restauranteId = useAuthStore((s) => s.usuario?.restaurante_id);
  const yoId = useAuthStore((s) => s.usuario?.id);

  const setPorEliminar = (usuario: Usuario | null) => {
    setErrorEliminar(null);
    setPorEliminarRaw(usuario);
  };

  const cargar = () => {
    if (!restauranteId) return;
    httpClient
      .get<Usuario[]>(`/api/v1/usuarios/restaurante/${restauranteId}`)
      .then(({ data }) => {
        setUsuarios(data);
        setErrorLista(null);
      })
      .catch(() => setErrorLista("No se pudo cargar el equipo. Revisa la conexión e inténtalo de nuevo."))
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
    try {
      await httpClient.patch(`/api/v1/usuarios/${usuario.id}/estado`, { estado: !usuario.estado });
      cargar();
    } catch {
      setErrorLista(
        `No se pudo ${usuario.estado ? "desactivar" : "activar"} a ${usuario.nombre}. Inténtalo de nuevo.`,
      );
    }
  };

  const confirmarEliminar = async () => {
    if (!porEliminar) return;
    setEliminando(true);
    try {
      await httpClient.delete(`/api/v1/usuarios/${porEliminar.id}`);
      setPorEliminar(null);
      cargar();
    } catch {
      setErrorEliminar("No se pudo eliminar el usuario. Inténtalo de nuevo.");
    } finally {
      setEliminando(false);
    }
  };

  const activos = usuarios.filter((u) => u.estado).length;
  const admins = usuarios.filter((u) => u.rol === "ADMIN").length;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Usuarios</h1>
          <p className="page-subtitle" aria-live="polite">
            {cargando
              ? "Cargando equipo…"
              : `${usuarios.length} en el equipo · ${activos} ${activos === 1 ? "activo" : "activos"} · ${admins} ${admins === 1 ? "administrador" : "administradores"}`}
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setEditando("nuevo")}>
          <Icon name="mas" size={16} strokeWidth={2.5} />
          Nuevo usuario
        </button>
      </div>

      {errorLista && (
        <div className="alert alert-error" role="alert">
          <Icon name="alerta" size={16} />
          {errorLista}
        </div>
      )}

      <div className="table-wrap animate-in" aria-busy={cargando}>
        <table className={`table ${styles.tabla}`}>
          <caption className="sr-only">Equipo del restaurante</caption>
          <thead>
            <tr>
              <th scope="col">Usuario</th>
              <th scope="col">Rol</th>
              <th scope="col">Estado</th>
              <th scope="col" className={styles.colAcciones}>
                Acciones
              </th>
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
              <tr
                key={usuario.id}
                className={`${styles.fila} ${usuario.estado ? "" : styles.filaInactiva}`}
                style={{ ["--i" as string]: i }}
              >
                <td>
                  <div className={styles.persona}>
                    <div
                      className={`${styles.avatar} ${usuario.estado ? "" : styles.avatarInactivo}`}
                      style={{ ["--tono" as string]: tonoPara(usuario.nombre) }}
                    >
                      {iniciales(usuario.nombre)}
                    </div>
                    <div className={styles.personaDatos}>
                      <span className={styles.nombre}>
                        {usuario.nombre}
                        {usuario.id === yoId && <span className={styles.tu}>Tú</span>}
                      </span>
                      <span className={styles.email}>{usuario.email}</span>
                    </div>
                  </div>
                </td>
                <td>
                  <span className={`${styles.rol} ${usuario.rol === "ADMIN" ? styles.rolAdmin : styles.rolOperador}`}>
                    <Icon name={usuario.rol === "ADMIN" ? "escudo" : "cola"} size={13} />
                    {ETIQUETA_ROL[usuario.rol]}
                  </span>
                </td>
                <td>
                  <span className={`${styles.estado} ${usuario.estado ? styles.estadoActivo : ""}`}>
                    {usuario.estado ? "Activo" : "Inactivo"}
                  </span>
                </td>
                <td>
                  <div className={styles.acciones}>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => setEditando(usuario)}
                      title="Editar"
                      aria-label={`Editar a ${usuario.nombre}`}
                    >
                      <Icon name="editar" size={14} />
                      <span className={styles.accionTexto}>Editar</span>
                    </button>
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => cambiarEstado(usuario)}
                      title={usuario.estado ? "Desactivar" : "Activar"}
                      aria-label={`${usuario.estado ? "Desactivar" : "Activar"} a ${usuario.nombre}`}
                    >
                      <Icon name="power" size={14} />
                      <span className={styles.accionTexto}>{usuario.estado ? "Desactivar" : "Activar"}</span>
                    </button>
                    <button
                      className={`btn btn-ghost btn-sm btn-icon ${styles.eliminar}`}
                      onClick={() => setPorEliminar(usuario)}
                      title="Eliminar"
                      aria-label={`Eliminar a ${usuario.nombre}`}
                    >
                      <Icon name="papelera" size={14} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {!cargando && !errorLista && usuarios.length === 0 && (
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

      {porEliminar && (
        <Modal titulo="Eliminar usuario" onClose={() => setPorEliminar(null)} ancho={440}>
          <p className={styles.confirmTexto}>
            Vas a eliminar a <strong>{porEliminar.nombre}</strong> ({porEliminar.email}). Esta acción no se puede
            deshacer.
          </p>
          {errorEliminar && (
            <div className="alert alert-error" role="alert">
              <Icon name="alerta" size={16} />
              {errorEliminar}
            </div>
          )}
          <div className={styles.confirmAcciones}>
            <button className="btn btn-secondary" onClick={() => setPorEliminar(null)} disabled={eliminando}>
              Cancelar
            </button>
            <button
              className={`btn btn-danger ${eliminando ? "is-loading" : ""}`}
              onClick={confirmarEliminar}
              disabled={eliminando}
            >
              Eliminar
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
