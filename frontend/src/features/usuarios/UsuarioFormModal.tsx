import { FormEvent, useState } from "react";
import Icon, { type NombreIcono } from "../../shared/components/Icon";
import Modal from "../../shared/components/Modal";
import type { RolUsuario, Usuario } from "../../shared/types/usuario";
import styles from "./UsuarioFormModal.module.css";

const ROLES: { valor: RolUsuario; titulo: string; descripcion: string; icono: NombreIcono }[] = [
  { valor: "OPERADOR", titulo: "Operador", descripcion: "Trabaja la cola de pedidos de la cocina.", icono: "cola" },
  { valor: "ADMIN", titulo: "Administrador", descripcion: "Además gestiona usuarios, canales y analíticas.", icono: "escudo" },
];

export interface DatosFormUsuario {
  nombre: string;
  email: string;
  password: string;
  rol: RolUsuario;
}

interface Props {
  usuario: Usuario | null;
  onClose: () => void;
  onGuardar: (datos: DatosFormUsuario) => Promise<void>;
}

export default function UsuarioFormModal({ usuario, onClose, onGuardar }: Props) {
  const [nombre, setNombre] = useState(usuario?.nombre ?? "");
  const [email, setEmail] = useState(usuario?.email ?? "");
  const [password, setPassword] = useState("");
  const [rol, setRol] = useState<RolUsuario>(usuario?.rol ?? "OPERADOR");
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  const esEdicion = usuario !== null;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setGuardando(true);
    try {
      await onGuardar({ nombre, email, password, rol });
    } catch {
      setError("No se pudo guardar el usuario.");
    } finally {
      setGuardando(false);
    }
  };

  return (
    <Modal titulo={esEdicion ? "Editar usuario" : "Nuevo usuario"} onClose={onClose} ancho={480}>
      <form onSubmit={onSubmit}>
        <div className="field">
          <label className="label" htmlFor="usuario-nombre">
            Nombre
          </label>
          <input
            id="usuario-nombre"
            name="nombre"
            className="input"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            autoComplete="off"
            placeholder="Ej. María López…"
            required
          />
        </div>
        <div className="field">
          <label className="label" htmlFor="usuario-email">
            Email
          </label>
          <input
            id="usuario-email"
            name="email"
            className="input"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={esEdicion}
            autoComplete="off"
            spellCheck={false}
            placeholder="maria@restaurante.com…"
            required
          />
        </div>
        {!esEdicion && (
          <div className="field">
            <label className="label" htmlFor="usuario-password">
              Contraseña
            </label>
            <input
              id="usuario-password"
              name="password"
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              required
            />
          </div>
        )}
        <fieldset className={styles.rolGrupo}>
          <legend className="label">Rol</legend>
          <div className={styles.rolOpciones}>
            {ROLES.map((opcion) => (
              <label
                key={opcion.valor}
                className={`${styles.rolOpcion} ${rol === opcion.valor ? styles.rolOpcionActiva : ""}`}
              >
                <input
                  type="radio"
                  name="usuario-rol"
                  value={opcion.valor}
                  checked={rol === opcion.valor}
                  onChange={() => setRol(opcion.valor)}
                  className={styles.rolRadio}
                />
                <Icon name={opcion.icono} size={18} />
                <span className={styles.rolTitulo}>{opcion.titulo}</span>
                <span className={styles.rolDescripcion}>{opcion.descripcion}</span>
              </label>
            ))}
          </div>
        </fieldset>

        {error && (
          <div className="alert alert-error" role="alert">
            <Icon name="alerta" size={16} />
            {error}
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 20 }}>
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={guardando}>
            Cancelar
          </button>
          <button
            type="submit"
            className={`btn btn-primary ${guardando ? "is-loading" : ""}`}
            disabled={guardando}
          >
            {guardando ? "Guardando…" : "Guardar"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
