import { useEffect, useState } from "react";
import Icon, { type NombreIcono } from "../../shared/components/Icon";
import { useOrdersStore } from "../../shared/stores/ordersStore";
import { useToastStore } from "../../shared/stores/toastStore";
import { moneda } from "../../shared/utils/formato";
import type { Toast } from "../../shared/stores/toastStore";
import CanalBadge from "../pedidos/CanalBadge";
import CancelarPedidoModal from "../pedidos/CancelarPedidoModal";
import { usePedidoAcciones } from "../pedidos/usePedidoAcciones";
import styles from "./ToastContainer.module.css";

const DURACION_MS = 10000;
// La salida arranca un poco antes para que el toast se desvanezca
// justo cuando termina su barra de tiempo.
const SALIDA_MS = 280;

export default function ToastContainer() {
  const { toasts, remove } = useToastStore();

  return (
    <div className={styles.contenedor} aria-live="polite">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDone={remove} />
      ))}
    </div>
  );
}

function ToastItem({ toast, onDone }: { toast: Toast; onDone: (id: string) => void }) {
  const { id, mensaje, variante } = toast;
  const [saliendo, setSaliendo] = useState(false);
  // Usamos el pedido vivo del store (por si ya cambió de estado desde que
  // se creó el toast, ej. otro operador ya lo aceptó) en vez del snapshot.
  const pedidoVivo = useOrdersStore((s) => (toast.pedido ? s.pedidos[toast.pedido.id] : undefined));
  const pedido = pedidoVivo ?? toast.pedido;

  useEffect(() => {
    const salida = setTimeout(() => setSaliendo(true), DURACION_MS - SALIDA_MS);
    const timer = setTimeout(() => onDone(id), DURACION_MS);
    return () => {
      clearTimeout(salida);
      clearTimeout(timer);
    };
  }, [id, onDone]);

  const cerrar = () => {
    setSaliendo(true);
    setTimeout(() => onDone(id), SALIDA_MS);
  };

  const mostrarAcciones = pedido && pedido.estado === "NUEVA";

  // Tono del toast: nuevo pedido (azul), cancelación (rojo) o aviso positivo (verde).
  const tono = variante === "critica" ? "critica" : toast.pedido ? "nuevo" : "exito";
  const icono: NombreIcono = tono === "critica" ? "prohibido" : tono === "nuevo" ? "bandeja" : "check";

  return (
    <div
      className={`${styles.toast} ${styles[tono]} ${saliendo ? styles.saliendo : ""}`}
      role="status"
    >
      <div className={styles.cuerpo}>
        <div className={styles.icono}>
          <Icon name={icono} size={16} strokeWidth={2.4} />
        </div>
        <div className={styles.texto}>
          <div className={styles.mensaje}>{mensaje}</div>
          {toast.pedido && (
            <div className={styles.meta}>
              <CanalBadge origen={toast.pedido.origen} />
              <span className={styles.total}>{moneda(toast.pedido.total)}</span>
            </div>
          )}
        </div>
        <button className={styles.cerrar} onClick={cerrar} aria-label="Cerrar notificación">
          <Icon name="cerrar" size={14} />
        </button>
      </div>
      {mostrarAcciones && pedido && <AccionesToast pedido={pedido} onDone={() => onDone(id)} />}
      <div className={styles.barra} />
    </div>
  );
}

function AccionesToast({ pedido, onDone }: { pedido: NonNullable<Toast["pedido"]>; onDone: () => void }) {
  const { procesando, aceptar, mostrarCancelar, setMostrarCancelar, confirmarCancelacion } =
    usePedidoAcciones(pedido);

  return (
    <>
      <div className={styles.accionesRapidas}>
        <button
          className={`btn btn-sm btn-primary ${procesando ? "is-loading" : ""}`}
          disabled={procesando}
          onClick={async () => {
            await aceptar();
            onDone();
          }}
        >
          Aceptar
        </button>
        <button
          className="btn btn-sm btn-danger-soft"
          disabled={procesando}
          onClick={() => setMostrarCancelar(true)}
        >
          Cancelar
        </button>
      </div>
      {mostrarCancelar && (
        <CancelarPedidoModal
          pedido={pedido}
          onClose={() => setMostrarCancelar(false)}
          onConfirmar={async (reasonCode, explanation) => {
            await confirmarCancelacion(reasonCode, explanation);
            onDone();
          }}
        />
      )}
    </>
  );
}
