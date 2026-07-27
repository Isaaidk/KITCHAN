// Adaptador de entrada (frontend): helpers de sesión reutilizados por todas las
// pantallas. Habla con el backend de login ya existente y guarda el JWT devuelto
// en localStorage, sin reinventar la verificación de contraseña ni la firma del token.

const API_BASE_URL = "http://127.0.0.1:8000";
const TOKEN_KEY = "kitchan_token";
const USUARIO_KEY = "kitchan_usuario";

async function login(email, password) {
  const respuesta = await fetch(`${API_BASE_URL}/api/v1/usuarios/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email, password: password }),
  });

  const datos = await respuesta.json();

  if (!respuesta.ok) {
    throw new Error(datos.detail || "No se pudo iniciar sesión.");
  }

  return datos; // { access_token, token_type, usuario }
}

function guardarSesion(token, usuario) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USUARIO_KEY, JSON.stringify(usuario));
}

function cerrarSesion() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USUARIO_KEY);
}

function tokenExpirado(token) {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    if (!payload.exp) return false;
    return Date.now() >= payload.exp * 1000;
  } catch (error) {
    return true;
  }
}

function obtenerSesion() {
  const token = localStorage.getItem(TOKEN_KEY);
  const usuarioCrudo = localStorage.getItem(USUARIO_KEY);

  if (!token || !usuarioCrudo) return null;

  if (tokenExpirado(token)) {
    cerrarSesion();
    return null;
  }

  return { token: token, usuario: JSON.parse(usuarioCrudo) };
}

// Guard de ruta: debe llamarse desde un <script> NO diferido/asíncrono en el
// <head>, antes de que el navegador pinte el <body>, para que la redirección
// ocurra sin que se llegue a ver ni un instante el contenido protegido.
function protegerRuta(rolRequerido) {
  const sesion = obtenerSesion();
  const loginPorRol = {
    ADMIN: "login-administrador.html",
    OPERADOR: "login-operador.html",
  };

  if (!sesion || sesion.usuario.rol !== rolRequerido) {
    window.location.replace(loginPorRol[rolRequerido]);
    return false;
  }

  return true;
}