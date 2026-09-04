import type { ReactNode } from "react";
import styles from "./Modal.module.css";

interface Props {
  titulo: string;
  onClose: () => void;
  children: ReactNode;
}

export default function Modal({ titulo, onClose, children }: Props) {
  return (
    <div className={styles.fondo} onClick={onClose}>
      <div className={styles.caja} onClick={(e) => e.stopPropagation()}>
        <div className={styles.encabezado}>
          <span className={styles.titulo}>{titulo}</span>
          <button className={styles.cerrar} onClick={onClose}>
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
