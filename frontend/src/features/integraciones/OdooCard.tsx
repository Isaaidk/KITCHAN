import { useEffect, useState } from "react";
import { mensajeDeError } from "../../shared/api/mensajeDeError";
import Icon from "../../shared/components/Icon";
import CanalLogo from "../../shared/components/CanalLogo";
import { useToastStore } from "../../shared/stores/toastStore";
import { conciliarFacturas, odooConfigurado } from "../facturacion/facturacionApi";
import { infoCanal } from "../pedidos/estadoUtils";
import styles from "./IntegracionesPage.module.css";

export default function OdooCard() {
  const [configurado, setConfigurado] = useState<boolean | null>(null);
  const [revisando, setRevisando] = useState(false);

  useEffect(() => {
    odooConfigurado()
      .then(setConfigurado)
      .catch(() => setConfigurado(false));
  }, []);

  const revisar = async () => {
    setRevisando(true);
    const toasts = useToastStore.getState();
    try {
      const actualizadas = await conciliarFacturas();
      toasts.add(
        actualizadas === 0
          ? "Las facturas ya estaban al día con Odoo."
          : `${actualizadas} ${actualizadas === 1 ? "factura actualizada" : "facturas actualizadas"} desde Odoo.`,
      );
    } catch (err) {
      toasts.add(mensajeDeError(err, "No se pudo revisar las facturas en Odoo."), "critica");
    } finally {
      setRevisando(false);
    }
  };

  return (
    <div className={`${styles.fila} animate-in`} style={{ ["--i" as string]: 4 }}>
      <CanalLogo className={styles.logo} canal="ODOO" {...infoCanal("ODOO")} size={44} />
      <div className={styles.texto}>
        <div className={styles.canal}>Odoo</div>
        <p className={styles.descripcion}>
          Emite la factura electrónica de cada pedido en Odoo, que la envía al SRI.
        </p>
      </div>
      {configurado === null ? (
        <span className={`skeleton ${styles.estadoSkeleton}`} aria-hidden="true" />
      ) : (
        <span
          className={`${styles.estado} ${configurado ? styles.estadoOk : ""}`}
          aria-live="polite"
        >
          {configurado ? "Conectado" : "Sin configurar"}
        </span>
      )}
      <div className={styles.accion}>
        <button
          className={`btn btn-secondary btn-sm ${revisando ? "is-loading" : ""}`}
          disabled={!configurado || revisando}
          onClick={revisar}
        >
          <Icon name="sync" size={14} />
          Revisar facturas
        </button>
      </div>
    </div>
  );
}
