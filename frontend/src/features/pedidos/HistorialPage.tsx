import { useEffect, useState } from "react";
import { httpClient } from "../../shared/api/httpClient";
import type { Pedido, PedidosPaginados } from "../../shared/types/pedido";
import { colorVarEstado, ETIQUETA_ESTADO } from "./estadoUtils";
import OrderDetailModal from "./OrderDetailModal";
import styles from "./HistorialPage.module.css";

const PAGE_SIZE = 20;

export default function HistorialPage() {
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [search, setSearch] = useState("");
  const [estado, setEstado] = useState("");
  const [canal, setCanal] = useState("");
  const [seleccionado, setSeleccionado] = useState<Pedido | null>(null);

  useEffect(() => {
    const params: Record<string, string | number> = { page: pagina, page_size: PAGE_SIZE };
    if (search) params.search = search;
    if (estado) params.estado = estado;
    if (canal) params.canal = canal;

    httpClient.get<PedidosPaginados>("/api/v1/pedidos", { params }).then(({ data }) => {
      setPedidos(data.resultados);
      setTotal(data.total);
    });
  }, [pagina, search, estado, canal]);

  const totalPaginas = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <div className={styles.filtros}>
        <input
          placeholder="Buscar por cliente o id externo..."
          value={search}
          onChange={(e) => {
            setPagina(1);
            setSearch(e.target.value);
          }}
        />
        <select
          value={estado}
          onChange={(e) => {
            setPagina(1);
            setEstado(e.target.value);
          }}
        >
          <option value="">Todos los estados</option>
          {Object.entries(ETIQUETA_ESTADO).map(([valor, etiqueta]) => (
            <option key={valor} value={valor}>
              {etiqueta}
            </option>
          ))}
        </select>
        <input
          placeholder="Canal (ej. UBER_EATS)"
          value={canal}
          onChange={(e) => {
            setPagina(1);
            setCanal(e.target.value);
          }}
        />
      </div>

      <table className={styles.tabla}>
        <thead>
          <tr>
            <th>Cliente</th>
            <th>Canal</th>
            <th>Estado</th>
            <th>Total</th>
            <th>Fecha</th>
          </tr>
        </thead>
        <tbody>
          {pedidos.map((pedido) => (
            <tr key={pedido.id} onClick={() => setSeleccionado(pedido)} style={{ cursor: "pointer" }}>
              <td>{pedido.cliente}</td>
              <td>{pedido.origen}</td>
              <td>
                <span
                  className={styles.badge}
                  style={{ background: colorVarEstado(pedido.estado) }}
                >
                  {ETIQUETA_ESTADO[pedido.estado]}
                </span>
              </td>
              <td>${pedido.total.toFixed(2)}</td>
              <td>{new Date(pedido.fecha_creacion).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className={styles.paginacion}>
        <button disabled={pagina <= 1} onClick={() => setPagina((p) => p - 1)}>
          Anterior
        </button>
        <span>
          Página {pagina} de {totalPaginas}
        </span>
        <button disabled={pagina >= totalPaginas} onClick={() => setPagina((p) => p + 1)}>
          Siguiente
        </button>
      </div>

      {seleccionado && (
        <OrderDetailModal pedido={seleccionado} onClose={() => setSeleccionado(null)} />
      )}
    </div>
  );
}
