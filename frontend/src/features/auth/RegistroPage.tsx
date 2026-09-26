import { FormEvent, useState } from "react";
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

export default function RegistroPage() {
  const [form, setForm] = useState<FormState>(VACIO);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

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
      setError(err?.response?.data?.detail ?? "No se pudo crear el restaurante.");
    } finally {
      setCargando(false);
    }
  };

  return (
    <AuthLayout ancho={560}>
      <div className={styles.logoMovil}>
        <div className={styles.logo}>K</div>
      </div>
      <h2 className={styles.formTitulo}>Crear restaurante</h2>
      <p className={styles.formBajada}>Configura tu restaurante y la cuenta del administrador.</p>

      <form onSubmit={onSubmit}>
        <div className={styles.seccionForm}>
          <span className={styles.seccionNumero}>1</span>
          Datos del restaurante
        </div>
        <div className={styles.grilla}>
          <div className="field">
            <label className="label">Nombre comercial</label>
            <input className="input" value={form.nombre_comercial} onChange={set("nombre_comercial")} required />
          </div>
          <div className="field">
            <label className="label">Razón social</label>
            <input className="input" value={form.razon_social} onChange={set("razon_social")} required />
          </div>
          <div className="field">
            <label className="label">Identificación fiscal (RUC/NIT)</label>
            <input
              className="input"
              value={form.identificacion_fiscal}
              onChange={set("identificacion_fiscal")}
              required
            />
          </div>
          <div className="field">
            <label className="label">Teléfono</label>
            <input className="input" value={form.telefono} onChange={set("telefono")} required />
          </div>
          <div className={`field ${styles.completo}`}>
            <label className="label">Dirección</label>
            <input className="input" value={form.direccion} onChange={set("direccion")} required />
          </div>
          <div className={`field ${styles.completo}`}>
            <label className="label">Email corporativo</label>
            <input
              className="input"
              type="email"
              value={form.email_corporativo}
              onChange={set("email_corporativo")}
              required
            />
          </div>
        </div>

        <div className={styles.seccionForm}>
          <span className={styles.seccionNumero}>2</span>
          Cuenta del administrador
        </div>
        <div className={styles.grilla}>
          <div className={`field ${styles.completo}`}>
            <label className="label">Nombre del administrador</label>
            <input className="input" value={form.admin_nombre} onChange={set("admin_nombre")} required />
          </div>
          <div className="field">
            <label className="label">Email del administrador</label>
            <input
              className="input"
              type="email"
              value={form.admin_email}
              onChange={set("admin_email")}
              required
            />
          </div>
          <div className="field">
            <label className="label">Contraseña</label>
            <input
              className="input"
              type="password"
              value={form.admin_password}
              onChange={set("admin_password")}
              required
            />
          </div>
        </div>

        {error && (
          <div className="alert alert-error">
            <Icon name="alerta" size={16} />
            {error}
          </div>
        )}

        <button
          type="submit"
          className={`btn btn-primary btn-block ${styles.submit} ${cargando ? "is-loading" : ""}`}
          disabled={cargando}
        >
          {cargando ? "Creando..." : "Crear restaurante"}
        </button>
      </form>

      <p className={styles.alternativa}>
        ¿Ya tienes cuenta? <Link to="/login">Ingresar</Link>
      </p>
    </AuthLayout>
  );
}
