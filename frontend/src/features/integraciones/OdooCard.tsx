import { useCallback, useEffect, useState } from "react";
import { mensajeDeError } from "../../shared/api/mensajeDeError";
import CanalLogo from "../../shared/components/CanalLogo";
import Icon from "../../shared/components/Icon";
import { useToastStore } from "../../shared/stores/toastStore";
import { hace, moneda, numero } from "../../shared/utils/formato";
import {
  conciliarFacturas,
  odooConfigurado,
  resumenFacturacion,
  type ResumenFacturacion,
} from "../facturacion/facturacionApi";
import { infoCanal } from "../pedidos/estadoUtils";
import styles from "./IntegracionesPage.module.css";

export default function OdooCard() {
  const [configurado, setConfigurado] = useState<boolean | null>(null);
  const [resumen, setResumen] = useState<ResumenFacturacion | null>(null);
  const [revisando, setRevisando] = useState(false);

  const cargarResumen = useCallback(() => {
    resumenFacturacion()
      .then(setResumen)
      // Las cifras no son críticas: sin ellas la tarjeta sigue mostrando el estado y el botón.
      .catch(() => setResumen(null));
  }, []);

  useEffect(() => {
    odooConfigurado()
      .then(setConfigurado)
      .catch(() => setConfigurado(false));
    cargarResumen();
  }, [cargarResumen]);

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
      cargarResumen();
    } catch (err) {
      toasts.add(mensajeDeError(err, "No se pudo revisar las facturas en Odoo."), "critica");
    } finally {
      setRevisando(false);
    }
  };

  return (
    <article className={`${styles.odoo} animate-in`}>
      <header className={styles.odooCabecera}>
        <CanalLogo className={styles.logo} canal="ODOO" {...infoCanal("ODOO")} size={52} />
        <div className={styles.tarjetaTitulo}>
          <h3 className={styles.canal}>Odoo</h3>
          {configurado === null ? (
            <span className={`skeleton ${styles.estadoSkeleton}`} aria-hidden="true" />
          ) : (
            <span className={`${styles.estado} ${configurado ? styles.estadoOk : styles.estadoAlerta}`} aria-live="polite">
              {configurado ? "Conectado" : "Sin configurar"}
            </span>
          )}
        </div>
        <button
          className={`btn btn-secondary btn-sm ${styles.odooBoton} ${revisando ? "is-loading" : ""}`}
          disabled={!configurado || revisando}
          onClick={revisar}
        >
          <Icon name="sync" size={14} />
          Revisar facturas
        </button>
      </header>

      <p className={styles.descripcion}>
        Emite la factura electrónica de cada pedido en Odoo, que la envía al SRI.
      </p>

      {resumen && resumen.total > 0 ? (
        <>
          <dl className={styles.datosOdoo}>
            <div>
              <dt>Autorizadas por el SRI</dt>
              <dd className={styles.cifra}>{numero(resumen.autorizadas)}</dd>
              <span className={styles.datoSub}>{moneda(resumen.monto_autorizado)} facturados</span>
            </div>
            <div>
              <dt>Esperando al SRI</dt>
              <dd className={styles.cifra}>{numero(resumen.pendientes_sri)}</dd>
              <span className={styles.datoSub}>Se revisan solas cada cierto tiempo</span>
            </div>
            <div className={resumen.con_error > 0 ? styles.datoAlerta : undefined}>
              <dt>Rechazadas</dt>
              <dd className={styles.cifra}>{numero(resumen.con_error)}</dd>
              <span className={styles.datoSub}>{resumen.con_error > 0 ? "Hay que reintentarlas" : "Ninguna"}</span>
            </div>
            <div>
              <dt>Última autorización</dt>
              <dd className={styles.ultimo}>
                {resumen.ultima_autorizacion ? hace(resumen.ultima_autorizacion) : "Todavía ninguna"}
              </dd>
            </div>
          </dl>

          {resumen.con_error > 0 && (
            <div className="alert alert-warning" role="alert" style={{ animation: "none" }}>
              <Icon name="alerta" size={16} />
              <span>
                {resumen.con_error === 1 ? "Hay una factura rechazada" : `Hay ${resumen.con_error} facturas rechazadas`}.
                Ábrela desde el pedido, en el Historial, y pulsa “Reintentar”.
              </span>
            </div>
          )}
        </>
      ) : (
        configurado && resumen && (
          <p className={styles.nota}>Todavía no se ha emitido ninguna factura desde KITCHAN.</p>
        )
      )}
    </article>
  );
}
