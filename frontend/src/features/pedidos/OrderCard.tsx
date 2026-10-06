import { useEffect, useState } from "react";
import Icon from "../../shared/components/Icon";
import type { Pedido } from "../../shared/types/pedido";
import CanalLogo from "../../shared/components/CanalLogo";
import { moneda } from "../../shared/utils/formato";
import CancelarPedidoModal from "./CancelarPedidoModal";
import { colorVarEstado, infoCanal, minutosTranscurridos } from "./estadoUtils";
import { usePedidoAcciones } from "./usePedidoAcciones";
import styles from "./OrderCard.module.css";

interface Props {
  pedido: Pedido;
  onAbrir: (pedido: Pedido) => void;
  /** Posición en la columna, para escalonar la animación de entrada. */
  indice?: number;
}

const LIMITE_MINUTOS = 10;
const MAX_ITEMS_VISIBLES = 3;

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
  const visibles = pedido.items.slice(0, MAX_ITEMS_VISIBLES);
  const ocultos = pedido.items.length - visibles.length;
  const canal = infoCanal(pedido.origen);
  const progreso = Math.min(minutos / LIMITE_MINUTOS, 1);
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
        <CanalLogo canal={pedido.origen} color={canal.color} nombre={canal.nombre} size={34} />
        <div className={styles.identidad}>
          <span className={styles.cliente}>{pedido.cliente}</span>
          <span className={styles.origen}>
            {canal.nombre}
            {pedido.id_externo && <span className={styles.referencia}>#{pedido.id_externo.length > 10 ? pedido.id_externo.slice(-6) : pedido.id_externo}</span>}
          </span>
        </div>
        <span className={`${styles.timer} ${vencido ? styles.timerVencido : ""}`}>
          <Icon name="reloj" size={12} strokeWidth={2.5} />
          {minutos} min
        </span>
      </div>

      <div className={styles.tiempo} aria-hidden="true">
        <span className={styles.tiempoBarra} style={{ width: `${progreso * 100}%` }} />
      </div>

      {visibles.length > 0 && (
        <ul className={styles.items}>
          {visibles.map((item, i) => (
            <li key={`${item.nombre}-${i}`}>
              <span className={styles.cantidad}>{item.cantidad}×</span>
              <span className={styles.itemNombre}>
                {item.nombre}
                {item.notas && <em className={styles.itemNota}>{item.notas}</em>}
              </span>
            </li>
          ))}
          {ocultos > 0 && <li className={styles.masItems}>+{ocultos} más</li>}
        </ul>
      )}

      <div className={styles.meta}>
        <span className={styles.detalle}>
          {unidades} {unidades === 1 ? "ítem" : "ítems"}
        </span>
        <strong className={styles.total}>{moneda(pedido.total)}</strong>
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
