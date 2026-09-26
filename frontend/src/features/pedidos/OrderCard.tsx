import { useEffect, useState } from "react";
import Icon from "../../shared/components/Icon";
import type { Pedido } from "../../shared/types/pedido";
import CanalBadge from "./CanalBadge";
import CancelarPedidoModal from "./CancelarPedidoModal";
import { colorVarEstado, minutosTranscurridos } from "./estadoUtils";
import { usePedidoAcciones } from "./usePedidoAcciones";
import styles from "./OrderCard.module.css";

interface Props {
  pedido: Pedido;
  onAbrir: (pedido: Pedido) => void;
  /** Posición en la columna, para escalonar la animación de entrada. */
  indice?: number;
}

const LIMITE_MINUTOS = 10;

export default function OrderCard({ pedido, onAbrir, indice = 0 }: Props) {
  const [minutos, setMinutos] = useState(() => minutosTranscurridos(pedido.fecha_creacion));

  useEffect(() => {
    const interval = setInterval(() => {
      setMinutos(minutosTranscurridos(pedido.fecha_creacion));
    }, 15000);
    return () => clearInterval(interval);
  }, [pedido.fecha_creacion]);

  const {
    procesando,
    puedeAceptar,
    puedeMarcarListo,
    puedeCancelar,
    puedeCompletar,
    mostrarCancelar,
    setMostrarCancelar,
    aceptar,
    marcarListo,
    marcarEntregado,
    confirmarCancelacion,
  } = usePedidoAcciones(pedido);

  const vencido = minutos >= LIMITE_MINUTOS;
  const unidades = pedido.items.reduce((suma, item) => suma + item.cantidad, 0);
  const resumen = pedido.items.map((item) => `${item.cantidad}× ${item.nombre}`).join(" · ");
  const cargando = procesando ? "is-loading" : "";

  return (
    <article
      className={styles.tarjeta}
      style={{
        ["--borde-estado" as string]: colorVarEstado(pedido.estado),
        ["--i" as string]: Math.min(indice, 6),
      }}
      onClick={() => onAbrir(pedido)}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" && e.target === e.currentTarget) onAbrir(pedido);
      }}
    >
      <div className={styles.encabezado}>
        <span className={styles.cliente}>{pedido.cliente}</span>
        <span className={`${styles.timer} ${vencido ? styles.timerVencido : ""}`}>
          <Icon name="reloj" size={12} strokeWidth={2.5} />
          {minutos} min
        </span>
      </div>

      {resumen && <p className={styles.resumen}>{resumen}</p>}

      <div className={styles.meta}>
        <CanalBadge origen={pedido.origen} />
        <span className={styles.detalle}>
          {unidades} {unidades === 1 ? "ítem" : "ítems"}
          <strong className={styles.total}>${pedido.total.toFixed(2)}</strong>
        </span>
      </div>

      {(puedeAceptar || puedeMarcarListo || puedeCompletar || puedeCancelar) && (
        <div className={styles.acciones} onClick={(e) => e.stopPropagation()}>
          {puedeAceptar && (
            <button className={`btn btn-sm btn-primary ${cargando}`} disabled={procesando} onClick={aceptar}>
              <Icon name="check" size={14} strokeWidth={2.5} />
              Aceptar
            </button>
          )}
          {puedeMarcarListo && (
            <button className={`btn btn-sm btn-success ${cargando}`} disabled={procesando} onClick={marcarListo}>
              <Icon name="check" size={14} strokeWidth={2.5} />
              Listo
            </button>
          )}
          {puedeCompletar && (
            <button className={`btn btn-sm btn-success ${cargando}`} disabled={procesando} onClick={marcarEntregado}>
              <Icon name="check" size={14} strokeWidth={2.5} />
              Entregado
            </button>
          )}
          {puedeCancelar && (
            <button
              className="btn btn-sm btn-danger-soft"
              disabled={procesando}
              onClick={() => setMostrarCancelar(true)}
            >
              Cancelar
            </button>
          )}
        </div>
      )}

      {mostrarCancelar && (
        <div onClick={(e) => e.stopPropagation()}>
          <CancelarPedidoModal
            pedido={pedido}
            onClose={() => setMostrarCancelar(false)}
            onConfirmar={confirmarCancelacion}
          />
        </div>
      )}
    </article>
  );
}
