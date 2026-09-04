import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { httpClient } from "../../shared/api/httpClient";
import { useAuthStore } from "../../shared/stores/authStore";
import type { LoginResponse } from "../../shared/types/usuario";
import styles from "./LoginPage.module.css";

// Credenciales de demo opcionales, configurables por entorno (no se
// inventan usuarios en el backend); si no están seteadas, los botones de
// acceso demo simplemente no se muestran.
const DEMO_ADMIN = {
  email: import.meta.env.VITE_DEMO_ADMIN_EMAIL as string | undefined,
  password: import.meta.env.VITE_DEMO_ADMIN_PASSWORD as string | undefined,
};
const DEMO_OPERADOR = {
  email: import.meta.env.VITE_DEMO_OPERADOR_EMAIL as string | undefined,
  password: import.meta.env.VITE_DEMO_OPERADOR_PASSWORD as string | undefined,
};

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mostrarPassword, setMostrarPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  const ingresar = async (correo: string, clave: string) => {
    setError(null);
    if (!correo || !clave) {
      setError("Completa email y contraseña.");
      return;
    }
    setCargando(true);
    try {
      const { data } = await httpClient.post<LoginResponse>("/api/v1/usuarios/login", {
        email: correo,
        password: clave,
      });
      login(data.access_token, data.usuario);
      navigate("/", { replace: true });
    } catch {
      setError("Credenciales inválidas.");
    } finally {
      setCargando(false);
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    ingresar(email, password);
  };

  return (
    <div className={styles.pantalla}>
      <div className={styles.tarjeta}>
        <div className={styles.marca}>KITCHAN</div>

        <form onSubmit={onSubmit}>
          <div className={styles.campo}>
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
            />
          </div>

          <div className={styles.campo}>
            <label htmlFor="password">Contraseña</label>
            <div className={styles.filaPassword}>
              <input
                id="password"
                type={mostrarPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
              <button
                type="button"
                className={styles.togglePassword}
                onClick={() => setMostrarPassword((v) => !v)}
              >
                {mostrarPassword ? "Ocultar" : "Ver"}
              </button>
            </div>
          </div>

          {error && <div className={styles.error}>{error}</div>}

          <button type="submit" className={styles.submit} disabled={cargando}>
            {cargando ? "Ingresando..." : "Ingresar"}
          </button>
        </form>

        <p style={{ textAlign: "center", marginTop: 16, fontSize: "0.82rem" }}>
          <Link to="/registro">Crear restaurante nuevo</Link>
        </p>

        {(DEMO_ADMIN.email || DEMO_OPERADOR.email) && (
          <div className={styles.demo}>
            {DEMO_ADMIN.email && DEMO_ADMIN.password && (
              <button
                className={styles.demoBoton}
                onClick={() => ingresar(DEMO_ADMIN.email!, DEMO_ADMIN.password!)}
              >
                Demo Admin
              </button>
            )}
            {DEMO_OPERADOR.email && DEMO_OPERADOR.password && (
              <button
                className={styles.demoBoton}
                onClick={() => ingresar(DEMO_OPERADOR.email!, DEMO_OPERADOR.password!)}
              >
                Demo Operador
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
