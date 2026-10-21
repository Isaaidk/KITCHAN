import CanalLogo from "../../shared/components/CanalLogo";
import Icon from "../../shared/components/Icon";
import Modal from "../../shared/components/Modal";
import type { Pedido } from "../../shared/types/pedido";
import { moneda } from "../../shared/utils/formato";
import { ETIQUETA_FACTURA } from "../facturacion/facturacionApi";
import { useFacturaPedido } from "../facturacion/useFacturaPedido";
import CancelarPedidoModal from "./CancelarPedidoModal";
import { colorVarEstado, ETIQUETA_ESTADO, infoCanal, nombreMetodoPago } from "./estadoUtils";
import { usePedidoAcciones } from "./usePedidoAcciones";
import styles from "./OrderDetailModal.module.css";

const PASOS: Array<Pedido["estado"]> = ["NUEVA", "EN_PREPARACION", "LISTA", "ENTREGADA"];

const formatoFechaHora = new Intl.DateTimeFormat(undefined, {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

interface Props {
  pedido: Pedido;
  onClose: () => void;
}

export default function OrderDetailModal({ pedido, onClose }: Props) {
  const {
    factura,
    cargando: cargandoFactura,
    facturando,
    facturar,
  } = useFacturaPedido(pedido.id);
  const facturable = pedido.estado === "LISTA" || pedido.estado === "ENTREGADA";
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
            {pedido.id_externo && <span className={styles.referencia} translate="no">
                #{pedido.id_externo}
              </span>}
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
          <time dateTime={pedido.fecha_creacion}>{formatoFechaHora.format(new Date(pedido.fecha_creacion))}</time>
        </span>
        {pedido.metodo_pago && (
          <span className={styles.dato}>
            <Icon name="dinero" size={13} />
            Pago: {nombreMetodoPago(pedido.metodo_pago)}
          </span>
        )}
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
          <div className={styles.linea} aria-hidden="true">
            <div className={styles.lineaRelleno} />
          </div>
          <ol className={styles.pasos} aria-label="Progreso del pedido">
            {PASOS.map((paso, i) => (
              <li
                key={paso}
                aria-current={i === indiceActual ? "step" : undefined}
                className={`${styles.paso} ${i <= indiceActual ? styles.pasoActivo : ""} ${
                  i === indiceActual ? styles.pasoActual : ""
                }`}
                style={{ ["--i" as string]: i }}
              >
                <div className={styles.punto} aria-hidden="true">
                  {i < indiceActual && <Icon name="check" size={12} strokeWidth={3} />}
                </div>
                <span className={styles.pasoTexto}>{ETIQUETA_ESTADO[paso]}</span>
                {/* El avance no depende solo del color: se dice en texto para lectores de pantalla. */}
                <span className="sr-only">
                  {i < indiceActual ? " (completado)" : i === indiceActual ? " (paso actual)" : " (pendiente)"}
                </span>
              </li>
            ))}
          </ol>
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
          <div className={styles.odooTexto}>
            <div className={styles.odooTitulo}>
              {factura?.numero ? `Factura ${factura.numero.replace(/^Fact\s*/, "")}` : "Factura electrónica"}
            </div>
            <div
              className={styles.odooEstado}
              data-estado={factura?.estado}
              aria-live="polite"
            >
              {cargandoFactura && "Consultando…"}
              {!cargandoFactura && !factura && (facturable ? "Sin facturar" : "Se factura cuando el pedido esté listo")}
              {factura && ETIQUETA_FACTURA[factura.estado]}
            </div>
            {factura?.numero_autorizacion && (
              <div className={styles.odooDetalle} title="Número de autorización del SRI">
                Autorización {factura.numero_autorizacion}
              </div>
            )}
            {factura?.estado === "CON_ERROR" && factura.mensaje_error && (
              <div className={styles.odooDetalle}>{factura.mensaje_error}</div>
            )}
          </div>
        </div>
        {!cargandoFactura && (!factura || factura.estado === "CON_ERROR") && (
          <button
            className={`btn btn-secondary btn-sm ${facturando ? "is-loading" : ""}`}
            disabled={facturando || (!factura && !facturable)}
            onClick={facturar}
          >
            {factura ? "Reintentar" : "Facturar"}
          </button>
        )}
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
