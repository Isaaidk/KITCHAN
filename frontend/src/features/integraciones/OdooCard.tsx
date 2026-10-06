import Icon from "../../shared/components/Icon";
import CanalLogo from "../../shared/components/CanalLogo";
import { infoCanal } from "../pedidos/estadoUtils";
import { useOdooSyncStub } from "./useOdooSyncStub";
import styles from "./IntegracionesPage.module.css";

export default function OdooCard() {
  const { estado, ejecutar } = useOdooSyncStub();

  return (
    <div className={`${styles.fila} animate-in`} style={{ ["--i" as string]: 4 }}>
      <CanalLogo className={styles.logo} canal="ODOO" {...infoCanal("ODOO")} size={44} />
      <div className={styles.texto}>
        <div className={styles.canal}>Odoo</div>
        <p className={styles.descripcion}>Sincroniza pedidos y ventas con tu ERP.</p>
      </div>
      <span className={styles.estado} aria-live="polite">
        {estado === "idle" && "Sin sincronizar"}
        {estado === "sincronizando" && "Sincronizando…"}
        {estado === "no_disponible" && "Aún no disponible"}
      </span>
      <div className={styles.accion}>
        <button
          className={`btn btn-secondary btn-sm ${estado === "sincronizando" ? "is-loading" : ""}`}
          disabled={estado === "sincronizando"}
          onClick={ejecutar}
        >
          <Icon name="sync" size={14} />
          Sincronizar ahora
        </button>
      </div>
    </div>
  );
}
