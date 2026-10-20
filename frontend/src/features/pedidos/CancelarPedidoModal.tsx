import { useState } from "react";
import { mensajeDeError } from "../../shared/api/mensajeDeError";
import CanalLogo from "../../shared/components/CanalLogo";
import Icon from "../../shared/components/Icon";
import Modal from "../../shared/components/Modal";
import type { Pedido } from "../../shared/types/pedido";
import { moneda } from "../../shared/utils/formato";
import { infoCanal } from "./estadoUtils";
import { motivosCancelacionPara, tieneIntegracionDisponible } from "./integracionesApi";
import styles from "./CancelarPedidoModal.module.css";

interface Props {
  pedido: Pedido;
  onClose: () => void;
  onConfirmar: (reasonCode: string, explanation: string) => Promise<void>;
}

export default function CancelarPedidoModal({ pedido, onClose, onConfirmar }: Props) {
  const motivos = motivosCancelacionPara(pedido);
  const [motivo, setMotivo] = useState<string>(motivos[0].value);
  const [explicacion, setExplicacion] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canal = infoCanal(pedido.origen);
  const unidades = pedido.items.reduce((suma, item) => suma + item.cantidad, 0);
  const notificaPlataforma = tieneIntegracionDisponible(pedido.origen);

  const confirmar = async () => {
    setError(null);
    setEnviando(true);
    try {
      await onConfirmar(motivo, explicacion || "Cancelado desde KITCHAN");
      onClose();
    } catch (err) {
      setError(
        mensajeDeError(err, "No se pudo cancelar el pedido. Revisa la conexión e inténtalo de nuevo."),
      );
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Modal titulo={`Cancelar pedido de ${pedido.cliente}`} onClose={onClose} ancho={480}>
      <div className={styles.pedido}>
        <CanalLogo canal={pedido.origen} color={canal.color} nombre={canal.nombre} size={38} />
        <div className={styles.pedidoTexto}>
          <div className={styles.cliente}>{pedido.cliente}</div>
          <div className={styles.meta}>
            {canal.nombre} · {unidades} {unidades === 1 ? "ítem" : "ítems"}
            {pedido.id_externo && <span className={styles.referencia}> · #{pedido.id_externo}</span>}
          </div>
        </div>
        <span className={styles.total}>{moneda(pedido.total)}</span>
      </div>

      <div className={styles.aviso}>
        <Icon name="alerta" size={16} />
        <span>
          {notificaPlataforma
            ? `La cancelación se enviará a ${canal.nombre}. Esta acción no se puede deshacer.`
            : "El pedido se cancela solo dentro de KITCHAN. Esta acción no se puede deshacer."}
        </span>
      </div>

      <fieldset className={styles.grupo}>
        <legend className="label">Motivo</legend>
        <div className={styles.motivos}>
          {motivos.map((m) => (
            <label
              key={m.value}
              className={`${styles.motivo} ${motivo === m.value ? styles.motivoActivo : ""}`}
            >
              <input
                type="radio"
                name="motivo-cancelacion"
                value={m.value}
                checked={motivo === m.value}
                onChange={() => setMotivo(m.value)}
                className={styles.radio}
              />
              <span className={styles.marca} aria-hidden="true" />
              {m.label}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="field">
        <label className="label" htmlFor="detalle-cancelacion">
          Detalle <span className="label-hint">· opcional</span>
        </label>
        <input
          id="detalle-cancelacion"
          name="detalle"
          className="input"
          value={explicacion}
          onChange={(e) => setExplicacion(e.target.value)}
          autoComplete="off"
          placeholder="Ej. Nos quedamos sin ingredientes…"
        />
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          <Icon name="alerta" size={16} />
          {error}
        </div>
      )}

      <div className={styles.acciones}>
        <button className="btn btn-secondary" onClick={onClose} disabled={enviando}>
          Volver
        </button>
        <button
          className={`btn btn-danger ${enviando ? "is-loading" : ""}`}
          onClick={confirmar}
          disabled={enviando}
        >
          <Icon name="prohibido" size={16} />
          Confirmar cancelación
        </button>
      </div>
    </Modal>
  );
}
