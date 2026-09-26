import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { httpClient } from "../../shared/api/httpClient";
import Icon from "../../shared/components/Icon";
import { useAuthStore } from "../../shared/stores/authStore";
import type { LoginResponse } from "../../shared/types/usuario";
import AuthLayout from "./AuthLayout";
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
  // Se incrementa en cada error para volver a reproducir la animación.
  const [intentoFallido, setIntentoFallido] = useState(0);

  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  const ingresar = async (correo: string, clave: string) => {
    setError(null);
    if (!correo || !clave) {
      setError("Completa email y contraseña.");
      setIntentoFallido((n) => n + 1);
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
      setIntentoFallido((n) => n + 1);
    } finally {
      setCargando(false);
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    ingresar(email, password);
  };

  return (
    <AuthLayout>
      <div className={styles.logoMovil}>
        <div className={styles.logo}>K</div>
      </div>
      <h2 className={styles.formTitulo}>Bienvenido de nuevo</h2>
      <p className={styles.formBajada}>Ingresa para ver la cola de pedidos de tu cocina.</p>

      <form onSubmit={onSubmit}>
        <div className="field">
          <label className="label" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            className="input"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
            placeholder="tu@restaurante.com"
          />
        </div>

        <div className="field">
          <label className="label" htmlFor="password">
            Contraseña
          </label>
          <div className={styles.filaPassword}>
            <input
              id="password"
              className="input"
              type={mostrarPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              placeholder="••••••••"
            />
            <button
              type="button"
              className={styles.togglePassword}
              onClick={() => setMostrarPassword((v) => !v)}
              aria-label={mostrarPassword ? "Ocultar contraseña" : "Ver contraseña"}
              title={mostrarPassword ? "Ocultar" : "Ver"}
            >
              <Icon name={mostrarPassword ? "ojoOff" : "ojo"} size={17} />
            </button>
          </div>
        </div>

        {error && (
          <div className="alert alert-error" key={intentoFallido}>
            <Icon name="alerta" size={16} />
            {error}
          </div>
        )}

        <button
          type="submit"
          className={`btn btn-primary btn-block ${styles.submit} ${cargando ? "is-loading" : ""}`}
          disabled={cargando}
        >
          {cargando ? "Ingresando..." : "Ingresar"}
          {!cargando && <Icon name="flecha" size={16} />}
        </button>
      </form>

      <p className={styles.alternativa}>
        ¿Primera vez en KITCHAN? <Link to="/registro">Crear restaurante nuevo</Link>
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
    </AuthLayout>
  );
}
