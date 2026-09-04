import { useMemo, useState } from "react";
import { useOrdersStore } from "../../shared/stores/ordersStore";
import type { EstadoPedido, Pedido } from "../../shared/types/pedido";
import { ESTADOS_ACTIVOS, ETIQUETA_ESTADO } from "./estadoUtils";
import OrderCard from "./OrderCard";
import OrderDetailModal from "./OrderDetailModal";
import styles from "./ColaPedidosPage.module.css";

export default function ColaPedidosPage() {
  const pedidosMap = useOrdersStore((s) => s.pedidos);
  const [filtroEstado, setFiltroEstado] = useState<EstadoPedido | "TODOS">("TODOS");
  const [filtroCanal, setFiltroCanal] = useState<string>("TODOS");
  const [seleccionado, setSeleccionado] = useState<Pedido | null>(null);

  const pedidos = useMemo(() => Object.values(pedidosMap), [pedidosMap]);

  const canales = useMemo(
    () => Array.from(new Set(pedidos.map((p) => p.origen))).sort(),
    [pedidos],
  );

  const columnas = filtroEstado === "TODOS" ? ESTADOS_ACTIVOS : [filtroEstado];

  const pedidosFiltrados = (estado: EstadoPedido) =>
    pedidos
      .filter((p) => p.estado === estado)
      .filter((p) => filtroCanal === "TODOS" || p.origen === filtroCanal)
      .sort((a, b) => a.fecha_creacion.localeCompare(b.fecha_creacion));

  return (
    <div>
      <div className={styles.filtros}>
        <select
          value={filtroEstado}
          onChange={(e) => setFiltroEstado(e.target.value as EstadoPedido | "TODOS")}
        >
          <option value="TODOS">Todos los estados</option>
          {ESTADOS_ACTIVOS.map((estado) => (
            <option key={estado} value={estado}>
              {ETIQUETA_ESTADO[estado]}
            </option>
          ))}
        </select>
        <select value={filtroCanal} onChange={(e) => setFiltroCanal(e.target.value)}>
          <option value="TODOS">Todos los canales</option>
          {canales.map((canal) => (
            <option key={canal} value={canal}>
              {canal}
            </option>
          ))}
        </select>
      </div>

      <div className={styles.tablero}>
        {columnas.map((estado) => {
          const items = pedidosFiltrados(estado);
          return (
            <div key={estado} className={styles.columna}>
              <div className={styles.columnaTitulo}>
                <span>{ETIQUETA_ESTADO[estado]}</span>
                <span>{items.length}</span>
              </div>
              <div className={styles.tarjetas}>
                {items.length === 0 && <div className={styles.vacio}>Sin pedidos</div>}
                {items.map((pedido) => (
                  <OrderCard key={pedido.id} pedido={pedido} onAbrir={setSeleccionado} />
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {seleccionado && (
        <OrderDetailModal pedido={seleccionado} onClose={() => setSeleccionado(null)} />
      )}
    </div>
  );
}
