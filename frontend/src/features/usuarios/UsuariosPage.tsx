import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { httpClient } from "../../shared/api/httpClient";
import { mensajeDeError } from "../../shared/api/mensajeDeError";
import Icon, { type NombreIcono } from "../../shared/components/Icon";
import Modal from "../../shared/components/Modal";
import { useAuthStore } from "../../shared/stores/authStore";
import { useToastStore } from "../../shared/stores/toastStore";
import type { Usuario } from "../../shared/types/usuario";
import { hace, minutos, numero } from "../../shared/utils/formato";
import { useActividad } from "./actividad";
import UsuarioDetalleModal from "./UsuarioDetalleModal";
import UsuarioFormModal, { DatosFormUsuario } from "./UsuarioFormModal";
import { ETIQUETA_ROL, iniciales, tonoPara } from "./usuariosUtils";
import styles from "./UsuariosPage.module.css";

type FiltroRol = "TODOS" | "ADMIN" | "OPERADOR";
type FiltroEstado = "TODOS" | "ACTIVO" | "INACTIVO";

/** Filtros en la URL (?q=&rol=&estado=): se pueden compartir y sobreviven a recargar. */
function useFiltros() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const rolParam = params.get("rol");
  const estadoParam = params.get("estado");
  const rol: FiltroRol = rolParam === "ADMIN" || rolParam === "OPERADOR" ? rolParam : "TODOS";
  const estado: FiltroEstado = estadoParam === "ACTIVO" || estadoParam === "INACTIVO" ? estadoParam : "TODOS";

  const cambiar = (clave: string, valor: string) =>
    setParams(
      (previos) => {
        const nuevos = new URLSearchParams(previos);
        if (valor && valor !== "TODOS") nuevos.set(clave, valor);
        else nuevos.delete(clave);
        return nuevos;
      },
      { replace: true },
    );

  return { q, rol, estado, cambiar, limpiar: () => setParams({}, { replace: true }) };
}

interface TarjetaResumen {
  etiqueta: string;
  valor: number;
  icono: NombreIcono;
  tono: string;
}

export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [editando, setEditando] = useState<Usuario | null | "nuevo">(null);
  const [verDetalle, setVerDetalle] = useState<Usuario | null>(null);
  const [cargando, setCargando] = useState(true);
  const [porEliminar, setPorEliminarRaw] = useState<Usuario | null>(null);
  const [eliminando, setEliminando] = useState(false);
  const [errorEliminar, setErrorEliminar] = useState<string | null>(null);
  const [errorLista, setErrorLista] = useState<string | null>(null);
  const [paraCodigo, setParaCodigoRaw] = useState<Usuario | null>(null);
  const [enviandoCodigo, setEnviandoCodigo] = useState(false);
  const [errorCodigo, setErrorCodigo] = useState<string | null>(null);
  const restauranteId = useAuthStore((s) => s.usuario?.restaurante_id);
  const yoId = useAuthStore((s) => s.usuario?.id);
  const agregarToast = useToastStore((s) => s.add);
  const filtros = useFiltros();
  // Pedidos aceptados por cada persona en los últimos 7 días (no es crítico si falla).
  const { datos: actividad } = useActividad("7d");

  const setPorEliminar = (usuario: Usuario | null) => {
    setErrorEliminar(null);
    setPorEliminarRaw(usuario);
  };

  const setParaCodigo = (usuario: Usuario | null) => {
    setErrorCodigo(null);
    setParaCodigoRaw(usuario);
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
    setVerDetalle(null);
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

  const confirmarCodigo = async () => {
    if (!paraCodigo) return;
    setEnviandoCodigo(true);
    setErrorCodigo(null);
    try {
      await httpClient.post(`/api/v1/usuarios/${paraCodigo.id}/codigo-recuperacion`);
      agregarToast(`Enviamos un código a ${paraCodigo.email}`);
      setParaCodigo(null);
    } catch (err) {
      setErrorCodigo(mensajeDeError(err, "No se pudo enviar el código. Inténtalo de nuevo."));
    } finally {
      setEnviandoCodigo(false);
    }
  };

  const activos = usuarios.filter((u) => u.estado).length;
  const admins = usuarios.filter((u) => u.rol === "ADMIN").length;
  const operadores = usuarios.length - admins;
  const inactivos = usuarios.length - activos;

  const resumen: TarjetaResumen[] = [
    { etiqueta: "En el equipo", valor: usuarios.length, icono: "usuarios", tono: "#6b1e3c" },
    { etiqueta: "Administradores", valor: admins, icono: "escudo", tono: "#2e3a46" },
    { etiqueta: "Operadores", valor: operadores, icono: "cola", tono: "#1f8f8f" },
    { etiqueta: "Inactivos", valor: inactivos, icono: "power", tono: "#9a6410" },
  ];

  const porUsuario = useMemo(
    () => new Map(actividad?.usuarios.map((a) => [a.usuario_id, a]) ?? []),
    [actividad],
  );

  const visibles = useMemo(() => {
    const texto = filtros.q.trim().toLocaleLowerCase();
    return usuarios.filter((u) => {
      if (filtros.rol !== "TODOS" && u.rol !== filtros.rol) return false;
      if (filtros.estado === "ACTIVO" && !u.estado) return false;
      if (filtros.estado === "INACTIVO" && u.estado) return false;
      return !texto || u.nombre.toLocaleLowerCase().includes(texto) || u.email.toLocaleLowerCase().includes(texto);
    });
  }, [usuarios, filtros.q, filtros.rol, filtros.estado]);

  const hayFiltros = filtros.q !== "" || filtros.rol !== "TODOS" || filtros.estado !== "TODOS";

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Usuarios</h1>
          <p className="page-subtitle" aria-live="polite">
            {cargando
              ? "Cargando equipo…"
              : `${usuarios.length} en el equipo · ${activos} ${activos === 1 ? "activo" : "activos"}`}
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

      <ul className={styles.resumen} aria-label="Resumen del equipo">
        {resumen.map((t) => (
          <li key={t.etiqueta} className={styles.tarjeta} style={{ ["--tono" as string]: t.tono }}>
            <span className={styles.tarjetaIcono}>
              <Icon name={t.icono} size={18} />
            </span>
            <span className={styles.tarjetaValor}>{cargando ? "—" : numero(t.valor)}</span>
            <span className={styles.tarjetaEtiqueta}>{t.etiqueta}</span>
          </li>
        ))}
      </ul>

      <div className={styles.barra} role="search">
        <div className={styles.buscador}>
          <Icon name="buscar" size={16} className={styles.buscadorIcono} />
          <input
            type="search"
            name="buscar"
            className={`input ${styles.buscadorInput}`}
            value={filtros.q}
            onChange={(e) => filtros.cambiar("q", e.target.value)}
            placeholder="Buscar por nombre o correo…"
            aria-label="Buscar por nombre o correo"
            autoComplete="off"
            spellCheck={false}
          />
        </div>
        <select
          className={`select ${styles.filtro}`}
          value={filtros.rol}
          onChange={(e) => filtros.cambiar("rol", e.target.value)}
          aria-label="Filtrar por rol"
        >
          <option value="TODOS">Todos los roles</option>
          <option value="ADMIN">Administradores</option>
          <option value="OPERADOR">Operadores</option>
        </select>
        <select
          className={`select ${styles.filtro}`}
          value={filtros.estado}
          onChange={(e) => filtros.cambiar("estado", e.target.value)}
          aria-label="Filtrar por estado"
        >
          <option value="TODOS">Todos los estados</option>
          <option value="ACTIVO">Activos</option>
          <option value="INACTIVO">Inactivos</option>
        </select>
        {hayFiltros && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={filtros.limpiar}>
            Limpiar filtros
          </button>
        )}
      </div>

      <div className="table-wrap animate-in" aria-busy={cargando}>
        <table className={`table ${styles.tabla}`}>
          <caption className="sr-only">Equipo del restaurante</caption>
          <thead>
            <tr>
              <th scope="col">Usuario</th>
              <th scope="col">Rol</th>
              <th scope="col">Estado</th>
              <th scope="col">Último acceso</th>
              <th scope="col">Pedidos aceptados (7 días)</th>
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
                  <td />
                  <td />
                </tr>
              ))}

            {visibles.map((usuario, i) => {
              const act = porUsuario.get(usuario.id);
              return (
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
                          <button type="button" className={styles.verFicha} onClick={() => setVerDetalle(usuario)}>
                            {usuario.nombre}
                            <span className="sr-only"> (ver ficha)</span>
                          </button>
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
                  <td className={styles.acceso}>
                    {usuario.ultimo_acceso ? (
                      hace(usuario.ultimo_acceso)
                    ) : (
                      <span className={styles.sinDato}>Aún no ha entrado</span>
                    )}
                  </td>
                  <td>
                    {act ? (
                      <div className={styles.actividad}>
                        <strong>{numero(act.pedidos_atendidos)}</strong>
                        {act.tiempo_promedio_minutos > 0 && (
                          <span className={styles.actividadSub}>{minutos(act.tiempo_promedio_minutos)} en promedio</span>
                        )}
                      </div>
                    ) : (
                      <span className={styles.sinDato}>{actividad ? "Ninguno" : "—"}</span>
                    )}
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
                        className="btn btn-ghost btn-sm btn-icon"
                        onClick={() => setParaCodigo(usuario)}
                        disabled={!usuario.estado}
                        title="Enviar código de acceso"
                        aria-label={`Enviar código de acceso a ${usuario.nombre}`}
                      >
                        <Icon name="correo" size={14} />
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
              );
            })}
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

        {!cargando && usuarios.length > 0 && visibles.length === 0 && (
          <div className="empty">
            <div className="empty-icon">
              <Icon name="buscar" size={20} />
            </div>
            <span className="empty-title">Ningún usuario coincide</span>
            <span>Prueba con otro nombre o limpia los filtros.</span>
          </div>
        )}
      </div>

      {actividad && actividad.sin_atribuir > 0 && (
        <p className={styles.nota}>
          {numero(actividad.sin_atribuir)}{" "}
          {actividad.sin_atribuir === 1 ? "pedido aceptado" : "pedidos aceptados"} en estos 7 días no tiene registrado
          quién lo aceptó (son anteriores a este registro), por eso no aparece en ninguna persona.
        </p>
      )}

      {editando && (
        <UsuarioFormModal
          usuario={editando === "nuevo" ? null : editando}
          onClose={() => setEditando(null)}
          onGuardar={guardar}
        />
      )}

      {verDetalle && (
        <UsuarioDetalleModal
          usuario={verDetalle}
          esYo={verDetalle.id === yoId}
          onClose={() => setVerDetalle(null)}
          onEditar={() => setEditando(verDetalle)}
          onEnviarCodigo={() => setParaCodigo(verDetalle)}
        />
      )}

      {paraCodigo && (
        <Modal titulo="Enviar código de acceso" onClose={() => setParaCodigo(null)} ancho={460}>
          <p className={styles.confirmTexto}>
            Le enviaremos un código de 6 dígitos a <strong>{paraCodigo.email}</strong>. Con él, {paraCodigo.nombre}{" "}
            podrá crear una contraseña nueva desde “¿Olvidaste tu contraseña?”. Tú no verás ni cambiarás su
            contraseña.
          </p>
          {errorCodigo && (
            <div className="alert alert-error" role="alert">
              <Icon name="alerta" size={16} />
              {errorCodigo}
            </div>
          )}
          <div className={styles.confirmAcciones}>
            <button className="btn btn-secondary" onClick={() => setParaCodigo(null)} disabled={enviandoCodigo}>
              Cancelar
            </button>
            <button
              className={`btn btn-primary ${enviandoCodigo ? "is-loading" : ""}`}
              onClick={confirmarCodigo}
              disabled={enviandoCodigo}
            >
              <Icon name="correo" size={16} />
              Enviar código
            </button>
          </div>
        </Modal>
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
