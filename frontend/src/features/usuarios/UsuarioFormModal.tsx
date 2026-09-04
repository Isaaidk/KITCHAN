import { FormEvent, useState } from "react";
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
    <Modal titulo={esEdicion ? "Editar usuario" : "Nuevo usuario"} onClose={onClose}>
      <form onSubmit={onSubmit}>
        <div style={{ marginBottom: 10 }}>
          <label>Nombre</label>
          <input
            style={{ width: "100%", padding: 8 }}
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            required
          />
        </div>
        <div style={{ marginBottom: 10 }}>
          <label>Email</label>
          <input
            style={{ width: "100%", padding: 8 }}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={esEdicion}
            required
          />
        </div>
        {!esEdicion && (
          <div style={{ marginBottom: 10 }}>
            <label>Contraseña</label>
            <input
              style={{ width: "100%", padding: 8 }}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
        )}
        <div style={{ marginBottom: 14 }}>
          <label>Rol</label>
          <select
            style={{ width: "100%", padding: 8 }}
            value={rol}
            onChange={(e) => setRol(e.target.value as RolUsuario)}
          >
            <option value="ADMIN">ADMIN</option>
            <option value="OPERADOR">OPERADOR</option>
          </select>
        </div>
        {error && <div style={{ color: "var(--color-danger)", marginBottom: 10 }}>{error}</div>}
        <button type="submit" disabled={guardando}>
          {guardando ? "Guardando..." : "Guardar"}
        </button>
      </form>
    </Modal>
  );
}
