import CanalLogo from "../../shared/components/CanalLogo";
import Icon from "../../shared/components/Icon";
import Modal from "../../shared/components/Modal";
import type { Pedido } from "../../shared/types/pedido";
import { moneda } from "../../shared/utils/formato";
import { useOdooSyncStub } from "../integraciones/useOdooSyncStub";
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
  const canal = infoCanal(pedido.origen);
  const nombreCanal = canal.nombre;
  const unidades = pedido.items.reduce((suma, item) => suma + item.cantidad, 0);

  return (
    <Modal titulo={`Pedido de ${pedido.cliente}`} onClose={onClose} ancho={560}>
      <div className={styles.cabecera}>
        <CanalLogo canal={pedido.origen} color={canal.color} nombre={canal.nombre} size={48} />
        <div className={styles.cabeceraTexto}>
          <div className={styles.cliente}>{pedido.cliente}</div>
          <div className={styles.origen}>
            {canal.nombre}
            {pedido.id_externo && <span className={styles.referencia}>#{pedido.id_externo}</span>}
          </div>
        </div>
        <span
          className="badge badge-dot"
          style={{ ["--badge-color" as string]: colorVarEstado(pedido.estado) }}
        >
          {ETIQUETA_ESTADO[pedido.estado]}
        </span>
      </div>

      <div className={styles.datos}>
        <span className={styles.dato}>
          <Icon name="reloj" size={13} />
          {new Date(pedido.fecha_creacion).toLocaleString([], {
            day: "numeric",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
        {pedido.estado_entrega && (
          <span className={styles.dato}>
            <Icon name="tienda" size={13} />
            Entrega: {pedido.estado_entrega.toLowerCase().replace(/_/g, " ")}
          </span>
        )}
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

      {pedido.nota_cliente && (
        <div className={styles.notaCliente}>
          <Icon name="nota" size={16} />
          <div>
            <div className={styles.notaTitulo}>Nota del cliente</div>
            {pedido.nota_cliente}
          </div>
        </div>
      )}

      <div className={styles.items}>
        <div className={styles.itemsTitulo}>
          {unidades} {unidades === 1 ? "ítem" : "ítems"}
        </div>
        <ul className={styles.listaItems}>
          {pedido.items.map((item, i) => (
            <li key={i} className={styles.item}>
              <span className={styles.cantidad}>{item.cantidad}×</span>
              <div className={styles.itemDatos}>
                <span className={styles.itemNombre}>{item.nombre}</span>
                {item.notas && <span className={styles.itemNota}>{item.notas}</span>}
                {item.cantidad > 1 && (
                  <span className={styles.itemUnitario}>{moneda(item.precio_unitario)} c/u</span>
                )}
              </div>
              <span className={styles.itemSubtotal}>{moneda(item.precio_unitario * item.cantidad)}</span>
            </li>
          ))}
        </ul>
        <div className={styles.total}>
          <span>Total</span>
          <span className={styles.totalValor}>{moneda(pedido.total)}</span>
        </div>
      </div>

      <div className={styles.odoo}>
        <div className={styles.odooInfo}>
          <CanalLogo canal="ODOO" {...infoCanal("ODOO")} size={34} />
          <div>
            <div className={styles.odooTitulo}>Sincronización con Odoo</div>
            <div className={styles.odooEstado}>
              {estadoOdoo === "idle" && "Sin sincronizar"}
              {estadoOdoo === "sincronizando" && "Sincronizando…"}
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
