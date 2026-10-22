import { FormEvent, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { httpClient } from "../../shared/api/httpClient";
import Icon from "../../shared/components/Icon";
import KitchanLogo from "../../shared/components/KitchanLogo";
import { recordarSesion, useAuthStore } from "../../shared/stores/authStore";
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

/** Logo "G" de Google (colores oficiales). */
function GoogleG() {
  return (
    <svg width="20" height="20" viewBox="0 0 48 48" aria-hidden="true">
      <path
        fill="#EA4335"
        d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
      />
      <path
        fill="#4285F4"
        d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
      />
      <path
        fill="#FBBC05"
        d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
      />
      <path
        fill="#34A853"
        d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
      />
    </svg>
  );
}

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mostrarPassword, setMostrarPassword] = useState(false);
  const [recordar, setRecordar] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);
  // Se incrementa en cada error para volver a reproducir la animación.
  const [intentoFallido, setIntentoFallido] = useState(0);

  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);

  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  const ingresar = async (correo: string, clave: string) => {
    setError(null);
    if (!correo || !clave) {
      setError("Completa email y contraseña.");
      setIntentoFallido((n) => n + 1);
      // El foco va al primer campo que falta.
      (!correo ? emailRef : passwordRef).current?.focus();
      return;
    }
    setCargando(true);
    try {
      const { data } = await httpClient.post<LoginResponse>("/api/v1/usuarios/login", {
        email: correo,
        password: clave,
      });
      // Decide dónde se guarda la sesión: con "Recordarme" sobrevive al cerrar el navegador.
      recordarSesion(recordar);
      login(data.access_token, data.usuario);
      navigate("/", { replace: true });
    } catch {
      setError("Credenciales inválidas. Revisa tu email y contraseña e inténtalo de nuevo.");
      setIntentoFallido((n) => n + 1);
      passwordRef.current?.focus();
      passwordRef.current?.select();
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
        <KitchanLogo tamano={34} />
      </div>
      <h2 className={styles.saludo}>
        ¡Bienvenido a<strong>Vangalia KITCHAN!</strong>
      </h2>
      <p className={styles.formBajada}>
        Inicia sesión para gestionar tus pedidos y hacer que cada momento cuente.
      </p>

      <form onSubmit={onSubmit}>
        <div className="field">
          <label className="label" htmlFor="email">
            Correo electrónico
          </label>
          <div className={styles.campoIcono}>
            <Icon name="correo" size={18} className={styles.iconoCampo} />
            <input
              id="email"
              ref={emailRef}
              name="email"
              className="input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
              spellCheck={false}
              placeholder="tu@correo.com…"
            />
          </div>
        </div>

        <div className="field">
          <label className="label" htmlFor="password">
            Contraseña
          </label>
          <div className={`${styles.campoIcono} ${styles.filaPassword}`}>
            <Icon name="candado" size={18} className={styles.iconoCampo} />
            <input
              id="password"
              ref={passwordRef}
              name="password"
              className="input"
              type={mostrarPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              placeholder="Ingresa tu contraseña…"
            />
            <button
              type="button"
              className={styles.togglePassword}
              onClick={() => setMostrarPassword((v) => !v)}
              aria-label={mostrarPassword ? "Ocultar contraseña" : "Ver contraseña"}
              title={mostrarPassword ? "Ocultar" : "Ver"}
            >
              <Icon name={mostrarPassword ? "ojoOff" : "ojo"} size={18} />
            </button>
          </div>
        </div>

        <div className={styles.opciones}>
          <label className={styles.recordar}>
            <input
              type="checkbox"
              name="recordar"
              className={styles.recordarInput}
              checked={recordar}
              onChange={(e) => setRecordar(e.target.checked)}
            />
            <span className={styles.recordarCaja} aria-hidden="true">
              <Icon name="check" size={14} strokeWidth={3} />
            </span>
            Recordarme
          </label>
          <Link to="/recuperar" className={styles.olvido}>
            ¿Olvidaste tu contraseña?
          </Link>
        </div>

        {error && (
          <div className="alert alert-error" role="alert" key={intentoFallido}>
            <Icon name="alerta" size={16} />
            {error}
          </div>
        )}

        <button
          type="submit"
          className={`btn btn-primary btn-block ${styles.submit} ${cargando ? "is-loading" : ""}`}
          disabled={cargando}
        >
          {cargando ? "Ingresando…" : "Iniciar sesión"}
          {!cargando && <Icon name="flecha" size={18} />}
        </button>
      </form>

      <div className={styles.separador}>o continúa con</div>

      {/* El inicio con Google aún no existe en el backend: se muestra deshabilitado. */}
      <button type="button" className={styles.google} disabled>
        <GoogleG />
        Iniciar sesión con Google
        <span className={styles.googleEtiqueta}>Próximamente</span>
      </button>

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
