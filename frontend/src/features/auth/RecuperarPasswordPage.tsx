import { FormEvent, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { httpClient } from "../../shared/api/httpClient";
import { mensajeDeError } from "../../shared/api/mensajeDeError";
import Icon from "../../shared/components/Icon";
import AuthLayout from "./AuthLayout";
import styles from "./LoginPage.module.css";
import recuperar from "./RecuperarPasswordPage.module.css";

type Paso = "correo" | "codigo" | "password" | "listo";

const LARGO_MINIMO = 8;
/** Segundos antes de poder pedir otro código (el backend también lo limita). */
const ESPERA_REENVIO = 60;

export default function RecuperarPasswordPage() {
  const navigate = useNavigate();
  const [paso, setPaso] = useState<Paso>("correo");
  const [email, setEmail] = useState("");
  const [codigo, setCodigo] = useState("");
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirmacion, setConfirmacion] = useState("");
  const [mostrar, setMostrar] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);
  const [espera, setEspera] = useState(0);
  const [reenviado, setReenviado] = useState(false);

  const campoRef = useRef<HTMLInputElement>(null);

  // El foco va al primer campo de cada paso.
  useEffect(() => {
    campoRef.current?.focus();
  }, [paso]);

  useEffect(() => {
    if (espera <= 0) return;
    const id = window.setTimeout(() => setEspera((s) => s - 1), 1000);
    return () => window.clearTimeout(id);
  }, [espera]);

  const fallo = (mensaje: string) => {
    setError(mensaje);
    campoRef.current?.focus();
  };

  const pedirCodigo = async (esReenvio = false) => {
    setError(null);
    setCargando(true);
    try {
      await httpClient.post("/api/v1/usuarios/recuperar/solicitar", { email: email.trim() });
      setEspera(ESPERA_REENVIO);
      setReenviado(esReenvio);
      setCodigo("");
      setPaso("codigo");
    } catch (err) {
      fallo(mensajeDeError(err, "No pudimos enviar el código. Revisa el correo e inténtalo de nuevo."));
    } finally {
      setCargando(false);
    }
  };

  const enviarCorreo = (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return fallo("Escribe tu correo electrónico.");
    pedirCodigo();
  };

  const verificarCodigo = async (e: FormEvent) => {
    e.preventDefault();
    if (!/^\d{6}$/.test(codigo)) return fallo("El código tiene 6 dígitos.");
    setError(null);
    setCargando(true);
    try {
      const { data } = await httpClient.post<{ token_restablecimiento: string }>(
        "/api/v1/usuarios/recuperar/verificar",
        { email: email.trim(), codigo },
      );
      setToken(data.token_restablecimiento);
      setPaso("password");
    } catch (err) {
      fallo(mensajeDeError(err, "No pudimos verificar el código. Inténtalo de nuevo."));
    } finally {
      setCargando(false);
    }
  };

  const guardarPassword = async (e: FormEvent) => {
    e.preventDefault();
    if (password.length < LARGO_MINIMO) return fallo(`La contraseña debe tener al menos ${LARGO_MINIMO} caracteres.`);
    if (password !== confirmacion) return fallo("Las contraseñas no coinciden.");
    setError(null);
    setCargando(true);
    try {
      await httpClient.post("/api/v1/usuarios/recuperar/restablecer", {
        token_restablecimiento: token,
        nueva_password: password,
      });
      setPaso("listo");
    } catch (err) {
      fallo(mensajeDeError(err, "No pudimos cambiar la contraseña. Vuelve a empezar."));
    } finally {
      setCargando(false);
    }
  };

  const alerta = error && (
    <div className="alert alert-error" role="alert">
      <Icon name="alerta" size={16} />
      {error}
    </div>
  );

  const boton = (texto: string, cargandoTexto: string) => (
    <button
      type="submit"
      className={`btn btn-primary btn-block ${styles.submit} ${cargando ? "is-loading" : ""}`}
      disabled={cargando}
    >
      {cargando ? cargandoTexto : texto}
      {!cargando && <Icon name="flecha" size={18} />}
    </button>
  );

  return (
    <AuthLayout>
      {paso === "correo" && (
        <form onSubmit={enviarCorreo} noValidate>
          <h2 className={styles.formTitulo}>Recupera tu contraseña</h2>
          <p className={styles.formBajada}>
            Escribe el correo de tu cuenta y te enviaremos un código de 6 dígitos para crear una contraseña nueva.
          </p>
          <div className="field">
            <label className="label" htmlFor="recuperar-email">
              Correo electrónico
            </label>
            <div className={styles.campoIcono}>
              <Icon name="correo" size={18} className={styles.iconoCampo} />
              <input
                id="recuperar-email"
                ref={campoRef}
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
          {alerta}
          {boton("Enviar código", "Enviando…")}
          <div className={recuperar.acciones}>
            <button
              type="button"
              className={recuperar.enlace}
              onClick={() => {
                if (!email.trim()) return fallo("Escribe tu correo electrónico.");
                setError(null);
                setCodigo("");
                setPaso("codigo");
              }}
            >
              Ya tengo un código
            </button>
          </div>
        </form>
      )}

      {paso === "codigo" && (
        <form onSubmit={verificarCodigo} noValidate>
          <h2 className={styles.formTitulo}>Revisa tu correo</h2>
          <p className={styles.formBajada}>
            Si <strong>{email.trim()}</strong> tiene una cuenta, le enviamos un código de 6 dígitos. Vence en 10 minutos.
          </p>
          <div className="field">
            <label className="label" htmlFor="recuperar-codigo">
              Código de verificación
            </label>
            <input
              id="recuperar-codigo"
              ref={campoRef}
              name="codigo"
              className={`input ${recuperar.codigo}`}
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={codigo}
              onChange={(e) => setCodigo(e.target.value.replace(/\D/g, "").slice(0, 6))}
              placeholder="000000"
              spellCheck={false}
            />
          </div>
          <p className="sr-only" role="status">
            {reenviado ? "Te enviamos un código nuevo." : ""}
          </p>
          {alerta}
          {boton("Verificar código", "Verificando…")}
          <div className={recuperar.acciones}>
            <button
              type="button"
              className={recuperar.enlace}
              onClick={() => pedirCodigo(true)}
              disabled={cargando || espera > 0}
            >
              {espera > 0 ? `Reenviar código en ${espera} s` : "Reenviar código"}
            </button>
            <button
              type="button"
              className={recuperar.enlace}
              onClick={() => {
                setError(null);
                setPaso("correo");
              }}
            >
              Cambiar correo
            </button>
          </div>
        </form>
      )}

      {paso === "password" && (
        <form onSubmit={guardarPassword} noValidate>
          <h2 className={styles.formTitulo}>Crea tu contraseña nueva</h2>
          <p className={styles.formBajada}>Elige una contraseña de al menos {LARGO_MINIMO} caracteres.</p>
          <div className="field">
            <label className="label" htmlFor="recuperar-password">
              Contraseña nueva
            </label>
            <div className={`${styles.campoIcono} ${styles.filaPassword}`}>
              <Icon name="candado" size={18} className={styles.iconoCampo} />
              <input
                id="recuperar-password"
                ref={campoRef}
                name="password"
                className="input"
                type={mostrar ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
                placeholder="Mínimo 8 caracteres…"
              />
              <button
                type="button"
                className={styles.togglePassword}
                onClick={() => setMostrar((v) => !v)}
                aria-label={mostrar ? "Ocultar contraseñas" : "Ver contraseñas"}
                title={mostrar ? "Ocultar" : "Ver"}
              >
                <Icon name={mostrar ? "ojoOff" : "ojo"} size={18} />
              </button>
            </div>
          </div>
          <div className="field">
            <label className="label" htmlFor="recuperar-confirmacion">
              Repite la contraseña
            </label>
            <div className={styles.campoIcono}>
              <Icon name="candado" size={18} className={styles.iconoCampo} />
              <input
                id="recuperar-confirmacion"
                name="confirmacion"
                className="input"
                type={mostrar ? "text" : "password"}
                value={confirmacion}
                onChange={(e) => setConfirmacion(e.target.value)}
                autoComplete="new-password"
                placeholder="Repítela para confirmar…"
              />
            </div>
          </div>
          {alerta}
          {boton("Guardar contraseña", "Guardando…")}
        </form>
      )}

      {paso === "listo" && (
        <div className={recuperar.exito}>
          <span className={recuperar.exitoIcono}>
            <Icon name="check" size={30} strokeWidth={3} />
          </span>
          <h2 className={`${styles.formTitulo} ${recuperar.exitoTitulo}`}>¡Contraseña actualizada!</h2>
          <p className={styles.formBajada}>Ya puedes iniciar sesión con tu contraseña nueva.</p>
          <button
            type="button"
            className={`btn btn-primary btn-block ${styles.submit}`}
            onClick={() => navigate("/login", { replace: true })}
          >
            Ir a iniciar sesión
            <Icon name="flecha" size={18} />
          </button>
        </div>
      )}

      {paso !== "listo" && (
        <p className={recuperar.volver}>
          <Link to="/login">← Volver a iniciar sesión</Link>
        </p>
      )}
    </AuthLayout>
  );
}
