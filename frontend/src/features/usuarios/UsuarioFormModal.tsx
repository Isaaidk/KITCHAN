import { FormEvent, useState } from "react";
import Icon from "../../shared/components/Icon";
import Modal from "../../shared/components/Modal";
import type { RolUsuario, Usuario } from "../../shared/types/usuario";

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
            className="input"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            placeholder="Ej. María López"
            required
          />
        </div>
        <div className="field">
          <label className="label" htmlFor="usuario-email">
            Email
          </label>
          <input
            id="usuario-email"
            className="input"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={esEdicion}
            placeholder="maria@restaurante.com"
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
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
        )}
        <div className="field">
          <label className="label" htmlFor="usuario-rol">
            Rol
          </label>
          <select
            id="usuario-rol"
            className="select"
            value={rol}
            onChange={(e) => setRol(e.target.value as RolUsuario)}
          >
            <option value="ADMIN">ADMIN</option>
            <option value="OPERADOR">OPERADOR</option>
          </select>
        </div>

        {error && (
          <div className="alert alert-error">
            <Icon name="alerta" size={16} />
            {error}
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 8 }}>
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={guardando}>
            Cancelar
          </button>
          <button
            type="submit"
            className={`btn btn-primary ${guardando ? "is-loading" : ""}`}
            disabled={guardando}
          >
            {guardando ? "Guardando..." : "Guardar"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
