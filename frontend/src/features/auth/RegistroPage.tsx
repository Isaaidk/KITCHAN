import { mensajeDeError } from "../../shared/api/mensajeDeError";
import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { httpClient } from "../../shared/api/httpClient";
import Icon from "../../shared/components/Icon";
import { useAuthStore } from "../../shared/stores/authStore";
import type { LoginResponse } from "../../shared/types/usuario";
import AuthLayout from "./AuthLayout";
import styles from "./LoginPage.module.css";

interface FormState {
  nombre_comercial: string;
  razon_social: string;
  identificacion_fiscal: string;
  direccion: string;
  telefono: string;
  email_corporativo: string;
  admin_nombre: string;
  admin_email: string;
  admin_password: string;
}

const VACIO: FormState = {
  nombre_comercial: "",
  razon_social: "",
  identificacion_fiscal: "",
  direccion: "",
  telefono: "",
  email_corporativo: "",
  admin_nombre: "",
  admin_email: "",
  admin_password: "",
};

interface CampoProps {
  campo: keyof FormState;
  etiqueta: string;
  ayuda?: string;
  completo?: boolean;
  valor: string;
  onCambio: (e: React.ChangeEvent<HTMLInputElement>) => void;
  type?: string;
  placeholder?: string;
  autoComplete?: string;
  inputMode?: React.HTMLAttributes<HTMLInputElement>["inputMode"];
  children?: React.ReactNode;
}

function Campo({ campo, etiqueta, ayuda, completo, valor, onCambio, children, ...input }: CampoProps) {
  const id = `registro-${campo}`;
  return (
    <div className={`field ${completo ? styles.completo : ""}`}>
      <label className="label" htmlFor={id}>
        {etiqueta} {ayuda && <span className="label-hint">· {ayuda}</span>}
      </label>
      {children ?? (
        <input
          id={id}
          name={campo}
          className="input"
          value={valor}
          onChange={onCambio}
          spellCheck={input.type === "email" ? false : undefined}
          required
          {...input}
        />
      )}
    </div>
  );
}

export default function RegistroPage() {
  const [form, setForm] = useState<FormState>(VACIO);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);
  const [mostrarPassword, setMostrarPassword] = useState(false);

  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  // Avisa antes de cerrar o recargar la pestaña si hay datos escritos sin enviar.
  const hayCambios = Object.values(form).some((valor) => valor.trim() !== "");
  useEffect(() => {
    if (!hayCambios) return;
    const avisar = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", avisar);
    return () => window.removeEventListener("beforeunload", avisar);
  }, [hayCambios]);

  const set = (campo: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [campo]: e.target.value }));

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setCargando(true);
    try {
      await httpClient.post("/api/v1/onboarding/", {
        restaurante: {
          nombre_comercial: form.nombre_comercial,
          razon_social: form.razon_social,
          identificacion_fiscal: form.identificacion_fiscal,
          direccion: form.direccion,
          telefono: form.telefono,
          email_corporativo: form.email_corporativo,
        },
        admin: {
          nombre: form.admin_nombre,
          email: form.admin_email,
          password: form.admin_password,
        },
      });

      // Auto-login con las credenciales del admin recién creado.
      const { data } = await httpClient.post<LoginResponse>("/api/v1/usuarios/login", {
        email: form.admin_email,
        password: form.admin_password,
      });
      login(data.access_token, data.usuario);
      navigate("/", { replace: true });
    } catch (err: any) {
      setError(mensajeDeError(err, "No se pudo crear el restaurante."));
    } finally {
      setCargando(false);
    }
  };

  return (
    <AuthLayout ancho={600}>
      <div className={styles.logoMovil}>
        <div className={styles.logo}>K</div>
      </div>
      <h2 className={styles.formTitulo}>Crea tu restaurante</h2>
      <p className={styles.formBajada}>Dos pasos: los datos del local y la cuenta del administrador.</p>

      <form onSubmit={onSubmit}>
        <div className={styles.seccionForm}>
          <span className={styles.seccionNumero}>1</span>
          <span className={styles.seccionTitulo}>Datos del restaurante</span>
        </div>
        <div className={styles.grilla}>
          <Campo
            campo="nombre_comercial"
            etiqueta="Nombre comercial"
            valor={form.nombre_comercial}
            onCambio={set("nombre_comercial")}
            placeholder="Ej. La Esquina Grill…"
            autoComplete="organization"
          />
          <Campo
            campo="razon_social"
            etiqueta="Razón social"
            valor={form.razon_social}
            onCambio={set("razon_social")}
            placeholder="Ej. Inversiones La Esquina…"
          />
          <Campo
            campo="identificacion_fiscal"
            etiqueta="Identificación fiscal"
            ayuda="RUC o NIT"
            valor={form.identificacion_fiscal}
            onCambio={set("identificacion_fiscal")}
          />
          <Campo
            campo="telefono"
            etiqueta="Teléfono"
            valor={form.telefono}
            onCambio={set("telefono")}
            type="tel"
            inputMode="tel"
            autoComplete="tel"
          />
          <Campo
            campo="direccion"
            etiqueta="Dirección"
            completo
            valor={form.direccion}
            onCambio={set("direccion")}
            autoComplete="street-address"
          />
          <Campo
            campo="email_corporativo"
            etiqueta="Email corporativo"
            completo
            valor={form.email_corporativo}
            onCambio={set("email_corporativo")}
            type="email"
            placeholder="contacto@turestaurante.com…"
          />
        </div>

        <div className={styles.seccionForm}>
          <span className={styles.seccionNumero}>2</span>
          <span className={styles.seccionTitulo}>Cuenta del administrador</span>
        </div>
        <div className={styles.grilla}>
          <Campo
            campo="admin_nombre"
            etiqueta="Nombre completo"
            completo
            valor={form.admin_nombre}
            onCambio={set("admin_nombre")}
            autoComplete="name"
          />
          <Campo
            campo="admin_email"
            etiqueta="Email"
            valor={form.admin_email}
            onCambio={set("admin_email")}
            type="email"
            autoComplete="username"
          />
          <Campo
            campo="admin_password"
            etiqueta="Contraseña"
            valor={form.admin_password}
            onCambio={set("admin_password")}
          >
            <div className={styles.filaPassword}>
              <input
                id="registro-admin_password"
                name="admin_password"
                className="input"
                type={mostrarPassword ? "text" : "password"}
                value={form.admin_password}
                onChange={set("admin_password")}
                autoComplete="new-password"
                required
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
          </Campo>
        </div>

        {error && (
          <div className="alert alert-error" role="alert">
            <Icon name="alerta" size={16} />
            {error}
          </div>
        )}

        <button
          type="submit"
          className={`btn btn-primary btn-block ${styles.submit} ${cargando ? "is-loading" : ""}`}
          disabled={cargando}
        >
          {cargando ? "Creando…" : "Crear restaurante"}
          {!cargando && <Icon name="flecha" size={16} />}
        </button>
      </form>

      <p className={styles.alternativa}>
        ¿Ya tienes cuenta? <Link to="/login">Ingresar</Link>
      </p>
    </AuthLayout>
  );
}
