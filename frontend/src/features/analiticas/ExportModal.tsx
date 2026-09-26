import { useState } from "react";
import Icon from "../../shared/components/Icon";
import Modal from "../../shared/components/Modal";
import type { AnaliticasPedidos } from "./types";

interface Props {
  datos: AnaliticasPedidos;
  onClose: () => void;
}

function generarCSV(datos: AnaliticasPedidos): string {
  const filas = [["canal", "pedidos_hoy"]];
  Object.entries(datos.por_canal).forEach(([canal, cantidad]) => {
    filas.push([canal, String(cantidad)]);
  });
  return filas.map((fila) => fila.join(",")).join("\n");
}

export default function ExportModal({ datos, onClose }: Props) {
  const [copiado, setCopiado] = useState(false);
  const csv = generarCSV(datos);

  const copiar = async () => {
    await navigator.clipboard.writeText(csv);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 2000);
  };

  return (
    <Modal titulo="Exportar analíticas (CSV)" onClose={onClose}>
      <p style={{ margin: "0 0 12px", fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
        Copia estos datos y pégalos en Excel o Google Sheets.
      </p>
      <textarea
        className="textarea"
        readOnly
        value={csv}
        rows={8}
        style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace", fontSize: "0.82rem" }}
      />
      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 16 }}>
        <button className={`btn ${copiado ? "btn-success" : "btn-primary"}`} onClick={copiar}>
          <Icon name={copiado ? "check" : "copiar"} size={16} />
          {copiado ? "Copiado" : "Copiar al portapapeles"}
        </button>
      </div>
    </Modal>
  );
}
