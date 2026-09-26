import { useState } from "react";
import Icon from "../../shared/components/Icon";
import Modal from "../../shared/components/Modal";
import type { Pedido } from "../../shared/types/pedido";
import { motivosCancelacionPara } from "./integracionesApi";

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

  const confirmar = async () => {
    setEnviando(true);
    try {
      await onConfirmar(motivo, explicacion || "Cancelado desde KITCHAN");
      onClose();
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Modal titulo={`Cancelar pedido de ${pedido.cliente}`} onClose={onClose} ancho={460}>
      <div className="alert alert-warning" style={{ animation: "none" }}>
        <Icon name="alerta" size={16} />
        Esta acción no se puede deshacer.
      </div>

      <div className="field">
        <label className="label" htmlFor="motivo-cancelacion">
          Motivo
        </label>
        <select
          id="motivo-cancelacion"
          className="select"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
        >
          {motivos.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>
      </div>

      <div className="field">
        <label className="label" htmlFor="detalle-cancelacion">
          Detalle <span className="label-hint">(opcional)</span>
        </label>
        <input
          id="detalle-cancelacion"
          className="input"
          value={explicacion}
          onChange={(e) => setExplicacion(e.target.value)}
          placeholder="Ej. Nos quedamos sin ingredientes"
        />
      </div>

      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 8 }}>
        <button className="btn btn-secondary" onClick={onClose} disabled={enviando}>
          Volver
        </button>
        <button
          className={`btn btn-danger ${enviando ? "is-loading" : ""}`}
          onClick={confirmar}
          disabled={enviando}
        >
          {enviando ? "Cancelando..." : "Confirmar cancelación"}
        </button>
      </div>
    </Modal>
  );
}
