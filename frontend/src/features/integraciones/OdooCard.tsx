import Icon from "../../shared/components/Icon";
import { useOdooSyncStub } from "./useOdooSyncStub";
import styles from "./IntegracionesPage.module.css";

export default function OdooCard() {
  const { estado, ejecutar } = useOdooSyncStub();

  return (
    <div className={`${styles.tarjeta} animate-in`} style={{ ["--i" as string]: 4 }}>
      <div className={styles.cabecera}>
        <div className={styles.logo} style={{ ["--c" as string]: "#714B67" }}>
          <Icon name="sync" size={20} />
        </div>
        <span className="badge">
          {estado === "idle" && "Sin sincronizar"}
          {estado === "sincronizando" && "Sincronizando..."}
          {estado === "no_disponible" && "Disponible próximamente"}
        </span>
      </div>
      <div className={styles.canal}>ODOO</div>
      <p className={styles.descripcion}>Sincroniza pedidos y ventas con tu ERP.</p>
      <button
        className={`btn btn-secondary btn-block ${estado === "sincronizando" ? "is-loading" : ""}`}
        disabled={estado === "sincronizando"}
        onClick={ejecutar}
      >
        <Icon name="sync" size={16} />
        Forzar sincronización
      </button>
    </div>
  );
}
