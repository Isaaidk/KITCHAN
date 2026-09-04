import { useOdooSyncStub } from "./useOdooSyncStub";
import styles from "./IntegracionesPage.module.css";

export default function OdooCard() {
  const { estado, ejecutar } = useOdooSyncStub();

  return (
    <div className={styles.tarjeta}>
      <div className={styles.canal}>ODOO</div>
      <div className={`${styles.estado} ${styles.desconectado}`}>
        {estado === "idle" && "Sin sincronizar"}
        {estado === "sincronizando" && "Sincronizando..."}
        {estado === "no_disponible" && "Disponible próximamente"}
      </div>
      <button className={styles.boton} disabled={estado === "sincronizando"} onClick={ejecutar}>
        Forzar sincronización
      </button>
    </div>
  );
}
