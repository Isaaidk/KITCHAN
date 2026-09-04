import { useEffect, useState } from "react";
import type { Pedido } from "../../shared/types/pedido";
import CancelarPedidoModal from "./CancelarPedidoModal";
import { colorVarEstado, minutosTranscurridos } from "./estadoUtils";
import { usePedidoAcciones } from "./usePedidoAcciones";
import styles from "./OrderCard.module.css";

interface Props {
  pedido: Pedido;
  onAbrir: (pedido: Pedido) => void;
}

const LIMITE_MINUTOS = 10;

export default function OrderCard({ pedido, onAbrir }: Props) {
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

  return (
    <div
      className={styles.tarjeta}
      style={{ ["--borde-estado" as string]: colorVarEstado(pedido.estado) }}
      onClick={() => onAbrir(pedido)}
    >
      <div className={styles.encabezado}>
        <span className={styles.cliente}>{pedido.cliente}</span>
        <span className={`${styles.timer} ${vencido ? styles.timerVencido : ""}`}>
          {minutos} min
        </span>
      </div>
      <div className={styles.meta}>
        <span>{pedido.origen}</span>
        <span>${pedido.total.toFixed(2)}</span>
      </div>

      <div className={styles.acciones} onClick={(e) => e.stopPropagation()}>
        {puedeAceptar && (
          <button className={`${styles.boton} ${styles.aceptar}`} disabled={procesando} onClick={aceptar}>
            Aceptar
          </button>
        )}
        {puedeMarcarListo && (
          <button className={`${styles.boton} ${styles.listo}`} disabled={procesando} onClick={marcarListo}>
            Listo
          </button>
        )}
        {puedeCompletar && (
          <button className={`${styles.boton} ${styles.listo}`} disabled={procesando} onClick={marcarEntregado}>
            Entregado
          </button>
        )}
        {puedeCancelar && (
          <button
            className={`${styles.boton} ${styles.cancelar}`}
            disabled={procesando}
            onClick={() => setMostrarCancelar(true)}
          >
            Cancelar
          </button>
        )}
      </div>

      {mostrarCancelar && (
        <div onClick={(e) => e.stopPropagation()}>
          <CancelarPedidoModal
            pedido={pedido}
            onClose={() => setMostrarCancelar(false)}
            onConfirmar={confirmarCancelacion}
          />
        </div>
      )}
    </div>
  );
}
