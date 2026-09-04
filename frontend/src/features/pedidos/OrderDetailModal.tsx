import Modal from "../../shared/components/Modal";
import type { Pedido } from "../../shared/types/pedido";
import { useOdooSyncStub } from "../integraciones/useOdooSyncStub";
import CancelarPedidoModal from "./CancelarPedidoModal";
import { ETIQUETA_ESTADO } from "./estadoUtils";
import { usePedidoAcciones } from "./usePedidoAcciones";
import styles from "./OrderDetailModal.module.css";

const PASOS: Array<Pedido["estado"]> = ["NUEVA", "EN_PREPARACION", "LISTA", "ENTREGADA"];

interface Props {
  pedido: Pedido;
  onClose: () => void;
}

export default function OrderDetailModal({ pedido, onClose }: Props) {
  const { estado: estadoOdoo, ejecutar } = useOdooSyncStub();
  const cancelado = pedido.estado === "CANCELADA";
  const indiceActual = PASOS.indexOf(pedido.estado);

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

  return (
    <Modal titulo={`Pedido de ${pedido.cliente}`} onClose={onClose}>
      <div className={styles.timeline}>
        {cancelado ? (
          <div className={`${styles.paso} ${styles.cancelada}`}>
            <div className={styles.punto} />
            Cancelada
          </div>
        ) : (
          PASOS.map((paso, i) => (
            <div
              key={paso}
              className={`${styles.paso} ${i <= indiceActual ? styles.pasoActivo : ""}`}
            >
              <div className={styles.punto} />
              {ETIQUETA_ESTADO[paso]}
            </div>
          ))
        )}
      </div>

      {(puedeAceptar || puedeMarcarListo || puedeCompletar || puedeCancelar) && (
        <div className={styles.acciones}>
          {puedeAceptar && (
            <button className={styles.botonAceptar} disabled={procesando} onClick={aceptar}>
              Aceptar
            </button>
          )}
          {puedeMarcarListo && (
            <button className={styles.botonListo} disabled={procesando} onClick={marcarListo}>
              Listo
            </button>
          )}
          {puedeCompletar && (
            <button className={styles.botonListo} disabled={procesando} onClick={marcarEntregado}>
              Entregado
            </button>
          )}
          {puedeCancelar && (
            <button
              className={styles.botonCancelar}
              disabled={procesando}
              onClick={() => setMostrarCancelar(true)}
            >
              Cancelar
            </button>
          )}
        </div>
      )}

      <table className={styles.tablaItems}>
        <thead>
          <tr>
            <th>Ítem</th>
            <th>Cant.</th>
            <th>Subtotal</th>
          </tr>
        </thead>
        <tbody>
          {pedido.items.map((item, i) => (
            <tr key={i}>
              <td>{item.nombre}</td>
              <td>{item.cantidad}</td>
              <td>${(item.precio_unitario * item.cantidad).toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className={styles.total}>Total: ${pedido.total.toFixed(2)}</div>

      {pedido.nota_cliente && <div className={styles.notaCliente}>{pedido.nota_cliente}</div>}

      <div className={styles.odoo}>
        <div>
          <div className={styles.odooTitulo}>Sincronización ODOO</div>
          <div className={styles.odooEstado}>
            {estadoOdoo === "idle" && "Sin sincronizar"}
            {estadoOdoo === "sincronizando" && "Sincronizando..."}
            {estadoOdoo === "no_disponible" && "Disponible próximamente"}
          </div>
        </div>
        <button
          className={styles.odooBoton}
          disabled={estadoOdoo === "sincronizando"}
          onClick={ejecutar}
        >
          Sincronizar
        </button>
      </div>

      {mostrarCancelar && (
        <CancelarPedidoModal
          pedido={pedido}
          onClose={() => setMostrarCancelar(false)}
          onConfirmar={confirmarCancelacion}
        />
      )}
    </Modal>
  );
}
