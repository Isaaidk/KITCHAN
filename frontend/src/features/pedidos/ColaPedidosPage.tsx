import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Icon from "../../shared/components/Icon";
import { useOrdersStore } from "../../shared/stores/ordersStore";
import type { EstadoPedido, Pedido } from "../../shared/types/pedido";
import { colorVarEstado, ESTADOS_ACTIVOS, ETIQUETA_ESTADO, infoCanal } from "./estadoUtils";
import OrderCard from "./OrderCard";
import OrderDetailModal from "./OrderDetailModal";
import styles from "./ColaPedidosPage.module.css";

const TEXTO_VACIO: Partial<Record<EstadoPedido, string>> = {
  NUEVA: "Los pedidos nuevos aparecerán aquí automáticamente.",
  EN_PREPARACION: "Nada en cocina por ahora.",
  LISTA: "Sin pedidos esperando retiro.",
};

export default function ColaPedidosPage() {
  const pedidosMap = useOrdersStore((s) => s.pedidos);
  const cargado = useOrdersStore((s) => s.cargado);
  const [seleccionado, setSeleccionado] = useState<Pedido | null>(null);

  const pedidos = useMemo(() => Object.values(pedidosMap), [pedidosMap]);

  const canales = useMemo(
    () => Array.from(new Set(pedidos.map((p) => p.origen))).sort(),
    [pedidos],
  );

  // Los filtros viven en la URL (?estado=…&canal=…): se pueden compartir,
  // recargar y volver con el botón "atrás". Ausente = "TODOS".
  const [params, setParams] = useSearchParams();
  const estadoParam = params.get("estado");
  const filtroEstado: EstadoPedido | "TODOS" = ESTADOS_ACTIVOS.includes(estadoParam as EstadoPedido)
    ? (estadoParam as EstadoPedido)
    : "TODOS";
  const canalParam = params.get("canal");
  // Los canales se conocen al cargar los pedidos; hasta entonces se respeta el de la URL.
  const filtroCanal = canalParam && (!cargado || canales.includes(canalParam)) ? canalParam : "TODOS";

  const cambiarFiltro = (clave: "estado" | "canal", valor: string) =>
    setParams(
      (previos) => {
        const nuevos = new URLSearchParams(previos);
        if (valor === "TODOS") nuevos.delete(clave);
        else nuevos.set(clave, valor);
        return nuevos;
      },
      { replace: true },
    );

  const columnas = filtroEstado === "TODOS" ? ESTADOS_ACTIVOS : [filtroEstado];

  const pedidosFiltrados = (estado: EstadoPedido) =>
    pedidos
      .filter((p) => p.estado === estado)
      .filter((p) => filtroCanal === "TODOS" || p.origen === filtroCanal)
      .sort((a, b) => a.fecha_creacion.localeCompare(b.fecha_creacion));

  const activos = pedidos.filter((p) => ESTADOS_ACTIVOS.includes(p.estado)).length;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Cola de pedidos</h1>
          <p className="page-subtitle" aria-live="polite">
            {cargado
              ? `${activos} ${activos === 1 ? "pedido activo" : "pedidos activos"} · se actualiza en tiempo real`
              : "Cargando pedidos…"}
          </p>
        </div>

        <div className={styles.filtros}>
          <select
            className="select"
            value={filtroEstado}
            onChange={(e) => cambiarFiltro("estado", e.target.value)}
            aria-label="Filtrar por estado"
          >
            <option value="TODOS">Todos los estados</option>
            {ESTADOS_ACTIVOS.map((estado) => (
              <option key={estado} value={estado}>
                {ETIQUETA_ESTADO[estado]}
              </option>
            ))}
          </select>
          <select
            className="select"
            value={filtroCanal}
            onChange={(e) => cambiarFiltro("canal", e.target.value)}
            aria-label="Filtrar por canal"
          >
            <option value="TODOS">Todos los canales</option>
            {canales.map((canal) => (
              <option key={canal} value={canal}>
                {infoCanal(canal).nombre}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className={styles.tablero} aria-busy={!cargado}>
        {columnas.map((estado, indiceColumna) => {
          const items = pedidosFiltrados(estado);
          const idTitulo = `columna-${estado}`;
          return (
            <section
              key={estado}
              aria-labelledby={idTitulo}
              className={`${styles.columna} animate-in`}
              style={{
                ["--i" as string]: indiceColumna,
                ["--color-columna" as string]: colorVarEstado(estado),
              }}
            >
              <header className={styles.columnaTitulo}>
                <h2 id={idTitulo} className={styles.columnaNombre}>
                  <span className={styles.columnaPunto} aria-hidden="true" />
                  {ETIQUETA_ESTADO[estado]}
                </h2>
                <span className={styles.contador} key={items.length}>
                  {items.length}
                  <span className="sr-only"> {items.length === 1 ? "pedido" : "pedidos"}</span>
                </span>
              </header>

              <div className={styles.tarjetas}>
                {!cargado &&
                  [0, 1].map((i) => (
                    <div key={i} className={styles.skeletonCard}>
                      <div className="skeleton" style={{ height: 14, width: "60%" }} />
                      <div className="skeleton" style={{ height: 10, width: "40%" }} />
                      <div className="skeleton" style={{ height: 32, width: "100%" }} />
                    </div>
                  ))}

                {cargado && items.length === 0 && (
                  <div className="empty">
                    <div className="empty-icon">
                      <Icon name="bandeja" size={20} />
                    </div>
                    <span className="empty-title">Sin pedidos</span>
                    <span>{TEXTO_VACIO[estado]}</span>
                  </div>
                )}

                {items.map((pedido, i) => (
                  <OrderCard key={pedido.id} pedido={pedido} indice={i} onAbrir={setSeleccionado} />
                ))}
              </div>
            </section>
          );
        })}
      </div>

      {seleccionado && (
        <OrderDetailModal pedido={seleccionado} onClose={() => setSeleccionado(null)} />
      )}
    </div>
  );
}
