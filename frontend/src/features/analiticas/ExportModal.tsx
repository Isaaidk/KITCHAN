import { useState } from "react";
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
      <textarea readOnly value={csv} rows={8} style={{ width: "100%", fontFamily: "monospace" }} />
      <button onClick={copiar} style={{ marginTop: 12 }}>
        {copiado ? "Copiado" : "Copiar al portapapeles"}
      </button>
    </Modal>
  );
}
