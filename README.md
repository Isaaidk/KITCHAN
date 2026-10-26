# KITCHAN

Panel de cocina para cafeterías y restaurantes (hoy, **Vangalia**). Centraliza en una sola cola, en tiempo real, los pedidos de Uber Eats, Rappi y PedidosYa, y ofrece un dashboard y analíticas para el administrador.

| Carpeta | Qué es |
|---|---|
| `kitchan-backend/` | API en FastAPI con PostgreSQL y Redis |
| `frontend/` | Aplicación web en React, TypeScript y Vite |

## Puesta en marcha

Necesitas Docker, Python 3.13 y Node.js.

### 1. Base de datos y Redis

```bash
cd kitchan-backend
docker compose up -d
```

### 2. Configuración

Copia `.env.example` a `.env` y completa los valores (el archivo `.env` real no se sube al repositorio).

### 3. Dependencias del backend

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Migraciones de la base de datos

```bash
alembic upgrade head
```

> **Este paso es obligatorio y hay que repetirlo después de cada `git pull`** que traiga archivos nuevos en `kitchan-backend/alembic/versions/`.
> Si la base de datos queda desactualizada, las consultas de pedidos fallan y el **Dashboard**, la **Cola de pedidos** y el **Historial** muestran un mensaje de error de conexión aunque el servidor esté encendido.
> Para ver en qué versión está tu base: `alembic current` (debe decir `(head)`).

### 5. Backend

```bash
python -m uvicorn src.kitchan.main:app --host 127.0.0.1 --port 8000
```

### 6. Frontend

```bash
cd frontend
npm install
npm run dev
```

La aplicación queda en <http://localhost:5173>.

## Demo

`kitchan-backend/scripts/demo/iniciar_demo.cmd` levanta todo lo necesario para la demo (Docker, APIs falsas de Rappi y PedidosYa, backend, frontend y ngrok) y **aplica las migraciones pendientes** antes de arrancar el backend. El paso a paso está en [`GUION_DEMO.md`](kitchan-backend/scripts/demo/GUION_DEMO.md); para cerrar todo usa `detener_demo.cmd`.

## Pruebas

```bash
cd kitchan-backend
python -m pytest
```

## Configuración útil

| Variable | Para qué sirve |
|---|---|
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Cuenta de correo desde la que salen los códigos de "¿Olvidaste tu contraseña?". Con Gmail: `smtp.gmail.com`, puerto `587` y una contraseña de aplicación. Si `SMTP_HOST` queda vacío, el código no se envía: aparece en la consola del backend (solo para desarrollo). |
| `KITCHAN_ZONA_HORARIA` | Zona horaria del restaurante (por defecto `America/Guayaquil`). Define qué es "hoy" y las horas pico del dashboard; los pedidos se guardan en UTC. |

## Roles

- **Administrador:** Dashboard, Analíticas, Cola de pedidos, Historial, Usuarios e Integraciones.
- **Operador:** Cola de pedidos e Historial.
