import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import Icon from "./Icon";
import styles from "./Modal.module.css";

interface Props {
  titulo: string;
  onClose: () => void;
  children: ReactNode;
  /** Ancho máximo de la caja (px). Por defecto 520. */
  ancho?: number;
}

const DURACION_SALIDA_MS = 160;

// Pila de modales abiertos: Escape solo cierra el que está encima (ej.
// "Cancelar pedido" abierto sobre el detalle del pedido).
const pilaModales: symbol[] = [];

export default function Modal({ titulo, onClose, children, ancho = 520 }: Props) {
  const [saliendo, setSaliendo] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cajaRef = useRef<HTMLDivElement>(null);
  // Ref para que `cerrar` sea estable aunque el padre pase un onClose inline.
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  // Cierre animado: primero se reproduce la salida y recién después se
  // avisa al padre, que es quien desmonta el modal.
  const cerrar = useCallback(() => {
    if (timerRef.current) return;
    setSaliendo(true);
    timerRef.current = setTimeout(() => onCloseRef.current(), DURACION_SALIDA_MS);
  }, []);

  useEffect(() => {
    const id = Symbol("modal");
    pilaModales.push(id);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && pilaModales[pilaModales.length - 1] === id) cerrar();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      pilaModales.splice(pilaModales.indexOf(id), 1);
    };
  }, [cerrar]);

  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    },
    [],
  );

  // Foco: al abrir pasa al modal (si ya hay un campo con autoFocus se respeta)
  // y al cerrar vuelve al elemento que lo abrió.
  useEffect(() => {
    const previo = document.activeElement as HTMLElement | null;
    if (!cajaRef.current?.contains(document.activeElement)) cajaRef.current?.focus();
    return () => previo?.focus?.();
  }, []);

  // Portal a <body>: evita que un ancestro con `transform` (tarjetas con
  // hover/animación) rompa el `position: fixed` del modal.
  return createPortal(
    <div
      className={`${styles.fondo} ${saliendo ? styles.saliendo : ""}`}
      onClick={cerrar}
      role="presentation"
    >
      <div
        ref={cajaRef}
        tabIndex={-1}
        className={styles.caja}
        style={{ maxWidth: ancho }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={titulo}
      >
        <div className={styles.encabezado}>
          <h2 className={styles.titulo}>{titulo}</h2>
          <button className={styles.cerrar} onClick={cerrar} aria-label="Cerrar">
            <Icon name="cerrar" size={18} />
          </button>
        </div>
        <div className={styles.cuerpo}>{children}</div>
      </div>
    </div>,
    document.body,
  );
}
