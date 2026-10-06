import { useEffect, useState } from "react";
import { httpClient } from "../../shared/api/httpClient";
import Icon from "../../shared/components/Icon";
import type { EstadoPedido, Pedido, PedidosPaginados } from "../../shared/types/pedido";
import { moneda } from "../../shared/utils/formato";
import CanalBadge from "./CanalBadge";
import { colorVarEstado, ETIQUETA_ESTADO, infoCanal } from "./estadoUtils";
import OrderDetailModal from "./OrderDetailModal";
import styles from "./HistorialPage.module.css";

const PAGE_SIZE = 20;
const CANALES_FILTRO = ["UBER_EATS", "RAPPI", "PEDIDOS_YA", "WHATSAPP", "LOCAL"];
// Espera tras la última tecla antes de consultar: evita una petición por letra.
const ESPERA_BUSQUEDA_MS = 300;

// Se crean una sola vez (no por fila) y siguen el idioma del navegador.
const formatoFecha = new Intl.DateTimeFormat(undefined, { dateStyle: "short" });
const formatoHora = new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" });

export default function HistorialPage() {
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  // `busqueda` es lo que se ve en el campo; `search` es lo que se consulta.
  const [busqueda, setBusqueda] = useState("");
  const [search, setSearch] = useState("");
  const [estado, setEstado] = useState("");
  const [canal, setCanal] = useState("");
  const [seleccionado, setSeleccionado] = useState<Pedido | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(false);
  // Se incrementa para volver a pedir los datos tras un error.
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    const espera = setTimeout(() => {
      setPagina(1);
      setSearch(busqueda.trim());
    }, ESPERA_BUSQUEDA_MS);
    return () => clearTimeout(espera);
  }, [busqueda]);

  useEffect(() => {
    const params: Record<string, string | number> = { page: pagina, page_size: PAGE_SIZE };
    if (search) params.search = search;
    if (estado) params.estado = estado;
    if (canal) params.canal = canal;

    // `vigente` descarta respuestas de consultas que ya fueron reemplazadas.
    let vigente = true;
    setCargando(true);
    setError(false);
    httpClient
      .get<PedidosPaginados>("/api/v1/pedidos", { params })
      .then(({ data }) => {
        if (!vigente) return;
        setPedidos(data.resultados);
        setTotal(data.total);
      })
      .catch(() => {
        if (!vigente) return;
        // Se vacía la tabla: mostrar filas de otra consulta bajo filtros nuevos engaña.
        setPedidos([]);
        setError(true);
      })
      .finally(() => {
        if (vigente) setCargando(false);
      });
    return () => {
      vigente = false;
    };
  }, [pagina, search, estado, canal, intento]);

  const totalPaginas = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const primeraCarga = cargando && pedidos.length === 0;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Historial</h1>
          <p className="page-subtitle" aria-live="polite">
            {error
              ? "No se pudo obtener el total"
              : `${total} ${total === 1 ? "pedido registrado" : "pedidos registrados"}`}
          </p>
        </div>
      </div>

      <div className={`${styles.filtros} animate-in`}>
        <div className={styles.filtrosFila}>
          <div className={styles.buscador}>
            <Icon name="buscar" size={16} className={styles.buscadorIcono} />
            <input
              className="input"
              type="search"
              name="busqueda"
              aria-label="Buscar pedidos por cliente o id externo"
              autoComplete="off"
              spellCheck={false}
              placeholder="Buscar por cliente o id externo…"
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
            />
          </div>
          <select
            className={`select ${styles.selectCanal}`}
            value={canal}
            onChange={(e) => {
              setPagina(1);
              setCanal(e.target.value);
            }}
            aria-label="Filtrar por canal"
          >
            <option value="">Todos los canales</option>
            {CANALES_FILTRO.map((valor) => (
              <option key={valor} value={valor}>
                {infoCanal(valor).nombre}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.chips} role="group" aria-label="Filtrar por estado">
          {[["", "Todos"], ...Object.entries(ETIQUETA_ESTADO)].map(([valor, etiqueta]) => (
            <button
              key={valor || "todos"}
              type="button"
              aria-pressed={estado === valor}
              className={`${styles.chip} ${estado === valor ? styles.chipActivo : ""}`}
              style={valor ? { ["--chip-color" as string]: colorVarEstado(valor as EstadoPedido) } : undefined}
              onClick={() => {
                setPagina(1);
                setEstado(valor);
              }}
            >
              {valor && <span className={styles.chipPunto} aria-hidden="true" />}
              {etiqueta}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          <Icon name="alerta" size={16} />
          <span className={styles.errorTexto}>No se pudo cargar el historial. Revisa la conexión e inténtalo de nuevo.</span>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => setIntento((n) => n + 1)}>
            <Icon name="sync" size={14} />
            Reintentar
          </button>
        </div>
      )}

      <div
        className={`table-wrap animate-in ${cargando && !primeraCarga ? styles.actualizando : ""}`}
        style={{ ["--i" as string]: 1 }}
        aria-busy={cargando}
      >
        <table className="table">
          <caption className="sr-only">Historial de pedidos</caption>
          <thead>
            <tr>
              <th scope="col">Cliente</th>
              <th scope="col">Canal</th>
              <th scope="col">Estado</th>
              <th scope="col" className="table-num">
                Total
              </th>
              <th scope="col">Fecha</th>
            </tr>
          </thead>
          <tbody>
            {primeraCarga &&
              Array.from({ length: 6 }).map((_, i) => (
                <tr key={i}>
                  {[140, 80, 90, 60, 130].map((ancho, j) => (
                    <td key={j}>
                      <div className="skeleton" style={{ height: 12, width: ancho, marginLeft: j === 3 ? "auto" : 0 }} />
                    </td>
                  ))}
                </tr>
              ))}

            {pedidos.map((pedido) => {
              const fecha = new Date(pedido.fecha_creacion);
              return (
                <tr key={pedido.id} onClick={() => setSeleccionado(pedido)} className={styles.fila}>
                  <td>
                    {/* El clic en toda la fila sigue funcionando con mouse; este botón es el
                        punto de acceso para teclado y lectores de pantalla. */}
                    <button
                      type="button"
                      className={`${styles.cliente} ${styles.clienteBoton}`}
                      onClick={() => setSeleccionado(pedido)}
                      aria-haspopup="dialog"
                      title={pedido.cliente}
                    >
                      {pedido.cliente}
                    </button>
                    {pedido.id_externo && (
                      <div className={styles.referencia} translate="no">
                        #{pedido.id_externo}
                      </div>
                    )}
                  </td>
                  <td>
                    <CanalBadge origen={pedido.origen} />
                  </td>
                  <td>
                    <span
                      className="badge badge-dot"
                      style={{ ["--badge-color" as string]: colorVarEstado(pedido.estado) }}
                    >
                      {ETIQUETA_ESTADO[pedido.estado]}
                    </span>
                  </td>
                  <td className={`table-num ${styles.total}`}>{moneda(pedido.total)}</td>
                  <td className={styles.fecha}>
                    <time dateTime={pedido.fecha_creacion}>
                      <span className={styles.bloque}>{formatoFecha.format(fecha)}</span>
                      <span className={`${styles.bloque} ${styles.hora}`}>{formatoHora.format(fecha)}</span>
                    </time>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {primeraCarga && <span className="sr-only" role="status">Cargando pedidos…</span>}

        {!cargando && !error && pedidos.length === 0 && (
          <div className="empty">
            <div className="empty-icon">
              <Icon name="buscar" size={20} />
            </div>
            <span className="empty-title">No hay pedidos para mostrar</span>
            <span>Prueba con otros filtros de búsqueda.</span>
          </div>
        )}
      </div>

      <nav className={styles.paginacion} aria-label="Paginación del historial">
        <button
          className="btn btn-secondary btn-sm"
          disabled={pagina <= 1}
          onClick={() => setPagina((p) => p - 1)}
        >
          <Icon name="flecha" size={14} style={{ transform: "rotate(180deg)" }} />
          Anterior
        </button>
        <span className={styles.paginaTexto} aria-live="polite">
          Página <strong>{pagina}</strong> de {totalPaginas}
        </span>
        <button
          className="btn btn-secondary btn-sm"
          disabled={pagina >= totalPaginas}
          onClick={() => setPagina((p) => p + 1)}
        >
          Siguiente
          <Icon name="flecha" size={14} />
        </button>
      </nav>

      {seleccionado && (
        <OrderDetailModal pedido={seleccionado} onClose={() => setSeleccionado(null)} />
      )}
    </div>
  );
}
