import { useEffect, useState } from "react";
import { httpClient } from "../../shared/api/httpClient";
import Icon from "../../shared/components/Icon";
import type { EstadoPedido, Pedido, PedidosPaginados } from "../../shared/types/pedido";
import CanalBadge from "./CanalBadge";
import { colorVarEstado, ETIQUETA_ESTADO, infoCanal } from "./estadoUtils";
import OrderDetailModal from "./OrderDetailModal";
import styles from "./HistorialPage.module.css";

const PAGE_SIZE = 20;
const CANALES_FILTRO = ["UBER_EATS", "RAPPI", "PEDIDOS_YA", "WHATSAPP", "LOCAL"];

export default function HistorialPage() {
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [search, setSearch] = useState("");
  const [estado, setEstado] = useState("");
  const [canal, setCanal] = useState("");
  const [seleccionado, setSeleccionado] = useState<Pedido | null>(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    const params: Record<string, string | number> = { page: pagina, page_size: PAGE_SIZE };
    if (search) params.search = search;
    if (estado) params.estado = estado;
    if (canal) params.canal = canal;

    setCargando(true);
    httpClient
      .get<PedidosPaginados>("/api/v1/pedidos", { params })
      .then(({ data }) => {
        setPedidos(data.resultados);
        setTotal(data.total);
      })
      .finally(() => setCargando(false));
  }, [pagina, search, estado, canal]);

  const totalPaginas = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const primeraCarga = cargando && pedidos.length === 0;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Historial</h1>
          <p className="page-subtitle">
            {total} {total === 1 ? "pedido registrado" : "pedidos registrados"}
          </p>
        </div>
      </div>

      <div className={`${styles.filtros} animate-in`}>
        <div className={styles.filtrosFila}>
          <div className={styles.buscador}>
            <Icon name="buscar" size={16} className={styles.buscadorIcono} />
            <input
              className="input"
              placeholder="Buscar por cliente o id externo..."
              value={search}
              onChange={(e) => {
                setPagina(1);
                setSearch(e.target.value);
              }}
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
              {valor && <span className={styles.chipPunto} />}
              {etiqueta}
            </button>
          ))}
        </div>
      </div>

      <div className={`table-wrap animate-in ${cargando && !primeraCarga ? styles.actualizando : ""}`} style={{ ["--i" as string]: 1 }}>
        <table className="table">
          <thead>
            <tr>
              <th>Cliente</th>
              <th>Canal</th>
              <th>Estado</th>
              <th className="table-num">Total</th>
              <th>Fecha</th>
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

            {pedidos.map((pedido) => (
              <tr key={pedido.id} onClick={() => setSeleccionado(pedido)} className={styles.fila}>
                <td>
                  <div className={styles.cliente}>{pedido.cliente}</div>
                  {pedido.id_externo && <div className={styles.referencia}>#{pedido.id_externo}</div>}
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
                <td className={`table-num ${styles.total}`}>${pedido.total.toFixed(2)}</td>
                <td className={styles.fecha}>
                  <div>{new Date(pedido.fecha_creacion).toLocaleDateString()}</div>
                  <div className={styles.hora}>
                    {new Date(pedido.fecha_creacion).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {!cargando && pedidos.length === 0 && (
          <div className="empty">
            <div className="empty-icon">
              <Icon name="buscar" size={20} />
            </div>
            <span className="empty-title">No hay pedidos para mostrar</span>
            <span>Prueba con otros filtros de búsqueda.</span>
          </div>
        )}
      </div>

      <div className={styles.paginacion}>
        <button
          className="btn btn-secondary btn-sm"
          disabled={pagina <= 1}
          onClick={() => setPagina((p) => p - 1)}
        >
          <Icon name="flecha" size={14} style={{ transform: "rotate(180deg)" }} />
          Anterior
        </button>
        <span className={styles.paginaTexto}>
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
      </div>

      {seleccionado && (
        <OrderDetailModal pedido={seleccionado} onClose={() => setSeleccionado(null)} />
      )}
    </div>
  );
}
