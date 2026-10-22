import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import CanalLogo from "../../shared/components/CanalLogo";
import Icon from "../../shared/components/Icon";
import { useOrdersStore } from "../../shared/stores/ordersStore";
import { useSonidoStore } from "../../shared/stores/sonidoStore";
import { sonarNuevoPedido } from "../../shared/utils/sonido";
import type { EstadoPedido, Pedido } from "../../shared/types/pedido";
import { colorVarEstado, ESTADOS_ACTIVOS, ETIQUETA_ESTADO, infoCanal } from "./estadoUtils";
import OrderCard from "./OrderCard";
import OrderDetailModal from "./OrderDetailModal";
import ResumenCola from "./ResumenCola";
import styles from "./ColaPedidosPage.module.css";

// Nombres de las columnas en el lenguaje de la cocina (en las insignias y el historial se mantiene "Nueva", "Lista"…).
const TITULO_COLUMNA: Partial<Record<EstadoPedido, string>> = {
  NUEVA: "Pendientes",
  EN_PREPARACION: "En preparación",
  LISTA: "Listos para entregar",
};

const TEXTO_VACIO: Partial<Record<EstadoPedido, string>> = {
  NUEVA: "Los pedidos nuevos aparecerán aquí automáticamente.",
  EN_PREPARACION: "Nada en cocina por ahora.",
  LISTA: "Sin pedidos esperando retiro.",
};

type Orden = "antiguos" | "recientes" | "monto";

const ORDENES: { valor: Orden; etiqueta: string }[] = [
  { valor: "antiguos", etiqueta: "Más antiguos primero" },
  { valor: "recientes", etiqueta: "Más recientes primero" },
  { valor: "monto", etiqueta: "Mayor monto primero" },
];

/** Texto en el que se busca: cliente, número de pedido y nombre de los platos. */
function textoBuscable(p: Pedido): string {
  return [p.cliente, p.id_externo ?? "", ...p.items.map((i) => i.nombre)].join(" ").toLocaleLowerCase();
}

/** Hora actual que se refresca cada 15 s, para que los tiempos de espera y demoras se mantengan al día. */
function useAhora(): number {
  const [ahora, setAhora] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setAhora(Date.now()), 15000);
    return () => clearInterval(id);
  }, []);
  return ahora;
}

export default function ColaPedidosPage() {
  const pedidosMap = useOrdersStore((s) => s.pedidos);
  const cargado = useOrdersStore((s) => s.cargado);
  const [seleccionado, setSeleccionado] = useState<Pedido | null>(null);
  const sonido = useSonidoStore((s) => s.activo);
  const alternarSonido = useSonidoStore((s) => s.alternar);
  const ahora = useAhora();

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

  const busqueda = params.get("q") ?? "";
  const ordenParam = params.get("orden");
  const orden: Orden = ORDENES.some((o) => o.valor === ordenParam) ? (ordenParam as Orden) : "antiguos";

  const cambiarFiltro = (clave: "estado" | "canal" | "q" | "orden", valor: string) =>
    setParams(
      (previos) => {
        const nuevos = new URLSearchParams(previos);
        if (valor === "" || valor === "TODOS" || (clave === "orden" && valor === "antiguos")) nuevos.delete(clave);
        else nuevos.set(clave, valor);
        return nuevos;
      },
      { replace: true },
    );

  const columnas = filtroEstado === "TODOS" ? ESTADOS_ACTIVOS : [filtroEstado];

  const texto = busqueda.trim().toLocaleLowerCase();
  const coincideBusqueda = (p: Pedido) => !texto || textoBuscable(p).includes(texto);

  const comparar = (a: Pedido, b: Pedido) => {
    if (orden === "recientes") return b.fecha_creacion.localeCompare(a.fecha_creacion);
    if (orden === "monto") return b.total - a.total || a.fecha_creacion.localeCompare(b.fecha_creacion);
    return a.fecha_creacion.localeCompare(b.fecha_creacion);
  };

  const pedidosFiltrados = (estado: EstadoPedido) =>
    pedidos
      .filter((p) => p.estado === estado)
      .filter((p) => filtroCanal === "TODOS" || p.origen === filtroCanal)
      .filter(coincideBusqueda)
      .sort(comparar);

  const pedidosActivos = pedidos.filter((p) => ESTADOS_ACTIVOS.includes(p.estado));
  const activos = pedidosActivos.length;

  // Pedidos por canal con los filtros de estado y búsqueda ya aplicados (el canal elegido no cuenta,
  // para no vaciar el resto de chips).
  const porCanal = new Map<string, number>();
  for (const p of pedidosActivos) {
    if (filtroEstado !== "TODOS" && p.estado !== filtroEstado) continue;
    if (!coincideBusqueda(p)) continue;
    porCanal.set(p.origen, (porCanal.get(p.origen) ?? 0) + 1);
  }
  const totalCanales = Array.from(porCanal.values()).reduce((a, b) => a + b, 0);

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
          <button
            type="button"
            className={`btn btn-secondary ${styles.sonido}`}
            aria-pressed={sonido}
            onClick={() => {
              // Al activarlo suena una vez: confirma el aviso y habilita el audio del navegador.
              if (!sonido) sonarNuevoPedido();
              alternarSonido();
            }}
            title={sonido ? "Silenciar el aviso de pedidos nuevos" : "Activar el aviso de pedidos nuevos"}
          >
            <Icon name={sonido ? "sonido" : "sonidoOff"} size={16} />
            Sonido {sonido ? "activado" : "silenciado"}
          </button>
        </div>
      </div>

      <ResumenCola pedidos={pedidosActivos} ahora={ahora} />

      <div className={styles.barra} role="search">
        <div className={styles.buscador}>
          <Icon name="buscar" size={16} className={styles.buscadorIcono} />
          <input
            type="search"
            name="buscar"
            className={`input ${styles.buscadorInput}`}
            value={busqueda}
            onChange={(e) => cambiarFiltro("q", e.target.value)}
            placeholder="Buscar cliente, pedido o plato…"
            aria-label="Buscar por cliente, número de pedido o plato"
            autoComplete="off"
            spellCheck={false}
          />
        </div>
        <select
          className={`select ${styles.selector}`}
          value={filtroEstado}
          onChange={(e) => cambiarFiltro("estado", e.target.value)}
          aria-label="Filtrar por estado"
        >
          <option value="TODOS">Todos los estados</option>
          {ESTADOS_ACTIVOS.map((estado) => (
            <option key={estado} value={estado}>
              {TITULO_COLUMNA[estado] ?? ETIQUETA_ESTADO[estado]}
            </option>
          ))}
        </select>
        <select
          className={`select ${styles.selector}`}
          value={orden}
          onChange={(e) => cambiarFiltro("orden", e.target.value)}
          aria-label="Ordenar pedidos"
        >
          {ORDENES.map((o) => (
            <option key={o.valor} value={o.valor}>
              {o.etiqueta}
            </option>
          ))}
        </select>
      </div>

      {canales.length > 0 && (
        <div className={styles.chips} role="group" aria-label="Filtrar por canal">
          <button
            type="button"
            className={`${styles.chip} ${filtroCanal === "TODOS" ? styles.chipActivo : ""}`}
            aria-pressed={filtroCanal === "TODOS"}
            onClick={() => cambiarFiltro("canal", "TODOS")}
          >
            Todos
            <span className={styles.chipNumero}>{totalCanales}</span>
          </button>
          {canales.map((canal) => {
            const { nombre, color } = infoCanal(canal);
            const activo = filtroCanal === canal;
            return (
              <button
                key={canal}
                type="button"
                className={`${styles.chip} ${activo ? styles.chipActivo : ""}`}
                aria-pressed={activo}
                onClick={() => cambiarFiltro("canal", activo ? "TODOS" : canal)}
              >
                <CanalLogo canal={canal} color={color} nombre={nombre} size={20} />
                {nombre}
                <span className={styles.chipNumero}>{porCanal.get(canal) ?? 0}</span>
              </button>
            );
          })}
        </div>
      )}

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
                // Texto del encabezado: blanco sobre granate, pizarra sobre ámbar y turquesa (contraste)
                ["--tinta-columna" as string]: estado === "NUEVA" ? "#fff" : "var(--brand-pizarra)",
              }}
            >
              <header className={styles.columnaTitulo}>
                <h2 id={idTitulo} className={styles.columnaNombre}>
                  <span className={styles.columnaPunto} aria-hidden="true" />
                  {TITULO_COLUMNA[estado] ?? ETIQUETA_ESTADO[estado]}
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
