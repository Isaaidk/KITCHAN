import Icon from "../../shared/components/Icon";
import Modal from "../../shared/components/Modal";
import type { Pedido } from "../../shared/types/pedido";
import { useOdooSyncStub } from "../integraciones/useOdooSyncStub";
import CanalBadge from "./CanalBadge";
import CancelarPedidoModal from "./CancelarPedidoModal";
import { colorVarEstado, ETIQUETA_ESTADO, infoCanal } from "./estadoUtils";
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
  // Porcentaje de la línea de progreso entre el primer y el último paso.
  const progreso = Math.max(0, indiceActual) / (PASOS.length - 1);

  const {
    procesando,
    puedeAceptar,
    puedeMarcarListo,
    puedeCancelar,
    puedeCompletar,
    cancelacionSoloPorSoporte,
    mostrarCancelar,
    setMostrarCancelar,
    aceptar,
    marcarListo,
    marcarEntregado,
    confirmarCancelacion,
  } = usePedidoAcciones(pedido);

  const cargando = procesando ? "is-loading" : "";
  const nombreCanal = infoCanal(pedido.origen).nombre;

  return (
    <Modal titulo={`Pedido de ${pedido.cliente}`} onClose={onClose} ancho={560}>
      <div className={styles.resumen}>
        <CanalBadge origen={pedido.origen} />
        <span
          className="badge badge-dot"
          style={{ ["--badge-color" as string]: colorVarEstado(pedido.estado) }}
        >
          {ETIQUETA_ESTADO[pedido.estado]}
        </span>
        <span className={styles.fecha}>
          <Icon name="reloj" size={13} />
          {new Date(pedido.fecha_creacion).toLocaleString()}
        </span>
      </div>

      {cancelado ? (
        <div className="alert alert-error" style={{ animation: "none" }}>
          <Icon name="prohibido" size={16} />
          Este pedido fue cancelado.
        </div>
      ) : (
        <div
          className={styles.timeline}
          style={{ ["--progreso" as string]: progreso }}
        >
          <div className={styles.linea}>
            <div className={styles.lineaRelleno} />
          </div>
          {PASOS.map((paso, i) => (
            <div
              key={paso}
              className={`${styles.paso} ${i <= indiceActual ? styles.pasoActivo : ""} ${
                i === indiceActual ? styles.pasoActual : ""
              }`}
              style={{ ["--i" as string]: i }}
            >
              <div className={styles.punto}>
                {i < indiceActual && <Icon name="check" size={12} strokeWidth={3} />}
              </div>
              <span className={styles.pasoTexto}>{ETIQUETA_ESTADO[paso]}</span>
            </div>
          ))}
        </div>
      )}

      {(puedeAceptar || puedeMarcarListo || puedeCompletar || puedeCancelar) && (
        <div className={styles.acciones}>
          {puedeAceptar && (
            <button className={`btn btn-primary ${cargando}`} disabled={procesando} onClick={aceptar}>
              <Icon name="check" size={16} strokeWidth={2.5} />
              Aceptar
            </button>
          )}
          {puedeMarcarListo && (
            <button className={`btn btn-success ${cargando}`} disabled={procesando} onClick={marcarListo}>
              <Icon name="check" size={16} strokeWidth={2.5} />
              Listo
            </button>
          )}
          {puedeCompletar && (
            <button className={`btn btn-success ${cargando}`} disabled={procesando} onClick={marcarEntregado}>
              <Icon name="check" size={16} strokeWidth={2.5} />
              Entregado
            </button>
          )}
          {puedeCancelar && (
            <button
              className="btn btn-danger-soft"
              disabled={procesando}
              onClick={() => setMostrarCancelar(true)}
            >
              Cancelar
            </button>
          )}
        </div>
      )}

      {cancelacionSoloPorSoporte && (
        <div className="alert alert-warning" style={{ animation: "none" }}>
          <Icon name="alerta" size={16} />
          <span>
            {nombreCanal} no permite cancelar un pedido ya aceptado desde KITCHAN. Si necesitas
            cancelarlo, comunícate con el soporte de {nombreCanal}.
          </span>
        </div>
      )}

      <div className={styles.items}>
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
                <td>
                  {item.nombre}
                  {item.notas && <div className={styles.itemNota}>{item.notas}</div>}
                </td>
                <td>
                  <span className={styles.cantidad}>{item.cantidad}</span>
                </td>
                <td>${(item.precio_unitario * item.cantidad).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className={styles.total}>
          <span>Total</span>
          <span className={styles.totalValor}>${pedido.total.toFixed(2)}</span>
        </div>
      </div>

      {pedido.nota_cliente && (
        <div className={styles.notaCliente}>
          <Icon name="nota" size={16} />
          <div>
            <div className={styles.notaTitulo}>Nota del cliente</div>
            {pedido.nota_cliente}
          </div>
        </div>
      )}

      <div className={styles.odoo}>
        <div className={styles.odooInfo}>
          <div className={styles.odooIcono}>
            <Icon name="sync" size={16} />
          </div>
          <div>
            <div className={styles.odooTitulo}>Sincronización ODOO</div>
            <div className={styles.odooEstado}>
              {estadoOdoo === "idle" && "Sin sincronizar"}
              {estadoOdoo === "sincronizando" && "Sincronizando..."}
              {estadoOdoo === "no_disponible" && "Disponible próximamente"}
            </div>
          </div>
        </div>
        <button
          className={`btn btn-secondary btn-sm ${estadoOdoo === "sincronizando" ? "is-loading" : ""}`}
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
