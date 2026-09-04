import { useEffect } from "react";
import { useOrdersStore } from "../../shared/stores/ordersStore";
import { useToastStore } from "../../shared/stores/toastStore";
import type { Toast } from "../../shared/stores/toastStore";
import CancelarPedidoModal from "../pedidos/CancelarPedidoModal";
import { usePedidoAcciones } from "../pedidos/usePedidoAcciones";
import styles from "./ToastContainer.module.css";

const DURACION_MS = 10000;

export default function ToastContainer() {
  const { toasts, remove } = useToastStore();

  return (
    <div className={styles.contenedor}>
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDone={remove} />
      ))}
    </div>
  );
}

function ToastItem({ toast, onDone }: { toast: Toast; onDone: (id: string) => void }) {
  const { id, mensaje, variante } = toast;
  // Usamos el pedido vivo del store (por si ya cambió de estado desde que
  // se creó el toast, ej. otro operador ya lo aceptó) en vez del snapshot.
  const pedidoVivo = useOrdersStore((s) => (toast.pedido ? s.pedidos[toast.pedido.id] : undefined));
  const pedido = pedidoVivo ?? toast.pedido;

  useEffect(() => {
    const timer = setTimeout(() => onDone(id), DURACION_MS);
    return () => clearTimeout(timer);
  }, [id, onDone]);

  const mostrarAcciones = pedido && pedido.estado === "NUEVA";

  return (
    <div className={`${styles.toast} ${variante === "critica" ? styles.critica : ""}`}>
      {mensaje}
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
          className={styles.botonAceptarRapido}
          disabled={procesando}
          onClick={async () => {
            await aceptar();
            onDone();
          }}
        >
          Aceptar
        </button>
        <button
          className={styles.botonCancelarRapido}
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
