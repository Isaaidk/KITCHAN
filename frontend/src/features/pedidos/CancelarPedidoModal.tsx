import { useState } from "react";
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
    <Modal titulo={`Cancelar pedido de ${pedido.cliente}`} onClose={onClose}>
      <div style={{ marginBottom: 10 }}>
        <label>Motivo</label>
        <select
          style={{ width: "100%", padding: 8 }}
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
      <div style={{ marginBottom: 14 }}>
        <label>Detalle (opcional)</label>
        <input
          style={{ width: "100%", padding: 8 }}
          value={explicacion}
          onChange={(e) => setExplicacion(e.target.value)}
          placeholder="Ej. Nos quedamos sin ingredientes"
        />
      </div>
      <button onClick={confirmar} disabled={enviando} style={{ color: "var(--color-danger)" }}>
        {enviando ? "Cancelando..." : "Confirmar cancelación"}
      </button>
    </Modal>
  );
}
